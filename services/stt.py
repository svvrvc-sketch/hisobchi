import os
import logging
from pathlib import Path
from config import GROQ_API_KEY

logger = logging.getLogger(__name__)

async def transcribe_voice(file_path: Path) -> str:
    """
    Ovozli faylni (Telegram OGG) Groq Whisper modeli orqali matnga o'girish.
    Groq Whisper uzbek va rus tillarini juda aniq tushunadi va 1-2 soniyada javob qaytaradi.
    """
    if not GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY sozlanmagan! Ovozli xabarlarni tanish uchun .env faylida "
            "GROQ_API_KEY kalitini ko'rsating (https://console.groq.com dan bepul olinadi)."
        )

    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=GROQ_API_KEY)
        
        with open(file_path, "rb") as audio_file:
            audio_bytes = audio_file.read()
            transcription = await client.audio.transcriptions.create(
                file=(file_path.name, audio_bytes, "audio/ogg"),
                model="whisper-large-v3-turbo",
                language="uz",
                prompt="O'zbekcha moliya va xarajatlar: tushlik, taksi, ming so'm, oylik, eslatma",
                temperature=0.0
            )
            return transcription.text.strip()
    except Exception as e:
        logger.error(f"Ovozni matnga o'girishda xatolik: {e}")
        raise e
