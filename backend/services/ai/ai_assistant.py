import io
import logging
import os
import re
from pathlib import Path
from dotenv import load_dotenv
try:
    from sarvamai import SarvamAI
except ImportError:
    SarvamAI = None

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are AgroNex, an AI agricultural assistant for farmers.

You can communicate naturally in Tamil, English, and Tamil-English code-mixed language.

Give practical, simple and safe agricultural guidance. Keep your responses concise, conversational, and direct (within 2-4 sentences) so they are easy to listen to.

If the farmer asks about crop disease, explain possible causes and recommend appropriate next steps.

Never claim a disease is confirmed unless reliable prediction information is provided.

Do not invent weather information. Weather information must come from AgroNex's real weather API when available.

Prefer answering in the same language/style used by the farmer."""

class AIAssistant:
    def __init__(self):
        # Load SARVAM_API_KEY from backend/.env or root .env
        base_dir = Path(__file__).resolve().parents[2]
        load_dotenv(dotenv_path=base_dir / ".env")
        load_dotenv(dotenv_path=base_dir / "backend" / ".env")

        self.api_key = os.environ.get("SARVAM_API_KEY")
        if not self.api_key:
            for candidate in [base_dir / ".env", base_dir / "backend" / ".env"]:
                if candidate.exists():
                    for line in candidate.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if line.startswith("SARVAM_API_KEY="):
                            val = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if val:
                                self.api_key = val
                                break
                if self.api_key:
                    break

        if self.api_key and SarvamAI is not None:
            self.client = SarvamAI(api_subscription_key=self.api_key)
        else:
            self.client = None
            if not SarvamAI:
                logger.warning("sarvamai package is not installed; AI assistant features will operate in fallback mode.")


    def clean_for_tts(self, text: str) -> str:
        """Strip markdown symbols (asterisks, hashtags, bullets) so TTS reads smoothly."""
        clean = re.sub(r'[*_~`#]', '', text)
        clean = re.sub(r'^\s*[-+*]\s+', '', clean, flags=re.MULTILINE)
        clean = re.sub(r'\n+', ' ', clean).strip()
        return clean

    def answer(self, question: str, language: str = "en", context: dict = None) -> str:
        if not self.client:
            if language == "ta":
                return "மன்னிக்கவும், AI சேவைக்கான API சாவி கிடைக்கவில்லை."
            return "AgroNex AI service is temporarily unavailable because the API key is not configured."

        try:
            prompt_modifier = ""
            if language == "ta":
                prompt_modifier = "\nPlease answer primarily in Tamil or natural Tamil-English code-mix as used by Tamil Nadu farmers."
            elif language == "en":
                prompt_modifier = "\nPlease answer in simple, direct English."

            response = self.client.chat.completions(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT + prompt_modifier},
                    {"role": "user", "content": question},
                ],
                model="sarvam-105b-conversations",
            )
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content.strip()
            return "No response received from AI model."
        except Exception as e:
            logger.error(f"Error in chat completion: {e}")
            return "மன்னிக்கவும், பதிலை உருவாக்குவதில் சிக்கல் ஏற்பட்டது. மீண்டும் முயற்சிக்கவும்." if language == "ta" else "Sorry, there was an issue generating a response. Please try again."

    def speech_to_text(self, audio_bytes: bytes, filename: str = "audio.wav") -> tuple[str, str]:
        if not self.client:
            raise RuntimeError("Sarvam client is not configured.")

        # Ensure filename has an appropriate extension
        if "." not in filename:
            filename = f"{filename}.wav"

        response = self.client.speech_to_text.transcribe(
            file=(filename, io.BytesIO(audio_bytes)),
            model="saaras:v4",
            language_code="unknown",
            mode="codemix",
        )
        detected_lang = getattr(response, "language_code", None) or "ta-IN"
        transcript = getattr(response, "transcript", "").strip()
        return detected_lang, transcript

    def text_to_speech(self, text: str, language_code: str = "ta-IN") -> str | None:
        if not self.client:
            return None

        try:
            tts_lang = language_code if language_code in ["ta-IN", "en-IN", "hi-IN", "te-IN", "kn-IN", "ml-IN"] else "ta-IN"
            clean_text = self.clean_for_tts(text)

            response = self.client.text_to_speech.convert(
                text=clean_text,
                language_code=tts_lang,
                model="bulbul:v3",
                output_audio_codec="wav",
            )
            if response and response.audios and len(response.audios) > 0:
                return response.audios[0]
        except Exception as e:
            logger.error(f"TTS conversion failed: {e}")
        return None

    def process_voice_chat(self, audio_bytes: bytes, filename: str = "audio.wav", preferred_language: str = "ta") -> dict:
        # Step 1: Speech-to-Text (Saaras v4)
        detected_lang = "ta-IN" if "ta" in preferred_language else "en-IN"
        transcript = ""
        try:
            detected_lang, transcript = self.speech_to_text(audio_bytes, filename=filename)
        except Exception as e:
            logger.error(f"STT processing failed: {e}")

        if not transcript:
            fallback_msg = "மன்னிக்கவும், உங்கள் குரல் தெளிவாகக் கேட்கவில்லை. மீண்டும் பேசவும் அல்லது தட்டச்சு செய்யவும்." if "ta" in preferred_language else "Sorry, I could not hear any speech clearly. Please try again or type your question."
            audio_data = self.text_to_speech(fallback_msg, language_code="ta-IN" if "ta" in preferred_language else "en-IN")
            return {
                "detected_language": detected_lang or "unknown",
                "transcription": "",
                "reply": fallback_msg,
                "audio_base64": audio_data,
            }

        # Step 2: Sarvam-105B Chatbot
        ai_reply = self.answer(transcript, language="ta" if "ta" in detected_lang else preferred_language)

        # Step 3: Text-to-Speech (Bulbul v3)
        audio_base64 = self.text_to_speech(ai_reply, language_code=detected_lang)

        return {
            "detected_language": detected_lang,
            "transcription": transcript,
            "reply": ai_reply,
            "audio_base64": audio_base64,
        }
