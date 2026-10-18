import sqlite3
import os
from datetime import datetime
from utils.paths import resource_path

# DATABASE: lưu thông tin học sinh và lịch sử hoạt động
DB_PATH = resource_path(os.path.join("data", "students.db"))

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    class_name TEXT,
    late_count INTEGER DEFAULT 0,
    total_days INTEGER DEFAULT 0,
    total_sessions INTEGER DEFAULT 0,
    late_sessions INTEGER DEFAULT 0,
    last_attendance TEXT,
    checkin_start TEXT DEFAULT '06:00',
    checkin_end TEXT DEFAULT '07:30',
    late_end TEXT DEFAULT '08:00'
)
"""

HISTORY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    action TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL
)
"""


def init_db():
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(CREATE_TABLE_SQL)
        conn.execute(HISTORY_TABLE_SQL)
        
        # Thêm các cột mới nếu chưa tồn tại
        for col in ['checkin_start', 'checkin_end', 'late_end']:
            try:
                conn.execute(f"ALTER TABLE students ADD COLUMN {col} TEXT DEFAULT '06:00'")
            except sqlite3.OperationalError:
                pass
        
        conn.commit()
        conn.close()
        return True
    except sqlite3.OperationalError as e:
        print(f"Lỗi kết nối Database: {e}")
        return False


def log_history(student_id, action, details=None):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO history (student_id, action, details, created_at) VALUES (?, ?, ?, ?)",
            (student_id, action, details or '', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def load_history(limit=50):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT created_at, action, details FROM history ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return rows


def load_students():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, class_name, total_sessions, late_sessions, last_attendance FROM students")
    rows = cursor.fetchall()
    conn.close()
    return rows