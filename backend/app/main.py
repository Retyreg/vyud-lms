from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import os
import httpx
import traceback
from dotenv import load_dotenv
from litellm import completion

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY environment variable is not set")

async def call_ai(prompt: str, system: str, json_mode: bool = True) -> str:
    """
    Универсальная функция вызова ИИ.
    Сначала пробует Groq, при ошибке — Gemini через litellm.
    """
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt}
    ]
    
    # --- Попытка 1: Groq ---
    try:
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "temperature": 0.4,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=30.0
            )
            
            if response.status_code == 200:
                raw_bytes = response.content
                # Очистка спецсимволов
                clean_bytes = raw_bytes.replace(b'\xe2\x80\xa8', b' ').replace(b'\xe2\x80\xa9', b' ')
                safe_text = clean_bytes.decode('utf-8', errors='replace')
                
                groq_data = json.loads(safe_text)
                return groq_data['choices'][0]['message']['content']
            else:
                print(f"Groq API returned {response.status_code}. Falling back...")
                
    except Exception as e:
        print(f"Groq failed: {e}. Falling back to Gemini...")

    # --- Попытка 2: Gemini (Fallback) ---
    try:
        model = "gemini/gemini-1.5-flash"
        api_ver = "v1"
        
        # litellm completion is synchronous by default, but can be awaited if using async version, 
        # or we wrap it. For simplicity in this context we call it directly as before.
        # Note: litellm.completion is blocking, but we are inside async def. 
        # It's better to run it in executor if strictly async, but we'll stick to simple call as per request logic.
        response = completion(
            model=model, 
            messages=messages,
            api_version=api_ver
        )
        content = response.choices[0].message.content
        
        # Clean up text just in case
        content = content.replace('\u2028', ' ').replace('\u2029', ' ')
        return content

    except Exception as e:
        print(f"Gemini failed: {e}")
        raise HTTPException(status_code=503, detail="All AI providers unavailable")

from app.db.base import Base, engine, SessionLocal
import app.models 
from app.models.course import Course
from app.models.knowledge import KnowledgeNode, KnowledgeEdge

# Создаем таблицы при старте приложения
Base.metadata.create_all(bind=engine)

app = FastAPI(title="VYUD LMS API", version="0.1.0")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Настройка CORS для общения с Next.js
origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to VYUD LMS API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

# --- Pydantic модели для ответа API (можно вынести в schemas/) ---
class NodeSchema(BaseModel):
    id: int
    label: str
    level: int
    is_completed: bool
    is_available: bool
    prerequisites: List[int] = []

class EdgeSchema(BaseModel):
    source: int
    target: int

class GraphResponse(BaseModel):
    nodes: List[NodeSchema]
    edges: List[EdgeSchema]

class CourseSchema(BaseModel):
    id: int
    title: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

@app.get("/api/courses", response_model=List[CourseSchema])
def get_courses(db: Session = Depends(get_db)):
    """
    Возвращает список доступных курсов из БД.
    """
    courses = db.query(Course).all()
    return courses

@app.delete("/api/nodes/clear-test")
def clear_test_nodes(db: Session = Depends(get_db)):
    """
    Удаляет все узлы, содержащие 'Тестовый' в названии.
    """
    deleted_count = db.query(KnowledgeNode).filter(KnowledgeNode.label.like("%Тестовый%")).delete(synchronize_session=False)
    db.commit()
    return {"status": "ok", "deleted_count": deleted_count}

@app.get("/api/nodes", response_model=List[NodeSchema])
def get_all_nodes(db: Session = Depends(get_db)):
    """
    Возвращает список всех узлов.
    """
    nodes = db.query(KnowledgeNode).all()
    
    # Создаем словарь статусов для быстрой проверки доступности (аналогично графу)
    completed_ids = {n.id for n in nodes if n.is_completed}
    
    node_schemas = []
    for n in nodes:
        prereqs = n.prerequisites or []
        is_available = all(pid in completed_ids for pid in prereqs)
        
        node_schemas.append(NodeSchema(
            id=n.id, 
            label=n.label, 
            level=n.level, 
            is_completed=n.is_completed,
            is_available=is_available,
            prerequisites=prereqs
        ))
    return node_schemas

