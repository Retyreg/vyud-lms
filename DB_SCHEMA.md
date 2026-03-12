# Структура базы данных

> Последнее обновление: Сессия 2, март 2026

## Таблицы

### `users`
Определена в: `backend/app/models/user.py`
- `id`: Integer, primary_key, index
- `email`: String, unique, index, nullable=False
- `hashed_password`: String, nullable=False (bcrypt cost=12)
- `full_name`: String, nullable=True
- `role`: Enum(`UserRole`), default=`associate`
- `is_active`: Boolean, default=True
- `created_at`: DateTime(timezone=True), server_default=now()
- `updated_at`: DateTime(timezone=True), onupdate=now()

**Роли (`UserRole`):** `super_admin`, `regional_manager`, `store_manager`, `associate`  
*(устаревшие алиасы для обратной совместимости: `student`, `curator`, `admin`)*

---

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

---

### `knowledge_nodes`
Определена в: `backend/app/models/knowledge.py`
- `id`: Integer, primary_key, index
- `label`: String, index, nullable=False
- `description`: Text, nullable=True
- `level`: Integer, default=1
- `is_completed`: Boolean, default=False
- `prerequisites`: JSON, default=[] *(список id узлов-пресквизитов)*
- `parent_id`: Integer, ForeignKey("knowledge_nodes.id"), nullable=True
- `course_id`: Integer, ForeignKey("courses.id"), nullable=True

### `knowledge_edges`
Определена в: `backend/app/models/knowledge.py`
- `id`: Integer, primary_key, index
- `source_id`: Integer, ForeignKey("knowledge_nodes.id")
- `target_id`: Integer, ForeignKey("knowledge_nodes.id")
- `weight`: Float, default=1.0

---

### `tasks`
Определена в: `backend/app/models/task.py`
- `id`: Integer, primary_key, index
- `title`: String(255), nullable=False, index
- `description`: Text, nullable=True
- `status`: Enum(`TaskStatus`), default=`pending`, index
- `priority`: Enum(`TaskPriority`), default=`medium`
- `assignee_id`: Integer, ForeignKey("users.id"), nullable=True, index
- `created_by_id`: Integer, ForeignKey("users.id"), nullable=True
- `checklist`: JSON, default=[] *(массив объектов: `{title, is_done, photo_required}`)*
- `due_date`: DateTime(timezone=True), nullable=True
- `created_at`: DateTime(timezone=True), server_default=now()
- `updated_at`: DateTime(timezone=True), onupdate=now()
- `completed_at`: DateTime(timezone=True), nullable=True *(заполняется автоматически)*
- `photo_url`: String(2048), nullable=True

**Статусы (`TaskStatus`):** `pending`, `in_progress`, `completed`, `overdue`  
**Приоритеты (`TaskPriority`):** `low`, `medium`, `high`, `critical`

---

### `news_posts`
Определена в: `backend/app/models/news.py`
- `id`: Integer, primary_key, index
- `title`: String(255), nullable=False, index
- `content`: Text, nullable=False
- `summary`: String(500), nullable=True *(краткое описание для карточки в ленте)*
- `author_id`: Integer, ForeignKey("users.id"), nullable=True
- `is_published`: Boolean, default=True *(False = черновик, скрыт из ленты)*
- `created_at`: DateTime(timezone=True), server_default=now()
- `updated_at`: DateTime(timezone=True), onupdate=now()

---

## Ручные миграции (legacy)

### `migrate_db.py` / `update_db.py`
- Добавляют колонку `parent_id` в таблицу `knowledge_nodes` через `ALTER TABLE`.

### `reset_nodes.py`
- Удаляет (DROP) таблицы `knowledge_nodes` и `knowledge_edges`.
- Пересоздает их заново через `Base.metadata.create_all`, применяя актуальную схему из моделей.

> ⚠️ **Примечание:** Для новых таблиц (`users`, `tasks`, `news_posts`) ручные миграции не нужны —  
> `Base.metadata.create_all()` вызывается автоматически при старте приложения.

