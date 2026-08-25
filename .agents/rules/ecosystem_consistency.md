# ECOSYSTEM FULL SYNCHRONIZATION RULE

Bắt buộc tuân thủ nguyên tắc: **KHI THAY ĐỔI / NÂNG CẤP BẤT KỲ TÍNH NĂNG NÀO, PHẢI ĐỒNG BỘ TOÀN DIỆN TẤT CẢ CÁC BÊN LIÊN QUAN**:

1. **Core Service & Models (`services/`):**
   - Khi thêm mới hoặc sửa API/LLM (ví dụ: Google Gemini 3.6 Flash, Flow Studio), phải cập nhật logic gọi, xử lý token, fallback và đo độ trễ (latency).
2. **5 Discord Bots (`main.py` & `agents/`):**
   - Cập nhật cả 5 con bot (Orchestrator, News, Market, Thumbnail, Monitor).
   - Đồng bộ slash commands (`/quota`, `/kichban`, `/ve_anh`, `/status`) và bộ lọc từ khóa nhận diện tin nhắn (intent triggers).
3. **Web Dashboard (`services/dashboard_server.py`):**
   - Cập nhật giao diện HTML, CSS, JavaScript auto-sync 3s.
   - Cập nhật các API `/api/stats`, `/api/chats`, `/api/reports` để web luôn phản ánh 100% dữ liệu từ Discord và Database.
4. **Database & Quota Logger (`services/chat_logger.py`, `services/quota_tracker.py`):**
   - Ghi nhận ngay lập tức mọi hoạt động (kịch bản, audit, vẽ ảnh, tin nhắn) vào SQLite.
5. **Deployment & GitHub:**
   - Dọn dẹp tiến trình cũ, kiểm tra binding port sạch sẽ và tự động commit & push lên GitHub `https://github.com/LAMHOANG37/B-c-h-t-c-m-o.git`.
