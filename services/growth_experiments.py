import json
from typing import Dict, Any, Optional
from services.llm_client import llm_client, strip_think_tags
from config import NICHE_TOPIC

class GrowthExperimentsStudio:
    """
    Phòng Thí Nghiệm Tăng Trưởng (A/B Testing Studio):
    Tạo ra 2 chiến lược đóng gói video đối kháng (Arm A vs Arm B) để thử nghiệm tối đa hóa CTR và Retention.
    """

    @classmethod
    async def generate_ab_experiment(cls, topic: str) -> Dict[str, Any]:
        system_prompt = f"""You are a master YouTube Growth Hacker specializing in A/B Testing, Viral Hooks and CTR Optimization in niche {NICHE_TOPIC}.
Given a topic, generate TWO distinct, competing packaging strategies (Arm A vs Arm B).

CRITICAL DIFFERENCES BETWEEN THE TWO STRATEGIES:
- **Arm A (Curiosity & Paradox Hook):** Focuses on a mind-bending question or scientific paradox ("Why do 99% of people believe X when Y happens?").
- **Arm B (Urgency / High Stakes / Drama Hook):** Focuses on direct impact, dramatic consequences, or fascinating physical danger ("What actually happens if you touch X?").

Return ONLY valid JSON:
{{
  "topic": "{topic}",
  "arm_a": {{
    "strategy_name": "Tò Mò Nghịch Lý (Curiosity)",
    "title_vn": "Tiêu đề tiếng Việt phương án A",
    "hook_3s": "Hook 3 giây mở đầu",
    "thumbnail_concept": "Mô tả hình ảnh thumbnail A",
    "thumbnail_prompt": "Midjourney/Flux prompt in English for Arm A",
    "target_psychology": "Tâm lý khán giả nhắm tới"
  }},
  "arm_b": {{
    "strategy_name": "Kịch Tính & Cảnh Báo (High Stakes)",
    "title_vn": "Tiêu đề tiếng Việt phương án B",
    "hook_3s": "Hook 3 giây mở đầu",
    "thumbnail_concept": "Mô tả hình ảnh thumbnail B",
    "thumbnail_prompt": "Midjourney/Flux prompt in English for Arm B",
    "target_psychology": "Tâm lý khán giả nhắm tới"
  }},
  "recommendation": "Đánh giá chuyên gia nên test phương án nào trước"
}}
"""
        user_prompt = f"Tạo thử nghiệm A/B Testing Title & Thumbnail cho chủ đề: '{topic}'"

        try:
            res = await llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1500
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
            "status": "partial",
            "topic": topic,
            "arm_a": {
                "strategy_name": "Tò Mò Nghịch Lý",
                "title_vn": f"Bí Ẩn Đằng Sau '{topic}' Mà 90% Mọi Người Hiểu Sai!",
                "hook_3s": f"Bạn có bao giờ tự hỏi vì sao {topic} lại diễn ra?",
                "thumbnail_concept": "Mặt cắt 3D phát sáng đối lập",
                "thumbnail_prompt": f"3D scientific cross-section of {topic}, dramatic studio lighting, 8k"
            },
            "arm_b": {
                "strategy_name": "Kịch Tính Cảnh Báo",
                "title_vn": f"Điều Gì Sẽ Xảy Ra Nếu {topic} Biến Mất?",
                "hook_3s": f"Nếu một ngày {topic} không còn nữa, đây là những gì sẽ xảy ra!",
                "thumbnail_concept": "Tương phản màu đỏ cam cảnh báo",
                "thumbnail_prompt": f"Extreme dramatic illustration of {topic}, red and cyan volumetric light, 8k"
            },
            "recommendation": "Nên test phương án A cho video Shorts tò mò, phương án B cho video dài."
        }

growth_experiments = GrowthExperimentsStudio()
