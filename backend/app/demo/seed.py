"""Seed a fresh demo user with a knowledge graph derived from the SOP library.

Seeding strategy:
- industry → segment → first SOP in that segment (ru language)
- SOP steps → KnowledgeNodes (linear graph)
- KnowledgeEdges: linear chain step[i] → step[i+1]
- NodeExplanations: first 3 nodes pre-populated from SOP content (no LLM call)
- NodeSRProgress: first 5 nodes queued for SM-2, user_key = "demo:{user_id}"
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.knowledge import KnowledgeEdge, KnowledgeNode, NodeExplanation, NodeSRProgress

logger = logging.getLogger(__name__)

SOPS_DIR = Path(__file__).parent / "sops"
INDEX_PATH = SOPS_DIR / "index.json"

INDUSTRY_SEGMENT: dict[str, str] = {
    "HoReCa": "cafe_restaurant",
    "Retail": "retail",
    "FMCG": "fmcg",
    "Other": "cafe_restaurant",
}

# Map segment folder names to file prefixes
SEGMENT_FOLDER: dict[str, str] = {
    "cafe_restaurant": "cafe_restaurant",
    "retail": "retail",
    "fmcg": "fmcg",
    "warehouse": "warehouse",
    "hotel": "hotel",
}


def _load_index() -> dict:
    with INDEX_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _load_sop(segment: str, file_prefix: str, language: str = "ru") -> dict | None:
    folder = SOPS_DIR / SEGMENT_FOLDER.get(segment, segment)
    suffix = f"_{language}.json"
    for path in sorted(folder.glob(f"*{suffix}")):
        if file_prefix in path.name:
            with path.open(encoding="utf-8") as f:
                return json.load(f)
    # fallback: first file in folder with the language suffix
    candidates = sorted(folder.glob(f"*{suffix}"))
    if candidates:
        with candidates[0].open(encoding="utf-8") as f:
            return json.load(f)
    return None


def seed_demo_user(db: Session, user) -> Course:
    """Create isolated demo data for a DemoUser. Returns the seeded Course."""
    segment = INDUSTRY_SEGMENT.get(user.industry, "cafe_restaurant")
    index = _load_index()
    segment_data = index["segments"].get(segment, {})
    sops_meta = segment_data.get("sops", [])

    # Pick the first SOP in the segment
    first_sop_id = sops_meta[0]["id"] if sops_meta else None
    file_prefix = first_sop_id.split("-", 1)[1] if first_sop_id and "-" in first_sop_id else ""
    sop_data = _load_sop(segment, file_prefix, language="ru")

    if not sop_data:
        logger.warning("No SOP data found for segment=%s, using fallback barista SOP", segment)
        sop_data = _load_sop("cafe_restaurant", "barista_onboarding", language="ru")

    course_title = sop_data.get("title", "Демо-обучение") if sop_data else "Демо-обучение"

    course = Course(
        title=f"[Демо] {course_title}",
        description=sop_data.get("description") if sop_data else None,
        org_id=None,
    )
    db.add(course)
    db.flush()

    if not sop_data:
        return course

    steps = sop_data.get("steps", [])[:8]  # cap at 8 nodes
    nodes: list[KnowledgeNode] = []
    for step in steps:
        node = KnowledgeNode(
            label=step["title"],
            description=step.get("content", ""),
            level=1,
            is_completed=False,
            prerequisites=[],
            course_id=course.id,
        )
        db.add(node)
        nodes.append(node)
    db.flush()

    # Linear edges: node[0] → node[1] → ... → node[n-1]
    for i in range(len(nodes) - 1):
        edge = KnowledgeEdge(
            source_id=nodes[i].id,
            target_id=nodes[i + 1].id,
            weight=1.0,
        )
        db.add(edge)

    # Pre-generated explanations for first 3 nodes (from key_takeaway)
    for i, step in enumerate(steps[:3]):
        key = step.get("key_takeaway", "")
        content = step.get("content", "")
        explanation_text = (
            f"**Главное:** {key}\n\n"
            f"**Подробнее:** {content}"
        )
        explanation = NodeExplanation(
            node_id=nodes[i].id,
            explanation=explanation_text,
        )
        db.add(explanation)

    # SM-2 review queue for first 5 nodes
    user_key = f"demo:{user.id}"
    for node in nodes[:5]:
        progress = NodeSRProgress(
            node_id=node.id,
            user_key=user_key,
            easiness_factor=2.5,
            interval=0,
            repetitions=0,
            next_review=datetime.now(timezone.utc),
        )
        db.add(progress)

    logger.info(
        "Seeded demo user %s: course_id=%d, %d nodes, segment=%s",
        user.id,
        course.id,
        len(nodes),
        segment,
    )
    return course
