import sqlite3
import os
import datetime
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "automator.db")

class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            # Processed comments table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_comments (
                    comment_id TEXT PRIMARY KEY,
                    media_id TEXT,
                    user_id TEXT,
                    username TEXT,
                    comment_text TEXT,
                    matched_keyword TEXT,
                    is_follower INTEGER,
                    dm_sent INTEGER DEFAULT 0,
                    comment_replied INTEGER DEFAULT 0,
                    comment_liked INTEGER DEFAULT 0,
                    status_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Daily stats for rate limiting and reporting
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date TEXT PRIMARY KEY,
                    dms_sent INTEGER DEFAULT 0,
                    comments_replied INTEGER DEFAULT 0,
                    followers_served INTEGER DEFAULT 0,
                    non_followers_blocked INTEGER DEFAULT 0
                );
            """)

            # Bot event logs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT,
                    message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

    def is_comment_processed(self, comment_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_comments WHERE comment_id = ?", (str(comment_id),))
            return cursor.fetchone() is not None

    def record_processed_comment(
        self,
        comment_id: str,
        media_id: str,
        user_id: str,
        username: str,
        comment_text: str,
        matched_keyword: str,
        is_follower: bool,
        dm_sent: bool = False,
        comment_replied: bool = False,
        comment_liked: bool = False,
        status_message: str = ""
    ) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO processed_comments (
                    comment_id, media_id, user_id, username,
                    comment_text, matched_keyword, is_follower,
                    dm_sent, comment_replied, comment_liked, status_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                str(comment_id),
                str(media_id),
                str(user_id),
                str(username),
                comment_text,
                matched_keyword,
                1 if is_follower else 0,
                1 if dm_sent else 0,
                1 if comment_replied else 0,
                1 if comment_liked else 0,
                status_message
            ))
            conn.commit()

    def get_today_str(self) -> str:
        return datetime.datetime.now().strftime("%Y-%m-%d")

    def get_daily_dm_count(self) -> int:
        today = self.get_today_str()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT dms_sent FROM daily_stats WHERE date = ?", (today,))
            row = cursor.fetchone()
            return row["dms_sent"] if row else 0

    def increment_daily_stat(self, stat_name: str, amount: int = 1) -> None:
        valid_stats = {"dms_sent", "comments_replied", "followers_served", "non_followers_blocked"}
        if stat_name not in valid_stats:
            return

        today = self.get_today_str()
        with self._get_connection() as conn:
            conn.execute(f"""
                INSERT INTO daily_stats (date, {stat_name})
                VALUES (?, ?)
                ON CONFLICT(date) DO UPDATE SET {stat_name} = {stat_name} + ?;
            """, (today, amount, amount))
            conn.commit()

    def log_event(self, level: str, message: str) -> None:
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{level}] {message}")
        with self._get_connection() as conn:
            conn.execute("INSERT INTO bot_logs (level, message) VALUES (?, ?);", (level, message))
            conn.commit()

    def get_recent_logs(self, limit: int = 40) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT level, message, created_at FROM bot_logs ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_recent_activity(self, limit: int = 25) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT comment_id, username, comment_text, matched_keyword,
                       is_follower, dm_sent, comment_replied, status_message, created_at
                FROM processed_comments
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_summary_stats(self) -> Dict[str, Any]:
        today = self.get_today_str()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Today's stats
            cursor.execute("SELECT * FROM daily_stats WHERE date = ?", (today,))
            today_row = cursor.fetchone()
            today_dms = today_row["dms_sent"] if today_row else 0
            today_followers = today_row["followers_served"] if today_row else 0
            today_non_followers = today_row["non_followers_blocked"] if today_row else 0
            
            # All time stats
            cursor.execute("SELECT COUNT(*) as total_processed FROM processed_comments")
            total_comments = cursor.fetchone()["total_processed"]
            
            cursor.execute("SELECT COUNT(*) as total_dms FROM processed_comments WHERE dm_sent = 1")
            total_dms = cursor.fetchone()["total_dms"]

            return {
                "today_date": today,
                "today_dms": today_dms,
                "today_followers_served": today_followers,
                "today_non_followers_blocked": today_non_followers,
                "total_processed_comments": total_comments,
                "total_dms_sent": total_dms
            }
