# Структура базы данных

## Таблицы

### `courses`
Определена в: `backend/app/models/course.py`
- `id`: Integer, primary_key, index
- `title`: String, index, nullable=False
- `description`: Text, nullable=True

### `lessons`
Определена в: `backend/app/models/course.py`
- `id`: Integer, primary_key, index
- `title`: String, index, nullable=False
- `content`: Text, nullable=False
- `course_id`: Integer, ForeignKey("courses.id")

### `knowledge_nodes`
Определена в: `backend/app/models/knowledge.py`
- `id`: Integer, primary_key, index
- `label`: String, index, nullable=False (уникальность убрана в reset_nodes.py)
- `description`: Text, nullable=True
- `level`: Integer, default=1
- `is_completed`: Boolean, default=False
- `prerequisites`: JSON, default=[]
- `parent_id`: Integer, ForeignKey("knowledge_nodes.id"), nullable=True (Добавлено через migrate_db.py/update_db.py)

### `knowledge_edges`
Определена в: `backend/app/models/knowledge.py`
- `id`: Integer, primary_key, index
- `source_id`: Integer, ForeignKey("knowledge_nodes.id")
- `target_id`: Integer, ForeignKey("knowledge_nodes.id")
- `weight`: Float, default=1.0

## Ручные миграции

### `migrate_db.py` / `update_db.py`
- Добавляют колонку `parent_id` в таблицу `knowledge_nodes` через `ALTER TABLE`.

### `reset_nodes.py`
- Удаляет (DROP) таблицы `knowledge_nodes` и `knowledge_edges`.
- Пересоздает их заново через `Base.metadata.create_all`, применяя актуальную схему из моделей (где у `label` убрана уникальность).
