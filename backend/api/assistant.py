from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from typing import Optional
from schemas import schemas
from services.ai.ai_assistant import AIAssistant

router = APIRouter()
assistant = AIAssistant()

@router.post("/chat", response_model=schemas.ChatResponse)
def chat(message: schemas.ChatMessage):
    try:
        lang = message.language or "en"
        reply = assistant.answer(message.message, lang, {})
        audio_base64 = assistant.text_to_speech(reply, language_code="ta-IN" if lang == "ta" else "en-IN")
        return {"reply": reply, "audio_base64": audio_base64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/voice", response_model=schemas.VoiceChatResponse)
async def voice_chat(
    file: UploadFile = File(...),
    language: Optional[str] = Form("ta"),
):
    try:
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file received")

        filename = file.filename or "recording.webm"
        if "." not in filename:
            ct = file.content_type or ""
            if "wav" in ct:
                filename = f"{filename}.wav"
            elif "mp4" in ct:
                filename = f"{filename}.mp4"
            elif "ogg" in ct:
                filename = f"{filename}.ogg"
            else:
                filename = f"{filename}.webm"

        result = assistant.process_voice_chat(
            audio_bytes=audio_bytes,
            filename=filename,
            preferred_language=language or "ta",
            content_type=file.content_type or "audio/wav",
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
