import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import YOUTUBE_API_KEY
from services.quota_tracker import quota_tracker

class YouTubeService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or YOUTUBE_API_KEY
        self._youtube = None
        if self.api_key:
            try:
                self._youtube = build("youtube", "v3", developerKey=self.api_key)
            except Exception as e:
                print(f"[YouTubeService] Init error: {e}")

    def is_configured(self) -> bool:
        return bool(self.api_key and self._youtube)

    def test_connection(self) -> Tuple[bool, str]:
        """Kiểm tra API Key hợp lệ bằng lệnh video_stats nhẹ (tốn 1 unit)."""
        if not self._youtube:
            return False, "Chưa cấu hình YOUTUBE_API_KEY hoặc khởi tạo thất bại."
        try:
            req = self._youtube.videos().list(part="id", id="dQw4w9WgXcQ")
            req.execute()
            quota_tracker.add_yt_units(1)
            return True, "YouTube Data API v3 kết nối thành công."
        except HttpError as e:
            return False, f"YouTube API HttpError {e.resp.status}: {e.error_details}"
        except Exception as e:
            return False, f"YouTube API Error: {str(e)}"

    async def search_videos(
        self,
        query: str,
        order: str = "viewCount",
        days_back: int = 30,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Tìm kiếm video YouTube trong khoảng 30 ngày gần đây.
        Tốn 100 units quota.
        """
        if not self._youtube:
            return []

        published_after = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()

        def _sync_search():
            try:
                quota_tracker.add_yt_units(100)
                request = self._youtube.search().list(
                    part="snippet",
                    q=query,
                    type="video",
                    order=order,
                    publishedAfter=published_after,
                    maxResults=min(max_results, 25)
                )
                response = request.execute()
                items = response.get("items", [])
                
                video_list = []
                for item in items:
                    vid_id = item.get("id", {}).get("videoId")
                    snippet = item.get("snippet", {})
                    if vid_id:
                        video_list.append({
                            "video_id": vid_id,
                            "title": snippet.get("title", ""),
                            "description": snippet.get("description", ""),
                            "channel_id": snippet.get("channelId", ""),
                            "channel_title": snippet.get("channelTitle", ""),
                            "published_at": snippet.get("publishedAt", ""),
                            "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url") or snippet.get("thumbnails", {}).get("default", {}).get("url", "")
                        })
                return video_list
            except Exception as e:
                print(f"[YouTubeService] Search error: {e}")
                return []

        return await asyncio.to_thread(_sync_search)

    async def get_video_stats_and_breakout(self, video_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Lấy thống kê chi tiết lượt xem, like, và subscriber của từng kênh để tính Breakout Score.
        Tốn 1-2 units quota.
        """
        if not self._youtube or not video_items:
            return []

        video_ids = [v["video_id"] for v in video_items if "video_id" in v]
        channel_ids = list(set([v["channel_id"] for v in video_items if "channel_id" in v]))

        def _sync_stats():
            try:
                # 1. Lấy Video Stats (tốn 1 unit)
                quota_tracker.add_yt_units(1)
                vid_req = self._youtube.videos().list(
                    part="statistics,snippet",
                    id=",".join(video_ids[:50])
                )
                vid_res = vid_req.execute()
                vid_stats_map = {}
                for item in vid_res.get("items", []):
                    v_id = item.get("id")
                    stats = item.get("statistics", {})
                    vid_stats_map[v_id] = {
                        "view_count": int(stats.get("viewCount", 0)),
                        "like_count": int(stats.get("likeCount", 0)),
                        "comment_count": int(stats.get("commentCount", 0))
                    }

                # 2. Lấy Channel Stats (tốn 1 unit)
                chan_stats_map = {}
                if channel_ids:
                    quota_tracker.add_yt_units(1)
                    chan_req = self._youtube.channels().list(
                        part="statistics",
                        id=",".join(channel_ids[:50])
                    )
                    chan_res = chan_req.execute()
                    for item in chan_res.get("items", []):
                        c_id = item.get("id")
                        c_stats = item.get("statistics", {})
                        chan_stats_map[c_id] = {
                            "subscriber_count": int(c_stats.get("subscriberCount", 0)),
                            "video_count": int(c_stats.get("videoCount", 0))
                        }

                # 3. Tổng hợp và tính toán Breakout Signal
                enriched_videos = []
                for v in video_items:
                    vid_id = v["video_id"]
                    chan_id = v.get("channel_id")
                    
                    v_stats = vid_stats_map.get(vid_id, {"view_count": 0, "like_count": 0, "comment_count": 0})
                    c_stats = chan_stats_map.get(chan_id, {"subscriber_count": 1000, "video_count": 0})
                    
                    view_count = v_stats["view_count"]
                    sub_count = c_stats["subscriber_count"]
                    
                    # Breakout Ratio: view / subs (lấy min subs là 1000 để tránh chia số quá nhỏ)
                    effective_subs = max(sub_count, 500)
                    ratio = round(view_count / effective_subs, 2)
                    
                    # Đánh giá tín hiệu Breakout
                    is_breakout = False
                    breakout_tier = "Normal"
                    if ratio >= 5.0 and sub_count < 100000:
                        is_breakout = True
                        breakout_tier = "Mega Breakout (Views gấp >5x Subs)"
                    elif ratio >= 2.0 and sub_count < 50000:
                        is_breakout = True
                        breakout_tier = "Strong Breakout (Kênh nhỏ view bứt phá)"
                    elif view_count > 100000:
                        breakout_tier = "High Volume"

                    enriched = {
                        **v,
                        "view_count": view_count,
                        "like_count": v_stats["like_count"],
                        "comment_count": v_stats["comment_count"],
                        "subscriber_count": sub_count,
                        "view_sub_ratio": ratio,
                        "is_breakout": is_breakout,
                        "breakout_tier": breakout_tier,
                        "url": f"https://www.youtube.com/watch?v={vid_id}"
                    }
                    enriched_videos.append(enriched)

                # Sắp xếp ưu tiên: Breakout ratio cao và view lớn
                enriched_videos.sort(key=lambda x: (x["view_sub_ratio"], x["view_count"]), reverse=True)
                return enriched_videos
            except Exception as e:
                print(f"[YouTubeService] Stats error: {e}")
                return video_items

        return await asyncio.to_thread(_sync_stats)

    async def get_channel_full_audit(self, channel_input: str) -> Dict[str, Any]:
        """
        Bóc tách toàn diện 1 kênh YouTube qua link, @handle, hoặc channel ID:
        - Lấy thông tin kênh (Subs, Views, Bio, Keywords)
        - Lấy danh sách video nổi bật & mới nhất
        - Trích xuất toàn bộ Thẻ Tag (Video Tags), Cấu trúc SEO Tiêu đề & Mô tả
        - Trích xuất ảnh Thumbnail của các video top views
        Tốn ~2-3 units quota.
        """
        if not self._youtube:
            return {"error": "Chưa cấu hình YouTube API Key."}

        import re

        def _sync_channel_audit():
            try:
                # 1. Trích xuất handle hoặc ID từ input
                raw = channel_input.strip()
                handle_match = re.search(r"@([A-Za-z0-9_.-]+)", raw)
                channel_id_match = re.search(r"(?:channel\/|c\/|user\/)?(UC[0-9A-Za-z_-]{22})", raw)
                
                channel_item = None

                # Thử tìm theo Channel ID nếu có
                if channel_id_match:
                    chan_id = channel_id_match.group(1)
                    quota_tracker.add_yt_units(1)
                    req = self._youtube.channels().list(
                        part="snippet,statistics,contentDetails,brandingSettings",
                        id=chan_id
                    )
                    res = req.execute()
                    if res.get("items"):
                        channel_item = res["items"][0]

                # Thử tìm theo @handle
                if not channel_item and handle_match:
                    handle_name = handle_match.group(1)
                    quota_tracker.add_yt_units(1)
                    try:
                        req = self._youtube.channels().list(
                            part="snippet,statistics,contentDetails,brandingSettings",
                            forHandle=handle_name
                        )
                        res = req.execute()
                        if res.get("items"):
                            channel_item = res["items"][0]
                    except Exception:
                        pass

                # Nếu vẫn chưa tìm thấy, dùng search type='channel'
                if not channel_item:
                    clean_query = re.sub(r"https?://(?:www\.)?youtube\.com/(?:@)?", "", raw).strip()
                    quota_tracker.add_yt_units(100)
                    s_req = self._youtube.search().list(
                        part="snippet",
                        q=clean_query,
                        type="channel",
                        maxResults=1
                    )
                    s_res = s_req.execute()
                    if s_res.get("items"):
                        found_id = s_res["items"][0]["snippet"]["channelId"]
                        quota_tracker.add_yt_units(1)
                        req = self._youtube.channels().list(
                            part="snippet,statistics,contentDetails,brandingSettings",
                            id=found_id
                        )
                        res = req.execute()
                        if res.get("items"):
                            channel_item = res["items"][0]

                if not channel_item:
                    return {"error": f"Không tìm thấy kênh YouTube tương ứng với `{channel_input}`."}

                # 2. Thông tin cơ bản kênh
                chan_snippet = channel_item.get("snippet", {})
                chan_stats = channel_item.get("statistics", {})
                chan_branding = channel_item.get("brandingSettings", {}).get("channel", {})
                channel_id = channel_item.get("id")

                channel_info = {
                    "channel_id": channel_id,
                    "title": chan_snippet.get("title", ""),
                    "custom_url": chan_snippet.get("customUrl", ""),
                    "description": chan_snippet.get("description", ""),
                    "avatar_url": chan_snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                    "subscriber_count": int(chan_stats.get("subscriberCount", 0)),
                    "video_count": int(chan_stats.get("videoCount", 0)),
                    "view_count": int(chan_stats.get("viewCount", 0)),
                    "channel_keywords": chan_branding.get("keywords", "")
                }

                # 3. Lấy Uploads Playlist để lấy video mới và video nổi bật
                uploads_playlist_id = channel_item.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
                video_ids = []

                if uploads_playlist_id:
                    quota_tracker.add_yt_units(1)
                    pl_req = self._youtube.playlistItems().list(
                        part="contentDetails",
                        playlistId=uploads_playlist_id,
                        maxResults=15
                    )
                    pl_res = pl_req.execute()
                    video_ids = [item["contentDetails"]["videoId"] for item in pl_res.get("items", [])]

                # 4. Lấy chi tiết Video (Tags, SEO, Stats, Thumbnails)
                top_videos = []
                all_tags = []
                if video_ids:
                    quota_tracker.add_yt_units(1)
                    v_req = self._youtube.videos().list(
                        part="snippet,statistics",
                        id=",".join(video_ids[:50])
                    )
                    v_res = v_req.execute()
                    for v in v_res.get("items", []):
                        snip = v.get("snippet", {})
                        st = v.get("statistics", {})
                        v_tags = snip.get("tags", [])
                        all_tags.extend(v_tags)
                        
                        top_videos.append({
                            "video_id": v.get("id"),
                            "title": snip.get("title", ""),
                            "published_at": snip.get("publishedAt", ""),
                            "description": snip.get("description", "")[:200],
                            "tags": v_tags,
                            "view_count": int(st.get("viewCount", 0)),
                            "like_count": int(st.get("likeCount", 0)),
                            "comment_count": int(st.get("commentCount", 0)),
                            "thumbnail_url": snip.get("thumbnails", {}).get("maxres", {}).get("url") or snip.get("thumbnails", {}).get("high", {}).get("url") or f"https://img.youtube.com/vi/{v.get('id')}/hqdefault.jpg"
                        })

                # Sắp xếp top videos theo lượt xem
                top_videos.sort(key=lambda x: x["view_count"], reverse=True)

                # Đếm tần suất thẻ tag phổ biến nhất
                from collections import Counter
                tag_counts = Counter(all_tags).most_common(20)
                popular_tags = [t[0] for t in tag_counts]

                return {
                    "status": "success",
                    "channel_info": channel_info,
                    "top_videos": top_videos[:6],
                    "popular_tags": popular_tags,
                    "total_tags_found": len(set(all_tags))
                }

            except Exception as e:
                print(f"[YouTubeService] Channel audit error: {e}")
                return {"error": f"Lỗi khi quét kênh YouTube: {str(e)}"}

        return await asyncio.to_thread(_sync_channel_audit)

youtube_service = YouTubeService()
