"""
Service for creating courses from AI-generated node data.

Encapsulates the common pattern: parse AI response → create Course + KnowledgeNodes + KnowledgeEdges.
"""
import json
import logging
import re

from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.knowledge import KnowledgeNode, KnowledgeEdge

logger = logging.getLogger(__name__)


def parse_ai_nodes(ai_content: str) -> list[dict]:
    """Parse AI text response into a list of node dicts.

    Handles markdown code fences and dict-wrapped arrays.
    Each node must have a 'title' key.
    """
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
        nodes_data = next(
            (v for v in parsed.values() if isinstance(v, list)),
            None,
        )
        if nodes_data is None:
            raise ValueError(f"AI вернул объект без списка: {list(parsed.keys())}")
    else:
        nodes_data = parsed

    if not nodes_data or not all(isinstance(n, dict) and "title" in n for n in nodes_data):
        raise ValueError(
            "AI вернул некорректные данные: каждый элемент должен быть объектом с полем 'title'"
        )

    return nodes_data


def create_course_from_nodes(
    db: Session,
    topic: str,
    nodes_data: list[dict],
    org_id: int | None = None,
) -> Course:
    """Create a Course with KnowledgeNodes and KnowledgeEdges from parsed node data.

    Returns the created Course object (already committed).
    """
    new_course = Course(title=topic, description=f"Курс: {topic}", org_id=org_id)
    db.add(new_course)
    db.flush()

    title_to_id: dict[str, int] = {}
    created_nodes: list[tuple[KnowledgeNode, list[str]]] = []

    for node_data in nodes_data:
        new_node = KnowledgeNode(
            label=node_data["title"],
            description=node_data.get("description", ""),
            level=1,
            course_id=new_course.id,
            prerequisites=[],
        )
        db.add(new_node)
        db.flush()
        title_to_id[node_data["title"]] = new_node.id
        created_nodes.append(
            (new_node, node_data.get("list_of_prerequisite_titles", []))
        )

    for node, prereq_titles in created_nodes:
        new_prereq_ids: list[int] = []
        for p_title in prereq_titles:
            if p_title in title_to_id:
                p_id = title_to_id[p_title]
                new_prereq_ids.append(p_id)
                db.add(KnowledgeEdge(source_id=p_id, target_id=node.id))
        node.prerequisites = new_prereq_ids

    db.commit()
    return new_course
