from fastapi import APIRouter, Depends
from schemas import schemas
from services.ai.ai_assistant import AIAssistant

router = APIRouter()
assistant = AIAssistant()

@router.post("/chat", response_model=schemas.ChatResponse)
def chat(message: schemas.ChatMessage):
    reply = assistant.answer(message.message, message.language, {})
    return {"reply": reply}
