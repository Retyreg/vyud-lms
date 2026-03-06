from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser

# Инициализация модели (API Key должен быть в .env)
llm = ChatGoogleGenerativeAI(model="gemini-pro", convert_system_message_to_human=True)

mentor_prompt = ChatPromptTemplate.from_template(
    """
    Ты — ИИ-ментор на платформе VYUD LMS.
    Контекст текущего урока: {lesson_content}
    Вопрос студента: {student_question}
    
    Отвечай кратко, мотивирующе и по существу. Используй примеры кода, если нужно.
    """
)

mentor_chain = mentor_prompt | llm | StrOutputParser()

async def get_ai_response(lesson_content: str, question: str):
    return await mentor_chain.ainvoke({
        "lesson_content": lesson_content,
        "student_question": question
    })
