import fitz  # PyMuPDF
import litellm


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


async def embed_chunks(chunks: list[str]) -> list[list[float]]:
    response = await litellm.aembedding(model="text-embedding-3-small", input=chunks)
    return [item["embedding"] for item in response.data]


async def build_graph_from_pdf(
    chunks: list[str],
    topic: str,
    call_ai_fn,
) -> list[dict]:
    top_chunks = sorted(chunks, key=len, reverse=True)[:5]
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

    import json
    import re

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
