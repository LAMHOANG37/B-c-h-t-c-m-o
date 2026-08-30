import re
import json
from typing import Dict, Any, Optional
from services.llm_client import llm_client, strip_think_tags
from config import NICHE_TOPIC

class SceneRepairStudio:
    """
    Trình Sửa & Tối Ưu Phân Cảnh (Scene Repair Studio):
    Cho phép biên tập, viết lại hoặc render lại đúng 1 phân cảnh bị lỗi mà không cần làm lại từ đầu.
    """

    @classmethod
    async def repair_scene(
        cls,
        topic: str,
        scene_number: int,
        current_script: str,
        repair_instruction: str
    ) -> Dict[str, Any]:
        """
        Viết lại đúng 1 phân cảnh (scene_number) dựa trên yêu cầu chỉnh sửa.
        """
        system_prompt = f"""You are an elite YouTube Video Editor and Script Doctor in niche {NICHE_TOPIC}.
Your task is to REPAIR and REWRITE ONLY Scene {scene_number} of the given script based on the user's specific repair instructions.

Keep the tone engaging, concise and scientifically accurate.
Return ONLY valid JSON:
{{
  "scene_number": {scene_number},
  "repaired_title": "Tên phân cảnh mới",
  "voiceover_vn": "Lời thoại tiếng Việt được viết lại (2-3 câu súc tích, tự nhiên)",
  "image_prompt_en": "Ultra-detailed Midjourney/Flux prompt in English for this specific scene",
  "video_prompt_en": "Runway/Kling video motion prompt in English",
  "sfx_description": "Mô tả âm thanh hiệu ứng",
  "repair_summary": "Tóm tắt những điểm đã cải tiến"
}}
"""
        user_prompt = f"Topic: {topic}\nScene to Repair: Scene {scene_number}\nInstructions: {repair_instruction}\nCurrent Script Context (Excerpt):\n{current_script[:1000]}"

        try:
            res = await llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            content = strip_think_tags(res.get("content", ""))
            if "{" in content and "}" in content:
                json_str = content[content.find("{"):content.rfind("}") + 1]
                data = json.loads(json_str)
                data["status"] = "success"
                return data
        except Exception as e:
            pass

        return {
            "status": "error",
            "message": "Không thể tối ưu lại phân cảnh."
        }

scene_repair_studio = SceneRepairStudio()
