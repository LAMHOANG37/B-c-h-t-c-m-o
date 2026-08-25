import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "chat_history.db")

class ChatLogger:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    context_type TEXT NOT NULL,
                    channel_name TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    user_name TEXT NOT NULL,
                    bot_name TEXT NOT NULL,
                    bot_role TEXT NOT NULL,
                    user_message TEXT NOT NULL,
                    bot_response TEXT NOT NULL
                )
            """)
            conn.commit()

    def log_chat(
        self,
        context_type: str,
        channel_name: str,
        user_id: str,
        user_name: str,
        bot_name: str,
        bot_role: str,
        user_message: str,
        bot_response: str
    ):
        """Ghi lại 1 lượt trò chuyện giữa User và Bot vào Database."""
        now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO chat_logs 
                    (timestamp, context_type, channel_name, user_id, user_name, bot_name, bot_role, user_message, bot_response)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    now_iso,
                    context_type,
                    channel_name,
                    str(user_id),
                    user_name,
                    bot_name,
                    bot_role,
                    user_message,
                    bot_response
                ))
                conn.commit()
        except Exception as e:
            print(f"[ChatLogger] Error logging chat: {e}", flush=True)

    def get_recent_chats(self, limit: int = 100, bot_filter: Optional[str] = None, search_query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lấy danh sách các cuộc trò chuyện gần nhất."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = "SELECT * FROM chat_logs WHERE 1=1"
                params = []

                if bot_filter and bot_filter != "all":
                    query += " AND (bot_role = ? OR bot_name LIKE ?)"
                    params.extend([bot_filter, f"%{bot_filter}%"])

                if search_query:
                    query += " AND (user_name LIKE ? OR user_message LIKE ? OR bot_response LIKE ?)"
                    search_wild = f"%{search_query}%"
                    params.extend([search_wild, search_wild, search_wild])

                query += " ORDER BY id DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            print(f"[ChatLogger] Error reading chats: {e}", flush=True)
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Thống kê tổng số cuộc trò chuyện và phân loại theo bot."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM chat_logs")
                total = cursor.fetchone()[0]

                cursor.execute("SELECT bot_role, COUNT(*) FROM chat_logs GROUP BY bot_role")
                by_bot = dict(cursor.fetchall())

                cursor.execute("SELECT COUNT(DISTINCT user_id) FROM chat_logs")
                unique_users = cursor.fetchone()[0]

                return {
                    "total_messages": total,
                    "by_bot": by_bot,
                    "unique_users": unique_users
                }
        except Exception as e:
            return {"total_messages": 0, "by_bot": {}, "unique_users": 0}

chat_logger = ChatLogger()
