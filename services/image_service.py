import os
import aiohttp
import urllib.parse
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from config import BASE_DIR
from services.llm_client import llm_client, strip_think_tags

IMAGES_DIR = BASE_DIR / "reports" / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

class ImageGenerationService:
    """
    Dịch vụ tạo ảnh và tối ưu prompt AI đa nền tảng:
    - Gemini / Google Imagen 3 (khi có GEMINI_API_KEY)
    - Flux / Pollinations AI Engine (Chất lượng cao, sẵn sàng hoạt động ngay)
    """

    @staticmethod
    async def craft_visual_prompt(user_idea: str, style: str = "3D Cinematic") -> Dict[str, str]:
        """
        Dùng LLM để chuyển đổi ý tưởng thô của người dùng thành Prompt AI đỉnh cao cho Midjourney/Flux/Imagen.
        """
        system_prompt = """
Bạn là Giám Đốc Nghệ Thuật (AI Prompt Master) chuyên tạo prompt vẽ ảnh Thumbnail YouTube và hình minh họa khoa học đỉnh cao.
Nhiệm vụ của bạn là nhận ý tưởng từ người dùng và viết ra 1 Prompt tiếng Anh hoàn hảo, siêu chi tiết cho các mô hình AI (Midjourney v6, Flux, Google Imagen 3, DALL-E 3).

QUY TẮC BẮT BUỘC:
1. Viết prompt hoàn toàn bằng tiếng Anh.
2. Mô tả rõ: Chủ thể chính (Subject), Ánh sáng (Lighting: cinematic, volumetric, neon rim light), Bố cục (Composition: rule of thirds, extreme close-up, cross-section), Màu sắc tương phản (Color Palette: high contrast, vibrant), Độ phân giải (hyper-realistic, 8k, octane render, Unreal Engine 5).
3. KHÔNG viết văn giải thích dài dòng, chỉ trả về đúng định dạng JSON:
{
  "optimized_prompt": "Mô tả chi tiết prompt tiếng Anh...",
  "concept_title": "Tên concept ngắn gọn tiếng Việt",
  "style_used": "Phong cách áp dụng"
}
"""
        user_prompt = f"Ý tưởng người dùng: {user_idea}\nPhong cách mong muốn: {style}"

        try:
            res = await llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=350
            )
            content = strip_think_tags(res.get("content", ""))
            
            import json
            # Cố gắng trích xuất JSON
            if "{" in content and "}" in content:
                json_str = content[content.find("{"):content.rfind("}") + 1]
                data = json.loads(json_str)
                return {
                    "prompt": data.get("optimized_prompt", user_idea),
                    "title": data.get("concept_title", user_idea),
                    "style": data.get("style_used", style)
                }
        except Exception as e:
            print(f"[ImageService] Lỗi craft prompt qua LLM: {e}", flush=True)

        return {
            "prompt": f"{user_idea}, highly detailed scientific illustration, 3D cross-section, volumetric lighting, vibrant contrast, 8k resolution, cinematic masterpiece",
            "title": user_idea,
            "style": style
        }

    @classmethod
    async def generate_image(
        cls,
        prompt_or_idea: str,
        style: str = "Cinematic 3D",
        width: int = 1280,
        height: int = 720,
        enhance_prompt: bool = True
    ) -> Dict[str, Any]:
        """
        Tự động viết prompt và vẽ ảnh, lưu vào reports/images/ và trả về đường dẫn file.
        """
        if enhance_prompt:
            crafted = await cls.craft_visual_prompt(prompt_or_idea, style)
            final_prompt = crafted["prompt"]
            title = crafted["title"]
        else:
            final_prompt = prompt_or_idea
            title = prompt_or_idea[:30]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gen_{timestamp}.png"
        filepath = IMAGES_DIR / filename

        # 1. Thử qua Google Gemini / Imagen nếu có GEMINI_API_KEY
        gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if gemini_api_key:
            try:
                from google import genai
                client = genai.Client(api_key=gemini_api_key)
                result = client.models.generate_images(
                    model='imagen-3.0-generate-002',
                    prompt=final_prompt,
                    config=dict(
                        number_of_images=1,
                        aspect_ratio="16:9" if width > height else "9:16",
                        output_mime_type="image/png"
                    )
                )
                for generated_image in result.generated_images:
                    filepath.write_bytes(generated_image.image.image_bytes)
                    return {
                        "status": "success",
                        "provider": "Google Imagen 3 (Gemini)",
                        "filepath": str(filepath),
                        "filename": filename,
                        "prompt": final_prompt,
                        "title": title
                    }
            except Exception as e:
                print(f"[ImageService] Gemini Imagen gặp sự cố, chuyển sang Flux Engine: {e}", flush=True)

        # 2. Engine Flux / Pollinations AI Engine (Độ nét cao, chạy ngay lập tức)
        encoded_prompt = urllib.parse.quote(final_prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model=flux&nologo=true&seed={int(datetime.now().timestamp())}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=45)) as resp:
                    if resp.status == 200:
                        image_data = await resp.read()
                        filepath.write_bytes(image_data)
                        return {
                            "status": "success",
                            "provider": "Flux Ultra Engine",
                            "filepath": str(filepath),
                            "filename": filename,
                            "prompt": final_prompt,
                            "title": title
                        }
                    else:
                        return {
                            "status": "error",
                            "message": f"Server ảnh phản hồi mã lỗi HTTP {resp.status}"
                        }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Lỗi kết nối khi vẽ ảnh: {e}"
            }

image_service = ImageGenerationService()
