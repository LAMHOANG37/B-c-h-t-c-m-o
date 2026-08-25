import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, Optional

# Múi giờ Pacific (UTC-7 cho PDT, UTC-8 cho PST) và Múi giờ VN (UTC+7)
PACIFIC_TZ = timezone(timedelta(hours=-7))
VIETNAM_TZ = timezone(timedelta(hours=7))

class QuotaTracker:
    def __init__(self):
        # YouTube Quota
        self.yt_daily_limit: int = 10000
        self.yt_used_units: int = 0
        self.yt_last_reset_date: str = self._get_current_pt_date()
        self.yt_warned_today: bool = False

        # LLM Quota (Groq / Claude)
        self.llm_total_requests: int = 0
        self.llm_total_tokens: int = 0
        self.llm_limit_requests: Optional[int] = 30  # Groq default 30 RPM
        self.llm_remaining_requests: Optional[int] = 30
        self.llm_limit_tokens: Optional[int] = 6000   # Groq default 6000 TPM
        self.llm_remaining_tokens: Optional[int] = 6000
        self.llm_reset_requests_str: Optional[str] = None
        self.llm_reset_tokens_str: Optional[str] = None
        self.llm_warned_today: bool = False
        self.llm_last_warn_date: str = self._get_current_pt_date()

        # Session tracking (for each report run)
        self._session_yt_units: int = 0
        self._session_llm_requests: int = 0
        self._session_llm_tokens: int = 0
        self._session_rate_limit_hits: int = 0

    def _get_current_pt_date(self) -> str:
        return datetime.now(PACIFIC_TZ).strftime("%Y-%m-%d")

    def _check_and_reset_yt_if_needed(self):
        current_date = self._get_current_pt_date()
        if current_date != self.yt_last_reset_date:
            self.yt_used_units = 0
            self.yt_last_reset_date = current_date
            self.yt_warned_today = False

        if current_date != self.llm_last_warn_date:
            self.llm_warned_today = False
            self.llm_last_warn_date = current_date

    def get_yt_reset_info(self) -> Dict[str, Any]:
        """Tính toán thời gian reset tiếp theo của YouTube API theo giờ Việt Nam."""
        now_pt = datetime.now(PACIFIC_TZ)
        tomorrow_pt = now_pt.date() + timedelta(days=1)
        next_reset_pt = datetime(tomorrow_pt.year, tomorrow_pt.month, tomorrow_pt.day, 0, 0, 0, tzinfo=PACIFIC_TZ)
        
        next_reset_vn = next_reset_pt.astimezone(VIETNAM_TZ)
        time_diff = next_reset_pt - now_pt
        
        hours, remainder = divmod(int(time_diff.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        countdown_str = f"{hours} giờ {minutes} phút"
        reset_time_str = next_reset_vn.strftime("%H:%M ngày %d/%m/%Y")
        
        return {
            "reset_time_vn": reset_time_str,
            "countdown": countdown_str,
            "hours_left": hours,
            "minutes_left": minutes
        }

    def start_session(self):
        """Khởi động bộ đếm cho 1 phiên chạy /report."""
        self._session_yt_units = 0
        self._session_llm_requests = 0
        self._session_llm_tokens = 0
        self._session_rate_limit_hits = 0

    def get_session_stats(self) -> Dict[str, int]:
        """Trả về thống kê tiêu thụ trong phiên chạy vừa rồi."""
        return {
            "yt_units": self._session_yt_units,
            "llm_requests": self._session_llm_requests,
            "llm_tokens": self._session_llm_tokens,
            "rate_limit_hits": self._session_rate_limit_hits
        }

    def record_rate_limit_hit(self):
        """Ghi nhận 1 lần bị 429 Rate Limit."""
        self._session_rate_limit_hits += 1

    def add_yt_units(self, units: int) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Cộng số YouTube API units tiêu thụ (search=100, stats=1).
        Trả về (cần_cảnh_báo: bool, thông_điệp_cảnh_báo: str, thông_tin_reset: dict)
        """
        self._check_and_reset_yt_if_needed()
        self.yt_used_units += units
        self._session_yt_units += units

        remaining = max(0, self.yt_daily_limit - self.yt_used_units)
        pct_remaining = (remaining / self.yt_daily_limit) * 100
        reset_info = self.get_yt_reset_info()

        if pct_remaining <= 20.0 and not self.yt_warned_today:
            self.yt_warned_today = True
            msg = (
                f"🚨 **CẢNH BÁO HẠN MỨC YOUTUBE (< 20%)**:\n"
                f"• Còn lại: `{remaining:,}` / `{self.yt_daily_limit:,}` units ({pct_remaining:.1f}%)\n"
                f"• Thời gian Reset: `{reset_info['reset_time_vn']}` (còn `{reset_info['countdown']}`)"
            )
            return True, msg, reset_info

        return False, "", reset_info

    def update_llm_headers(self, headers: Dict[str, Any], used_tokens: int = 0) -> Tuple[bool, str]:
        """
        Cập nhật thông tin quota LLM từ response headers (Groq / Anthropic).
        """
        self._check_and_reset_yt_if_needed()
        self.llm_total_requests += 1
        self._session_llm_requests += 1
        self.llm_total_tokens += used_tokens
        self._session_llm_tokens += used_tokens

        # Headers từ Groq
        if "x-ratelimit-limit-requests" in headers:
            try:
                self.llm_limit_requests = int(headers.get("x-ratelimit-limit-requests"))
            except (ValueError, TypeError):
                pass

        if "x-ratelimit-remaining-requests" in headers:
            try:
                self.llm_remaining_requests = int(headers.get("x-ratelimit-remaining-requests"))
            except (ValueError, TypeError):
                pass

        if "x-ratelimit-limit-tokens" in headers:
            try:
                self.llm_limit_tokens = int(headers.get("x-ratelimit-limit-tokens"))
            except (ValueError, TypeError):
                pass

        if "x-ratelimit-remaining-tokens" in headers:
            try:
                self.llm_remaining_tokens = int(headers.get("x-ratelimit-remaining-tokens"))
            except (ValueError, TypeError):
                pass

        if "x-ratelimit-reset-requests" in headers:
            self.llm_reset_requests_str = str(headers.get("x-ratelimit-reset-requests"))

        if "x-ratelimit-reset-tokens" in headers:
            self.llm_reset_tokens_str = str(headers.get("x-ratelimit-reset-tokens"))

        # Cảnh báo nếu remaining requests < 20% và chưa cảnh báo hôm nay
        if self.llm_remaining_requests is not None and self.llm_limit_requests:
            pct_left = (self.llm_remaining_requests / self.llm_limit_requests) * 100
            if pct_left <= 20.0 and not self.llm_warned_today:
                self.llm_warned_today = True
                reset_str = f"Sẽ reset sau `{self.llm_reset_requests_str}`" if self.llm_reset_requests_str else "Tự động reset theo phút"
                msg = (
                    f"🚨 **CẢNH BÁO HẠN MỨC GROQ API (< 20%)**:\n"
                    f"• Requests còn lại: `{self.llm_remaining_requests}` / `{self.llm_limit_requests}` ({pct_left:.1f}%)\n"
                    f"• Thời gian Reset: {reset_str}"
                )
                return True, msg

        return False, ""

    def get_quota_summary(self, provider: str = "groq") -> Dict[str, Any]:
        """Lấy thông tin tổng thể phục vụ Web Dashboard và slash command /quota."""
        self._check_and_reset_yt_if_needed()
        yt_remaining = max(0, self.yt_daily_limit - self.yt_used_units)
        yt_pct = (yt_remaining / self.yt_daily_limit) * 100
        reset_info = self.get_yt_reset_info()

        # Tính % Groq
        groq_req_limit = self.llm_limit_requests or 30
        groq_req_rem = self.llm_remaining_requests if self.llm_remaining_requests is not None else groq_req_limit
        groq_req_pct = round((groq_req_rem / groq_req_limit) * 100, 1)

        groq_tok_limit = self.llm_limit_tokens or 6000
        groq_tok_rem = self.llm_remaining_tokens if self.llm_remaining_tokens is not None else groq_tok_limit
        groq_tok_pct = round((groq_tok_rem / groq_tok_limit) * 100, 1)

        return {
            # YouTube API
            "yt_used": self.yt_used_units,
            "yt_limit": self.yt_daily_limit,
            "yt_remaining": yt_remaining,
            "yt_pct_remaining": yt_pct,
            "yt_reset_time_vn": reset_info["reset_time_vn"],
            "yt_countdown": reset_info["countdown"],
            
            # Groq / LLM API
            "llm_provider": provider,
            "llm_total_requests": self.llm_total_requests,
            "llm_total_tokens": self.llm_total_tokens,
            "llm_limit_requests": groq_req_limit,
            "llm_remaining_requests": groq_req_rem,
            "llm_requests_pct": groq_req_pct,
            "llm_limit_tokens": groq_tok_limit,
            "llm_remaining_tokens": groq_tok_rem,
            "llm_tokens_pct": groq_tok_pct,
            "llm_reset_requests": self.llm_reset_requests_str or "Tức thì (theo giây)",
            "llm_reset_tokens": self.llm_reset_tokens_str or "Tức thì (theo giây)"
        }

# Singleton instance
quota_tracker = QuotaTracker()
