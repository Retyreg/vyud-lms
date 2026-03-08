from sqlalchemy import text
from app.db.base import engine, Base
from app.models.knowledge import KnowledgeNode, KnowledgeEdge

def reset_tables():
    with engine.connect() as connection:
        print("Dropping knowledge_nodes table (CASCADE)...")
        connection.execute(text("DROP TABLE IF EXISTS knowledge_nodes CASCADE;"))
        connection.execute(text("DROP TABLE IF EXISTS knowledge_edges CASCADE;"))
        connection.commit()
        print("Tables dropped.")
    
    print("Recreating tables...")
    Base.metadata.create_all(bind=engine)
    print("Done. Schema updated (label is not unique).")

if __name__ == "__main__":
    reset_tables()