@app.get("/api/knowledge-graph", response_model=GraphResponse)
def get_knowledge_graph(db: Session = Depends(get_db)):
    """
    Возвращает структуру дерева навыков для визуализации из БД.
    """
    nodes = db.query(KnowledgeNode).all()
    edges = db.query(KnowledgeEdge).all()
    
    # Создаем словарь статусов для быстрой проверки
    completed_ids = {n.id for n in nodes if n.is_completed}
    
    node_schemas = []
    for n in nodes:
        # Узел доступен, если у него нет пререквизитов ИЛИ все пререквизиты выполнены
        prereqs = n.prerequisites or []
        is_available = all(pid in completed_ids for pid in prereqs)
        
        node_schemas.append(NodeSchema(
            id=n.id, 
            label=n.label, 
            level=n.level, 
            is_completed=n.is_completed,
            is_available=is_available,
            prerequisites=prereqs
        ))

    return GraphResponse(
        nodes=node_schemas,
        edges=[EdgeSchema(source=e.source_id, target=e.target_id) for e in edges]
    )

@app.post("/api/complete/{node_id}")
def complete_node(node_id: int, db: Session = Depends(get_db)):
    """
    Отмечает узел как изученный.
    """
    node = db.query(KnowledgeNode).filter(KnowledgeNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    node.is_completed = True
    db.commit()
    return {"status": "ok", "message": f"Node {node.label} marked as completed"}

@app.post("/api/nodes/{node_id}/complete")
def complete_node_rest(node_id: int, db: Session = Depends(get_db)):
    """
    Отмечает узел как изученный (REST-style).
    """
    node = db.query(KnowledgeNode).filter(KnowledgeNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    node.is_completed = True
    db.commit()
    return {"status": "ok", "message": f"Node {node.label} marked as completed", "is_completed": True}

@app.post("/api/nodes/{node_id}/toggle-complete")
def toggle_complete_node(node_id: int, db: Session = Depends(get_db)):
    """
    Переключает статус изучения узла (изучено/не изучено).
    """
    node = db.query(KnowledgeNode).filter(KnowledgeNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    # Инвертируем значение
    node.is_completed = not node.is_completed
    db.commit()
    
    status_msg = "completed" if node.is_completed else "uncompleted"
    return {
        "status": "ok", 
        "message": f"Node {node.label} marked as {status_msg}", 
        "is_completed": node.is_completed
    }

class ExplanationResponse(BaseModel):
    explanation: str

class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    correct_answer: int  # Индекс правильного ответа (0-3)
    explanation: Optional[str] = None # Пояснение (почему это верно)

class QuizResponse(BaseModel):
    questions: List[QuizQuestion]

class CourseGenerationRequest(BaseModel):
    topic: str

class QuizSubmission(BaseModel):
    answers: dict[int, int] # {question_index: selected_option_index}
    questions: List[QuizQuestion]

@app.post("/api/nodes/{node_id}/check-quiz")
def check_quiz_and_complete(node_id: int, submission: QuizSubmission, db: Session = Depends(get_db)):
    """
    Проверяет ответы на тест. Если 100% верно, отмечает узел как пройденный.
    """
    node = db.query(KnowledgeNode).filter(KnowledgeNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    correct_count = 0
    total_questions = len(submission.questions)

    if total_questions == 0:
         raise HTTPException(status_code=400, detail="No questions provided")

    for idx, question in enumerate(submission.questions):
        user_answer = submission.answers.get(idx)
        if user_answer is not None and user_answer == question.correct_answer:
            correct_count += 1
    
    is_passed = correct_count == total_questions
    
    if is_passed:
        node.is_completed = True
        
        # Агрегация прогресса: проверяем родителя
        if node.parent_id:
            parent = db.query(KnowledgeNode).filter(KnowledgeNode.id == node.parent_id).first()
            if parent:
                # Проверяем всех детей
                children = db.query(KnowledgeNode).filter(KnowledgeNode.parent_id == parent.id).all()
                all_children_completed = all(child.is_completed for child in children) # node уже обновлен в сессии (is_completed=True)
                
                if all_children_completed:
                    parent.is_completed = True
                    # Здесь можно добавить логику разблокировки следующих узлов, если они зависят от parent
        
        db.commit()
    
    return {
        "status": "ok",
        "passed": is_passed,
        "score": f"{correct_count}/{total_questions}",
        "is_completed": node.is_completed
    }

@app.post("/api/nodes/{node_id}/subtopics")
async def generate_subtopics(node_id: int, db: Session = Depends(get_db)):
    """
    Генерирует 3 подтемы для указанного узла, сохраняя контекст.
    """
    parent_node = db.query(KnowledgeNode).filter(KnowledgeNode.id == node_id).first()
    if not parent_node:
        raise HTTPException(status_code=404, detail="Node not found")

    prompt = f"""
    Тема курса (родительский узел): "{parent_node.label}".
    Описание: "{parent_node.description}".
    
    Твоя задача: Сгенерируй ровно 3 подтемы (subtopics) для этой темы, чтобы углубить знания студента.
    Это должны быть конкретные, узкие аспекты родительской темы.
    
    Верни строго JSON массив объектов:
    [
        {{ "label": "Название подтемы 1", "description": "Краткое описание" }},
        {{ "label": "Название подтемы 2", "description": "Краткое описание" }},
        {{ "label": "Название подтемы 3", "description": "Краткое описание" }}
    ]
    """

    try:
        content = await call_ai(
            prompt=prompt, 
            system="Ты — методист образовательных программ. Отвечай только строгим JSON."
        )

        # Очистка
        content = content.strip()
        if content.startswith('```json'): content = content[7:]
        if content.startswith('```'): content = content[3:]
        if content.endswith('```'): content = content[:-3]
        content = content.strip()
        
        # Парсинг
        parsed = json.loads(content)
        subtopics_data = []
        if isinstance(parsed, dict) and "subtopics" in parsed:
            subtopics_data = parsed["subtopics"]
        elif isinstance(parsed, list):
            subtopics_data = parsed
        
        # Сохраняем в БД
            created_subtopics = []
            for sub in subtopics_data:
                label = sub.get("label")
                if not label: continue
                
                # Проверяем, нет ли уже такого под-узла у этого родителя
                existing_child = db.query(KnowledgeNode).filter(
                    KnowledgeNode.label == label,
                    KnowledgeNode.parent_id == parent_node.id
                ).first()

                if existing_child:
                    # Если уже есть, просто возвращаем его ID, не создавая дубль
                    created_subtopics.append({
                        "id": existing_child.id,
                        "label": existing_child.label
                    })
                    continue

                # Создаем новый узел
                new_node = KnowledgeNode(
                    label=label,
                    description=sub.get("description", ""),
                    level=parent_node.level + 1,
                    is_completed=False,
                    prerequisites=[parent_node.id], # Зависит от родителя
                    parent_id=parent_node.id
                )
                db.add(new_node)
                db.flush()
                
                # Создаем ребро
                new_edge = KnowledgeEdge(source_id=parent_node.id, target_id=new_node.id)
                db.add(new_edge)
                
                created_subtopics.append({
                    "id": new_node.id,
                    "label": new_node.label
                })
            
            db.commit()
            return {"status": "ok", "subtopics": created_subtopics}

    except Exception as e:
        db.rollback()
        print(f"Subtopics Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-course")
async def generate_course(request: CourseGenerationRequest, db: Session = Depends(get_db)):
    """
    Генерирует дорожную карту курса (10-15 узлов) по заданной теме и сохраняет в БД.
    """
    # 0. Удаляем тестовые узлы
    db.query(KnowledgeNode).filter(KnowledgeNode.label.like("%Тестовый%")).delete(synchronize_session=False)
    db.commit()

    topic = request.topic
    
    prompt = f"""
    Создай подробную дорожную карту изучения темы "{topic}".
    Сгенерируй от 10 до 15 узлов (тем), выстроенных в логической последовательности от простого к сложному.
    
    Верни строго валидный JSON массив объектов. Без markdown, без ```json.
    
    Формат каждого объекта:
    {{
        "id": int, (временный ID внутри этого списка, начиная с 1)
        "label": "Название темы",
        "description": "Краткое описание (1 предложение)",
        "level": int, (уровень сложности от 1 до 5)
        "prerequisites": [int] (список временных ID тем, которые нужно изучить ДО этой темы)
    }}
    
    Пример:
    [
        {{"id": 1, "label": "Введение", "description": "...", "level": 1, "prerequisites": []}},
        {{"id": 2, "label": "Основы", "description": "...", "level": 1, "prerequisites": [1]}}
    ]
    """

    print(f"Генерация курса '{topic}'...")

    try:
        content = await call_ai(
            prompt=prompt,
            system="Ты — методист образовательных программ. Ты отвечаешь только строгим JSON."
        )

        # Очистка от markdown
        clean_text = content.replace("```json", "").replace("```", "").strip()
        
        nodes_data = json.loads(clean_text)
        
        # Сохранение в БД
        # Нам нужно сопоставить временные ID (из JSON) с реальными ID в БД
        temp_id_map = {} # temp_id -> db_id
        
        # 1. Сначала создаем все узлы без связей
        created_nodes = []
        for node_data in nodes_data:
            # Проверяем, нет ли уже узла с таким именем, чтобы не дублировать
            existing = db.query(KnowledgeNode).filter(KnowledgeNode.label == node_data["label"]).first()
            if existing:
                temp_id_map[node_data["id"]] = existing.id
                continue

            new_node = KnowledgeNode(
                label=node_data["label"],
                description=node_data.get("description", ""),
                level=node_data.get("level", 1),
                is_completed=False,
                prerequisites=[] # Пока пусто
            )
            db.add(new_node)
            db.flush() # Получаем ID, но не коммитим пока всё
            temp_id_map[node_data["id"]] = new_node.id
            created_nodes.append((new_node, node_data["prerequisites"]))
        
        # 2. Теперь проставляем зависимости (prerequisites) и создаем ребра
        for node, prereqs_temp_ids in created_nodes:
            real_prereqs_ids = []
            for temp_id in prereqs_temp_ids:
                if temp_id in temp_id_map:
                    real_id = temp_id_map[temp_id]
                    real_prereqs_ids.append(real_id)
                    
                    # Создаем ребро для визуализации
                    # Проверяем существование ребра
                    edge_exists = db.query(KnowledgeEdge).filter(
                        KnowledgeEdge.source_id == real_id,
                        KnowledgeEdge.target_id == node.id
                    ).first()
                    
                    if not edge_exists:
                        new_edge = KnowledgeEdge(source_id=real_id, target_id=node.id)
                        db.add(new_edge)

            # Обновляем поле prerequisites у узла
            node.prerequisites = real_prereqs_ids
        
        db.commit()
        
        return {"status": "ok", "message": f"Course '{topic}' generated successfully", "nodes_count": len(nodes_data)}

    except Exception as e:
        db.rollback()
        print(f"Course Generation Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate course: {str(e)}")

@app.post("/api/courses/generate")
async def generate_course_smart(request: CourseGenerationRequest, db: Session = Depends(get_db)):
    """
    Умная генерация курса по названию темы. Создает структуру из 10-12 тем с зависимостями по названиям.
    Полностью изолированный метод без litellm и без print-ов для предотвращения ошибок кодировки.
    """
    topic = request.topic

    # Очистка от мусора (тестовых узлов), если они есть
    db.query(KnowledgeNode).filter(KnowledgeNode.label.like("Тестовый узел%")).delete(synchronize_session=False)
    db.commit()
    
    prompt = f"""
    Создай логическую структуру учебного курса по теме "{topic}".
    Курс должен состоять из 10-12 взаимосвязанных тем (уроков), от простого к сложному.
    
    Верни строго валидный JSON массив объектов. Без markdown, без ```json.
    
    Формат объекта:
    {{
        "title": "Название темы",
        "description": "Краткое описание (1 предложение)",
        "list_of_prerequisite_titles": ["Точное название предыдущей темы 1", "Точное название предыдущей темы 2"]
    }}
    
    В поле list_of_prerequisite_titles указывай только названия тем, которые есть в этом же списке (сгенерированном тобой). 
    Для первой темы список должен быть пустым.
    """

    try:
        ai_content = await call_ai(
            prompt=prompt,
            system="Ты — архитектор образовательных программ. Ты отвечаешь только строгим JSON."
        )

        # Очистка контента от markdown
        ai_content = ai_content.strip()
        if ai_content.startswith('```json'):
            ai_content = ai_content[7:]
        elif ai_content.startswith('```'):
            ai_content = ai_content[3:]
        if ai_content.endswith('```'):
            ai_content = ai_content[:-3]
        ai_content = ai_content.strip()

        try:
            nodes_data = json.loads(ai_content)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="AI returned invalid JSON structure")
        
        # Логика сохранения в БД
        title_to_id = {}
        created_nodes = []

        for node_data in nodes_data:
            title = node_data["title"]
            existing = db.query(KnowledgeNode).filter(KnowledgeNode.label == title).first()
            
            if existing:
                title_to_id[title] = existing.id
                created_nodes.append((existing, node_data.get("list_of_prerequisite_titles", [])))
            else:
                new_node = KnowledgeNode(
                    label=title,
                    description=node_data.get("description", ""),
                    level=1,
                    is_completed=False,
                    prerequisites=[]
                )
                db.add(new_node)
                db.flush()
                title_to_id[title] = new_node.id
                created_nodes.append((new_node, node_data.get("list_of_prerequisite_titles", [])))
        
        for node, prereq_titles in created_nodes:
            current_prereqs = node.prerequisites or []
            new_prereq_ids = []
            
            for p_title in prereq_titles:
                if p_title in title_to_id:
                    p_id = title_to_id[p_title]
                    if p_id != node.id:
                         new_prereq_ids.append(p_id)
                         
                         edge_exists = db.query(KnowledgeEdge).filter(
                            KnowledgeEdge.source_id == p_id,
                            KnowledgeEdge.target_id == node.id
                         ).first()
                         if not edge_exists:
                             db.add(KnowledgeEdge(source_id=p_id, target_id=node.id))
            
            updated_prereqs = list(set(current_prereqs + new_prereq_ids))
            node.prerequisites = updated_prereqs

        db.commit()
        return {"status": "ok", "message": f"Course '{topic}' generated.", "nodes_count": len(nodes_data)}

    except Exception as e:
        db.rollback()
        # Переводим всю ошибку в безопасный ASCII, заменяя опасные символы на '?'
        safe_trace = traceback.format_exc().encode('ascii', 'replace').decode('ascii')
        # Отправляем ошибку на фронтенд, а не в консоль
        raise HTTPException(status_code=500, detail=safe_trace)

@app.get("/api/explain/{topic}", response_model=ExplanationResponse)
async def explain_topic(topic: str, model: str = "groq/llama-3.3-70b-versatile"):
    """
    Генерирует короткое объяснение темы с помощью ИИ (через прямой запрос к Groq).
    """
    try:
        content = await call_ai(
            prompt=f"Объясни тему: {topic}",
            system="Ты — опытный и дружелюбный репетитор по программированию. Объясни тему кратко (2-3 предложения), просто и понятно для новичка.",
            json_mode=False
        )
        return ExplanationResponse(explanation=content)

    except Exception as e:
        safe_trace = traceback.format_exc().encode('ascii', 'replace').decode('ascii')
        raise HTTPException(status_code=500, detail=safe_trace)

import json

@app.get("/api/quiz/{topic}", response_model=QuizResponse)
async def get_quiz(topic: str, model: str = "groq/llama-3.3-70b-versatile", db: Session = Depends(get_db)):
    """
    Генерирует 3 вопроса с вариантами ответов по теме через Groq.
    """
    # Получаем детали узла из базы данных для контекста
    node = db.query(KnowledgeNode).filter(KnowledgeNode.label == topic).first()
    description = node.description if node else "Нет описания"

    prompt = f"""
    Ты — ведущий методолог онлайн-образования, Chief Product Officer c 15 летним опытом работы и Founder стартапа с оценкой больше 1 миллиарда долларов. 
    Твоя задача: генерировать проверочные тесты на основе темы и описания узла курса.

    ПРАВИЛА ГЕНЕРАЦИИ:
    1. КРЕАТИВНОСТЬ: Вопросы должны быть ситуативными (Case-based), имитировать реальные задачи стартапа или бизнеса.
    2. СТРУКТУРА: Каждый вопрос должен содержать 4 варианта ответа, где только ОДИН является верным.
    3. ДИСТРАКТОРЫ: Неправильные ответы должны быть логичными и правдоподобными, чтобы исключить угадывание.
    4. ФОРМАТ: Возвращай строго чистый JSON без вступительных слов.

    СТРУКТУРА JSON:
    {{
      "questions": [
        {{
          "question": "Текст вопроса (бизнес-кейс)...",
          "options": ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
          "correct_answer": 0,
          "explanation": "Краткое объяснение, почему именно этот выбор логически верен в контексте JTBD/Метрик."
        }}
      ]
    }}

    ВХОДНЫЕ ДАННЫЕ:
    Тема: {topic}
    Описание темы: {description}
    """
    
    try:
        content = await call_ai(
            prompt=prompt,
            system="Ты — генератор тестов. Твой ответ должен быть СТРОГО валидным JSON без каких-либо вступительных слов или markdown разметки."
        )

        # Очистка от markdown
        content = content.strip()
        if content.startswith('```json'):
            content = content[7:]
        elif content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()
        
        # Парсинг JSON ответа
        try:
            parsed = json.loads(content)
                questions_data = []

                # Если вернулся словарь с ключом questions (как мы просили в новом промпте)
                if isinstance(parsed, dict) and "questions" in parsed:
                    questions_data = parsed["questions"]
                # Fallback: если вернулся список
                elif isinstance(parsed, list):
                    questions_data = parsed
                
                # Валидация полей (убедимся, что correct_answer это int)
                valid_questions = []
                for q in questions_data:
                    if "question" in q and "options" in q and "correct_answer" in q:
                         # Иногда модели могут вернуть строку вместо числа, починим
                         if isinstance(q["correct_answer"], str):
                             if q["correct_answer"].isdigit():
                                 q["correct_answer"] = int(q["correct_answer"])
                             else:
                                 # Если вернул "A", "B"... или текст ответа, попробуем найти индекс или дефолт
                                 q["correct_answer"] = 0 
                         
                         valid_questions.append(q)
                
                questions_data = valid_questions

            except json.JSONDecodeError:
                 raise HTTPException(status_code=500, detail="Invalid JSON from AI")

            return QuizResponse(questions=questions_data)

    except Exception as e:
        safe_trace = traceback.format_exc().encode('ascii', 'replace').decode('ascii')
        # Возвращаем пустой тест с ошибкой, чтобы фронт не падал жестко, или 500
        # Но лучше вернуть ошибку, чтобы видеть в консоли
        raise HTTPException(status_code=500, detail=safe_trace)
