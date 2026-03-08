from sqlalchemy import text
from app.db.base import engine

def upgrade():
    with engine.connect() as connection:
        print("Adding parent_id column to knowledge_nodes...")
        connection.execute(text("ALTER TABLE knowledge_nodes ADD COLUMN IF NOT EXISTS parent_id INTEGER REFERENCES knowledge_nodes(id);"))
        connection.commit()
        print("Done.")

if __name__ == "__main__":
    upgrade()
