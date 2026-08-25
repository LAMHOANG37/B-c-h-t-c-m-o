import os
import sys
import aiohttp
import urllib.parse
import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from config import BASE_DIR
from services.llm_client import llm_client, strip_think_tags

IMAGES_DIR = BASE_DIR / "reports" / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

class ImageGenerationService:
    """
    Dịch vụ tạo ảnh và tối ưu prompt AI đa nền tảng kết hợp Google Gemini và Flux Ultra Engine.
    """

    @staticmethod
    async def craft_visual_prompt(user_idea: str, style: str = "3D Cinematic") -> Dict[str, str]:
        """
        Dùng Gemini hoặc Groq LLM để chuyển đổi ý tưởng thô thành Prompt AI đỉnh cao.
        """
        system_prompt = """You are an elite AI Art Director specializing in YouTube Thumbnails and scientific CGI visual prompts.
Your mission is to convert the user's concept into an extraordinary, ultra-detailed English Prompt for Midjourney v6, Flux, and DALL-E 3.

RULES:
1. Write the prompt entirely in English.
2. Include: Subject, Cinematic Lighting, Dynamic Composition (cross-section, microscopic 1000x or extreme close-up), High Contrast Color Palette (neon glow, deep dark space, thermal contrast), 8k hyper-realistic octane render.
3. Return ONLY valid JSON format:
{
  "optimized_prompt": "Ultra-detailed prompt in English...",
  "concept_title": "Short title in Vietnamese",
  "style_used": "Style applied"
}
"""
        user_prompt = f"Concept: {user_idea}\nDesired Style: {style}"

        # 1. Thử qua Gemini API trực tiếp nếu có key
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        if gemini_key:
            try:
                from google import genai
                client = genai.Client(api_key=gemini_key)
                res = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=f"{system_prompt}\n\n{user_prompt}"
                )
                content = res.text
                if "{" in content and "}" in content:
                    json_str = content[content.find("{"):content.rfind("}") + 1]
                    data = json.loads(json_str)
                    return {
                        "prompt": data.get("optimized_prompt", user_idea),
                        "title": data.get("concept_title", user_idea),
                        "style": data.get("style_used", style),
                        "model": "Google Gemini 3.6 Flash"
                    }
            except Exception as e:
                pass

        # 2. Fallback qua LLM Client (Groq)
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
            if "{" in content and "}" in content:
                json_str = content[content.find("{"):content.rfind("}") + 1]
                data = json.loads(json_str)
                return {
                    "prompt": data.get("optimized_prompt", user_idea),
                    "title": data.get("concept_title", user_idea),
                    "style": data.get("style_used", style),
                    "model": "Groq LPU"
                }
        except Exception:
            pass

        return {
            "prompt": f"{user_idea}, highly detailed scientific illustration, 3D cross-section, volumetric lighting, vibrant contrast, 8k resolution, cinematic masterpiece",
            "title": user_idea,
            "style": style,
            "model": "Default Engine"
        }

    @classmethod
    async def generate_image(
        cls,
        prompt_or_idea: str,
        style: str = "3D Cinematic Masterpiece",
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
            engine_prompt_model = crafted.get("model", "Gemini 3.6 Flash")
        else:
            final_prompt = prompt_or_idea
            title = prompt_or_idea[:30]
            engine_prompt_model = "Direct Prompt"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gen_{timestamp}.png"
        filepath = IMAGES_DIR / filename

        # Render qua Flux Ultra Engine (Chuẩn 4K/HD, tốc độ cao)
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
                            "provider": f"Flow: {engine_prompt_model} + Flux Ultra",
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
