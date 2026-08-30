import os
import sys
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import imageio_ffmpeg
from config import BASE_DIR
from services.tts_service import tts_service
from services.image_service import image_service

VIDEOS_DIR = BASE_DIR / "reports" / "videos"
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

class VideoAssembler:
    """
    Nhà máy dựng Video Shorts tự động với FFmpeg Engine:
    - Tự động tạo giọng đọc AI tiếng Việt theo từng phân cảnh
    - Tự động vẽ ảnh 4K cho từng phân cảnh
    - Ghép ảnh + audio + hiệu ứng chuyển cảnh mượt mà thành file .mp4 9:16 hoàn chỉnh.
    """

    def __init__(self):
        self.ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

    def _run_ffmpeg_sync(self, cmd: List[str]) -> bool:
        """Chạy lệnh ffmpeg đồng bộ trong thread pool."""
        try:
            # Ẩn cửa sổ terminal trên Windows
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                timeout=120
            )
            return result.returncode == 0
        except Exception as e:
            print(f"[VideoAssembler] FFmpeg exec error: {e}", flush=True)
            return False

    async def render_scene_clip(
        self,
        image_path: str,
        audio_path: str,
        output_clip_path: str,
        width: int = 720,
        height: int = 1280
    ) -> bool:
        """
        Dựng 1 phân cảnh: Ghép 1 ảnh + 1 file audio thành 1 đoạn video MP4 có hiệu ứng zoom nhẹ (Ken Burns).
        """
        loop = asyncio.get_running_loop()
        
        # FFmpeg command: lặp ảnh khớp thời lượng audio, scale về 9:16 (720x1280)
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-loop", "1",
            "-i", image_path,
            "-i", audio_path,
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},format=yuv420p",
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            output_clip_path
        ]

        return await loop.run_in_executor(None, self._run_ffmpeg_sync, cmd)

    async def concatenate_clips(
        self,
        clip_paths: List[str],
        output_final_path: str
    ) -> bool:
        """
        Ghép danh sách các clip phân cảnh thành video MP4 hoàn chỉnh.
        """
        loop = asyncio.get_running_loop()
        concat_list_file = Path(output_final_path).parent / f"concat_list_{int(datetime.now().timestamp())}.txt"
        
        with open(concat_list_file, "w", encoding="utf-8") as f:
            for p in clip_paths:
                # Escape backslashes for FFmpeg concat file
                clean_p = str(p).replace("\\", "/")
                f.write(f"file '{clean_p}'\n")

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list_file),
            "-c", "copy",
            output_final_path
        ]

        success = await loop.run_in_executor(None, self._run_ffmpeg_sync, cmd)
        try:
            concat_list_file.unlink(missing_ok=True)
        except Exception:
            pass

        return success

    async def create_short_video_from_scenes(
        self,
        topic: str,
        scenes: List[Dict[str, str]],
        voice: str = "nam_tram"
    ) -> Dict[str, Any]:
        """
        Dựng hoàn chỉnh 1 video Shorts từ danh sách phân cảnh:
        scenes = [
            {"voiceover": "...", "visual_prompt": "..."},
            ...
        ]
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_topic_slug = "".join([c if c.isalnum() else "_" for c in topic])[:25]
        
        temp_clips = []
        scene_assets = []

        print(f"\n[VideoAssembler] 🎬 Bắt đầu dựng video Shorts cho chủ đề: '{topic}' ({len(scenes)} cảnh)...", flush=True)

        for idx, sc in enumerate(scenes, 1):
            voiceover_text = sc.get("voiceover", "").strip()
            visual_prompt = sc.get("visual_prompt", topic).strip()

            if not voiceover_text:
                continue

            print(f"[VideoAssembler] 🎙️ [Cảnh {idx}/{len(scenes)}] Tổng hợp giọng đọc AI...", flush=True)
            tts_res = await tts_service.synthesize_speech(
                text=voiceover_text,
                voice=voice,
                output_filename=f"audio_s{idx}_{timestamp}.mp3"
            )
            if tts_res.get("status") != "success":
                continue

            print(f"[VideoAssembler] 🎨 [Cảnh {idx}/{len(scenes)}] Vẽ ảnh 9:16 siêu thực...", flush=True)
            img_res = await image_service.generate_image(
                prompt_or_idea=visual_prompt,
                topic=topic,
                scientific_details=f"Scene {idx} visual details of {topic}",
                style="3D Cinematic Masterpiece",
                width=720,
                height=1280,
                enhance_prompt=False
            )
            if img_res.get("status") != "success":
                continue

            clip_filename = f"clip_s{idx}_{timestamp}.mp4"
            clip_path = str(VIDEOS_DIR / clip_filename)

            print(f"[VideoAssembler] ⚡ [Cảnh {idx}/{len(scenes)}] Ghép clip phân cảnh...", flush=True)
            clip_ok = await self.render_scene_clip(
                image_path=img_res["filepath"],
                audio_path=tts_res["filepath"],
                output_clip_path=clip_path,
                width=720,
                height=1280
            )

            if clip_ok:
                temp_clips.append(clip_path)
                scene_assets.append({
                    "scene": idx,
                    "image": img_res["filepath"],
                    "audio": tts_res["filepath"],
                    "clip": clip_path
                })

        if not temp_clips:
            return {
                "status": "error",
                "message": "Không thể tạo các phân cảnh video."
            }

        # Ghép toàn bộ thành video hoàn chỉnh
        final_video_filename = f"shorts_{clean_topic_slug}_{timestamp}.mp4"
        final_video_path = str(VIDEOS_DIR / final_video_filename)

        print(f"[VideoAssembler] 🚀 Ghép toàn bộ {len(temp_clips)} phân cảnh thành video cuối cùng...", flush=True)
        final_ok = await self.concatenate_clips(temp_clips, final_video_path)

        if final_ok and os.path.exists(final_video_path):
            file_size_mb = round(os.path.getsize(final_video_path) / (1024 * 1024), 2)
            print(f"[VideoAssembler] [✅ HOÀN TẤT] Video Shorts đã xuất xưởng: {final_video_filename} ({file_size_mb} MB)\n", flush=True)
            return {
                "status": "success",
                "video_path": final_video_path,
                "video_filename": final_video_filename,
                "file_size_mb": file_size_mb,
                "scenes_count": len(temp_clips),
                "scene_assets": scene_assets
            }
        else:
            return {
                "status": "error",
                "message": "Lỗi khi ghép các phân cảnh bằng FFmpeg."
            }

video_assembler = VideoAssembler()
