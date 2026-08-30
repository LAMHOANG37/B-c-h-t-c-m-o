import os
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
import edge_tts
from config import BASE_DIR

AUDIO_DIR = BASE_DIR / "reports" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

class TTSService:
    """
    Dịch vụ chuyển văn bản thành giọng đọc (Text-to-Speech) tiếng Việt chất lượng cao chuẩn Studio.
    Sử dụng Microsoft Edge Neural Voices (Hoàn toàn miễn phí, không giới hạn).
    """

    VOICES = {
        "nam_tram": "vi-VN-NamMinhNeural",     # Nam trầm ấm, chuẩn kể chuyện khoa học / vũ trụ
        "nu_truyencam": "vi-VN-HoaiMyNeural",  # Nữ truyền cảm, tự nhiên, cuốn hút
    }

    @classmethod
    async def synthesize_speech(
        cls,
        text: str,
        voice: str = "nam_tram",
        rate: str = "+0%",
        pitch: str = "+0Hz",
        output_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Tổng hợp giọng đọc tiếng Việt và lưu file .mp3.
        """
        clean_text = text.strip()
        if not clean_text:
            return {"status": "error", "message": "Nội dung văn bản trống."}

        voice_id = cls.VOICES.get(voice, voice)
        
        from datetime import datetime
        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
            output_filename = f"tts_{timestamp}.mp3"

        filepath = AUDIO_DIR / output_filename
        
        try:
            communicate = edge_tts.Communicate(
                text=clean_text,
                voice=voice_id,
                rate=rate,
                pitch=pitch
            )
            await communicate.save(str(filepath))

            # Đo độ dài file âm thanh nếu có thể
            duration_sec = 0.0
            try:
                # Ước lượng 1 từ tiếng Việt đọc khoảng 0.28 giây
                word_count = len(clean_text.split())
                duration_sec = round(word_count * 0.28, 2)
            except Exception:
                pass

            return {
                "status": "success",
                "filepath": str(filepath),
                "filename": output_filename,
                "voice_used": voice_id,
                "word_count": len(clean_text.split()),
                "estimated_duration_sec": duration_sec
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Lỗi tổng hợp giọng đọc: {e}"
            }

tts_service = TTSService()
