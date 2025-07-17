import sqlite3
import os
import time
from pathlib import Path
from utils import get_mp4_duration_in_seconds

DB_PATH = "media_index.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            abs_path TEXT UNIQUE,
            rel_path TEXT,
            name TEXT,
            folder TEXT,
            mtime REAL,
            duration INTEGER
        );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_folder ON videos(folder);")

def scan_and_index(root):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError("Root path must be a directory")
    with sqlite3.connect(DB_PATH) as conn:
        for dirpath, dirs, files in os.walk(root):
            for fname in files:
                if fname.lower().endswith('.mp4'):
                    abs_path = str(Path(dirpath, fname))
                    rel_path = str(Path(abs_path).relative_to(root)).replace("\\", "/")
                    folder = str(Path(dirpath).relative_to(root))
                    mtime = os.path.getmtime(abs_path)
                    
                    # Check if file already in DB, and unchanged
                    cur = conn.execute(
                        "SELECT mtime FROM videos WHERE abs_path = ?", (abs_path,))
                    row = cur.fetchone()
                    if row and (abs(row[0] - mtime) < 1):
                        continue # already indexed, unchanged
                    
                    duration = get_mp4_duration_in_seconds(abs_path)
                    # Upsert
                    conn.execute("""
                        INSERT INTO videos (abs_path, rel_path, name, folder, mtime, duration)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(abs_path) DO UPDATE SET 
                            mtime=excluded.mtime,
                            duration=excluded.duration
                    """, (abs_path, rel_path, fname, folder, mtime, duration))
        conn.commit()

if __name__ == "__main__":
    import sys
    init_db()
    scan_and_index(sys.argv[1] if len(sys.argv) > 1 else ".")
    print("Indexing complete.")
