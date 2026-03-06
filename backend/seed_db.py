from app.db.base import SessionLocal, engine, Base
from app.models.course import Course, Lesson
from app.models.knowledge import KnowledgeNode, KnowledgeEdge

def seed():
    # Создаем таблицы
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Проверяем, есть ли данные
    if db.query(Course).first():
        print("База данных уже содержит данные.")
        return

    print("Заполнение базы данных...")

    # Курсы
    course_python = Course(title="Python Basics", description="Введение в Python")
    db.add(course_python)
    db.commit()

    lesson1 = Lesson(title="Переменные", content="Контент про переменные...", course_id=course_python.id)
    lesson2 = Lesson(title="Циклы", content="Контент про циклы...", course_id=course_python.id)
    db.add_all([lesson1, lesson2])

    # Граф знаний
    node1 = KnowledgeNode(label="Python Syntax", level=1)
    node2 = KnowledgeNode(label="Variables", level=1)
    node3 = KnowledgeNode(label="Loops", level=1)
    db.add_all([node1, node2, node3])
    db.commit()

    edge1 = KnowledgeEdge(source_id=node1.id, target_id=node2.id)
    edge2 = KnowledgeEdge(source_id=node2.id, target_id=node3.id)
    db.add_all([edge1, edge2])
    
    db.commit()
    db.close()
    print("Готово!")

if __name__ == "__main__":
    seed()
