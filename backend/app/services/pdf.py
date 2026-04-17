import json
import math
import os
import re

import fitz  # PyMuPDF
import httpx

JINA_API_KEY = os.getenv("JINA_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

_JINA_URL = "https://api.jina.ai/v1/embeddings"
_JINA_MODEL = "jina-embeddings-v2-base-multilingual"


def extract_text_from_pdf(file_bytes: bytes) -> str:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(pages)


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks


# ---------------------------------------------------------------------------
# Embeddings — Jina AI (free) or OpenAI fallback
# ---------------------------------------------------------------------------

async def embed_chunks(chunks: list[str]) -> list[list[float] | None]:
    """Embed text chunks. Priority: Jina AI → OpenAI → None."""
    if JINA_API_KEY:
        return await _embed_jina(chunks)
    if OPENAI_API_KEY:
        return await _embed_openai(chunks)
    return [None] * len(chunks)


async def _embed_jina(chunks: list[str]) -> list[list[float] | None]:
    """Embed via Jina AI REST API (free tier, multilingual)."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _JINA_URL,
                headers={
                    "Authorization": f"Bearer {JINA_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"model": _JINA_MODEL, "input": chunks},
                timeout=30.0,
            )
        if resp.status_code != 200:
            return [None] * len(chunks)
        data = resp.json()
        return [item["embedding"] for item in data["data"]]
    except Exception:
        return [None] * len(chunks)


async def _embed_openai(chunks: list[str]) -> list[list[float] | None]:
    """Embed via OpenAI (legacy fallback)."""
    try:
        import litellm
        response = await litellm.aembedding(model="text-embedding-3-small", input=chunks)
        return [item["embedding"] for item in response.data]
    except Exception:
        return [None] * len(chunks)


# ---------------------------------------------------------------------------
# Chunk selection helpers
# ---------------------------------------------------------------------------

def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    return dot / (norm_a * norm_b + 1e-8)


def _mean_vector(vectors: list[list[float]]) -> list[float]:
    n = len(vectors)
    size = len(vectors[0])
    return [sum(v[i] for v in vectors) / n for i in range(size)]


def _tfidf_scores(chunks: list[str], query: str) -> list[float]:
    """Score each chunk by TF-IDF relevance to query (pure Python, no deps)."""
    query_words = set(re.findall(r'\w+', query.lower()))
    n = len(chunks)
    scores = []

    # Document frequency for IDF
    df: dict[str, int] = {}
    tokenized = []
    for chunk in chunks:
        words = re.findall(r'\w+', chunk.lower())
        tokenized.append(words)
        for w in set(words):
            df[w] = df.get(w, 0) + 1

    for words in tokenized:
        if not words:
            scores.append(0.0)
            continue
        total = len(words)
        score = 0.0
        for qw in query_words:
            tf = words.count(qw) / total
            idf = math.log((n + 1) / (df.get(qw, 0) + 1)) + 1
            score += tf * idf
        scores.append(score)
    return scores


def _select_top_chunks(
    chunks: list[str],
    embeddings: list[list[float] | None],
    topic: str,
    k: int = 5,
) -> list[str]:
    """
    Select k most relevant chunks.
    - With embeddings: cosine similarity to mean topic embedding
    - Without embeddings: TF-IDF score against topic string
    """
    valid = [(i, e) for i, e in enumerate(embeddings) if e is not None]

    if valid:
        mean_emb = _mean_vector([e for _, e in valid])
        scored = [(i, _cosine(e, mean_emb)) for i, e in valid]
        # Include any chunks without embeddings at the end
        missing = [(i, -1.0) for i in range(len(chunks)) if embeddings[i] is None]
        scored = sorted(scored + missing, key=lambda x: x[1], reverse=True)
    else:
        tfidf = _tfidf_scores(chunks, topic)
        scored = sorted(enumerate(tfidf), key=lambda x: x[1], reverse=True)

    top_indices = [i for i, _ in scored[:k]]
    return [chunks[i] for i in top_indices]


# ---------------------------------------------------------------------------
# Main: build graph from PDF
# ---------------------------------------------------------------------------

async def build_graph_from_pdf(
    chunks: list[str],
    topic: str,
    call_ai_fn,
    embeddings: list[list[float] | None] | None = None,
) -> list[dict]:
    """Build a learning roadmap from PDF chunks using AI.

    Selects top-5 most relevant chunks via semantic similarity (if embeddings
    provided) or TF-IDF fallback, then asks AI to build a graph.
    """
    if embeddings is None:
        embeddings = [None] * len(chunks)

    top_chunks = _select_top_chunks(chunks, embeddings, topic, k=5)
    context = "\n\n".join(top_chunks)

    prompt = (
        f"На основе следующего текста создай дорожную карту обучения по теме '{topic}'.\n\n"
        f"Текст:\n{context}\n\n"
        f"Верни JSON-массив из 5–7 объектов: "
        f'[{{"title": "...", "description": "...", "list_of_prerequisite_titles": []}}]'
    )
    ai_content = await call_ai_fn(
        prompt,
        "Ты эксперт. Ответ — только валидный JSON без комментариев.",
        json_mode=False,
    )

    if "```json" in ai_content:
        ai_content = ai_content.split("```json")[1].split("```")[0]
    elif "```" in ai_content:
        ai_content = ai_content.split("```")[1].split("```")[0]
    else:
        m = re.search(r"(\[[\s\S]*\]|\{[\s\S]*\})", ai_content)
        if m:
            ai_content = m.group(1)

    parsed = json.loads(ai_content.strip())
    if isinstance(parsed, dict):
        nodes_data = next((v for v in parsed.values() if isinstance(v, list)), None)
        if nodes_data is None:
            raise ValueError(f"AI вернул объект без списка: {list(parsed.keys())}")
    else:
        nodes_data = parsed

    if not nodes_data or not all(isinstance(n, dict) and "title" in n for n in nodes_data):
        raise ValueError("AI вернул некорректные данные")

    return nodes_data
