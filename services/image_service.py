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
    async def craft_visual_prompt(
        user_idea: str,
        topic: Optional[str] = None,
        scientific_details: Optional[str] = None,
        style: str = "3D Cinematic"
    ) -> Dict[str, str]:
        """
        Dùng Gemini hoặc Groq LLM để chuyển đổi ý tưởng thô thành Prompt AI đỉnh cao,
        bắt buộc giữ đúng ngữ cảnh chủ đề khoa học và chạy self-check chống lạc đề.
        """
        effective_topic = (topic or user_idea).strip()
        details_context = f"\nSpecific Scientific Elements/Context: {scientific_details}" if scientific_details else ""

        system_prompt = f"""You are an elite AI Art Director specializing in hyper-accurate YouTube Thumbnails and scientific CGI visual prompts.
Your mission is to convert the specific concept into an extraordinary, ultra-detailed English Prompt for Midjourney v6, Flux, and DALL-E 3.

CRITICAL RULES:
1. Write the prompt entirely in English.
2. The prompt MUST BE 100% SPECIFIC TO THE TOPIC: "{effective_topic}". Never produce vague, generic or off-topic imagery!
3. Include specific scientific visual elements (e.g. microscopic molecular physics, Rayleigh light scattering, cross-section anatomy, thermal gradients, neon energy flow).
4. Composition: Dynamic 1/3 grid, extreme close-up or 3D cross-section, high contrast complementary colors, volumetric studio lighting, 8k octane render.
5. Return ONLY valid JSON format:
{{
  "optimized_prompt": "Ultra-detailed prompt in English specifically depicting {effective_topic}...",
  "concept_title": "Short title in Vietnamese",
  "style_used": "Style applied"
}}
"""
        user_prompt = f"Topic/Concept: {effective_topic}\nUser Idea: {user_idea}{details_context}\nDesired Style: {style}"

        candidate_prompt = None
        concept_title = effective_topic
        used_style = style
        used_model = "Google Gemini 3.6 Flash"
        latency_ms = 0.0

        # 1. Thử qua Gemini API trực tiếp nếu có key
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        if gemini_key:
            try:
                import time
                t0 = time.perf_counter()
                from google import genai
                from services.quota_tracker import quota_tracker
                client = genai.Client(api_key=gemini_key)
                
                loop = asyncio.get_running_loop()
                res = await loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=f"{system_prompt}\n\n{user_prompt}"
                    )
                )
                latency_ms = (time.perf_counter() - t0) * 1000
                quota_tracker.add_gemini_request(latency_ms=latency_ms, is_image_flow=True)

                content = res.text
                if "{" in content and "}" in content:
                    json_str = content[content.find("{"):content.rfind("}") + 1]
                    data = json.loads(json_str)
                    candidate_prompt = data.get("optimized_prompt")
                    concept_title = data.get("concept_title", effective_topic)
                    used_style = data.get("style_used", style)
            except Exception as e:
                pass

        # 2. Fallback qua LLM Client (Groq) nếu chưa có prompt
        if not candidate_prompt:
            try:
                res = await llm_client.chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.6,
                    max_tokens=400
                )
                content = strip_think_tags(res.get("content", ""))
                if "{" in content and "}" in content:
                    json_str = content[content.find("{"):content.rfind("}") + 1]
                    data = json.loads(json_str)
                    candidate_prompt = data.get("optimized_prompt")
                    concept_title = data.get("concept_title", effective_topic)
                    used_style = data.get("style_used", style)
                    used_model = "Groq LPU"
            except Exception:
                pass

        # 3. BƯỚC SELF-CHECK CHỐNG LẠC ĐỀ (Tối đa 1 lần kiểm tra & viết lại nếu chung chung)
        if candidate_prompt:
            try:
                check_prompt = f"""Review this image prompt for the topic "{effective_topic}":
Candidate Prompt: "{candidate_prompt}"

Question: Does this prompt specifically and vividly illustrate "{effective_topic}" with accurate visual elements, or is it generic/off-topic?
If specific, reply JSON: {{"is_on_topic": true}}
If generic/off-topic, rewrite a sharp specific prompt in JSON: {{"is_on_topic": false, "revised_prompt": "Ultra-detailed prompt explicitly illustrating {effective_topic}..."}}
"""
                check_res = await llm_client.chat_completion(
                    messages=[{"role": "user", "content": check_prompt}],
                    temperature=0.3,
                    max_tokens=300
                )
                check_text = strip_think_tags(check_res.get("content", ""))
                if "{" in check_text and "}" in check_text:
                    check_data = json.loads(check_text[check_text.find("{"):check_text.rfind("}") + 1])
                    if not check_data.get("is_on_topic", True) and check_data.get("revised_prompt"):
                        candidate_prompt = check_data["revised_prompt"]
            except Exception:
                pass

        # 4. Fallback động (Dynamic Fallback): Chèn trực tiếp topic và chi tiết cụ thể, không dùng template tĩnh
        if not candidate_prompt:
            spec_detail = scientific_details or "microscopic interactions, cross-section visualization and dynamic physics simulation"
            candidate_prompt = f"3D volumetric scientific render of {effective_topic}, featuring {spec_detail}, extreme detail, vibrant cinematic color contrast, atmospheric studio lighting, 8k resolution, photorealistic octane render"
            used_model = "Dynamic Topic-Locked Fallback"

        return {
            "prompt": candidate_prompt,
            "title": concept_title,
            "style": used_style,
            "model": used_model,
            "latency_ms": latency_ms
        }

    @classmethod
    async def generate_image(
        cls,
        prompt_or_idea: str,
        topic: Optional[str] = None,
        scientific_details: Optional[str] = None,
        style: str = "3D Cinematic Masterpiece",
        width: int = 1280,
        height: int = 720,
        enhance_prompt: bool = True
    ) -> Dict[str, Any]:
        """
        Tự động viết prompt bám sát chủ đề và vẽ ảnh, lưu vào reports/images/ và trả về đường dẫn file.
        """
        if enhance_prompt:
            crafted = await cls.craft_visual_prompt(
                user_idea=prompt_or_idea,
                topic=topic,
                scientific_details=scientific_details,
                style=style
            )
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
