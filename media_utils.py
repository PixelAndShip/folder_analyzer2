import os
import sqlite3
import subprocess
from pathlib import Path
import datetime

DB_PATH = os.path.abspath("media_index.db")

# Ensure DB directory exists
db_dir = os.path.dirname(DB_PATH)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)


def get_mp4_duration_in_seconds(filepath):
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                filepath
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, check=True
        )
        return int(float(result.stdout.strip()))
    except Exception:
        return 0


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
        conn.commit()


def normalize_folder(folder):
    folder = (folder or '').replace('\\', '/').strip('/')
    return '' if folder in ('', '.') else folder


def datetime_fmt(ts):
    if ts is None:
        return ""
    return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


def scan_and_index(root):
    root = Path(root).resolve()
    if not root.is_dir():
        return "Invalid folder", 0
    count = 0
    with sqlite3.connect(DB_PATH) as conn:
        for dirpath, dirs, files in os.walk(root):
            for fname in files:
                if fname.lower().endswith('.mp4'):
                    abs_path = str(Path(dirpath, fname).resolve())
                    rel_path = str(Path(abs_path).relative_to(root)).replace("\\", "/")
                    folder = normalize_folder(str(Path(dirpath).resolve().relative_to(root)))
                    mtime = os.path.getmtime(abs_path)
                    cur = conn.execute("SELECT mtime FROM videos WHERE abs_path = ?", (abs_path,))
                    row = cur.fetchone()
                    if row and abs(row[0] - mtime) < 1:
                        continue
                    duration = get_mp4_duration_in_seconds(abs_path)
                    conn.execute("""
                        INSERT INTO videos (abs_path, rel_path, name, folder, mtime, duration)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(abs_path) DO UPDATE SET 
                            mtime=excluded.mtime,
                            duration=excluded.duration
                        """, (abs_path, rel_path, fname, folder, mtime, duration))
                    count += 1
        conn.commit()
    return None, count


def get_folder_stats(conn, folder):
    folder = normalize_folder(folder)
    if folder:
        pattern = f"{folder}/%"
    else:
        pattern = '%'
    cur = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(duration), 0) FROM videos WHERE folder = ? OR folder LIKE ?",
        (folder, pattern)
    )
    vcount, total_seconds = cur.fetchone()
    return vcount or 0, total_seconds or 0


def get_folder_contents(conn, folder):
    folder = normalize_folder(folder)
    subfolders = set()
    for row in conn.execute("SELECT DISTINCT folder FROM videos"):
        f = normalize_folder(row[0])
        if folder == "":
            if f and "/" in f:
                sub = f.split("/", 1)[0]
                if sub:
                    subfolders.add(sub)
            elif f and "/" not in f:
                subfolders.add(f)
        else:
            if f.startswith(folder + "/"):
                rest = f[len(folder) + 1:]
                sub = rest.split("/", 1)[0]
                if sub:
                    subfolders.add(sub)

    folder_items = []
    for sub in sorted(subfolders):
        folder_path = sub if not folder else folder + "/" + sub
        vcount, totalsec = get_folder_stats(conn, folder_path)
        folder_items.append({
            'type': 'folder',
            'name': sub,
            'count': vcount,
            'modified': '',
            'rel_path': folder_path,
            'abs_path': str(Path() / folder_path),
            'children': None,
            'total_videos': vcount,
            'total_seconds': totalsec,
        })

    file_items = []
    cur = conn.execute(
        "SELECT name, rel_path, abs_path, duration, mtime FROM videos WHERE folder=?",
        (folder,)
    )
    for name, rel_path, abs_path, duration, mtime in cur.fetchall():
        mins, secs = divmod(duration or 0, 60)
        file_items.append({
            'type': 'file',
            'name': name,
            'duration': f"{mins}m {secs}s",
            'seconds': duration or 0,
            'modified': datetime_fmt(mtime),
            'rel_path': rel_path,
            'abs_path': abs_path,
        })

    return folder_items + file_items


def get_data_for_local(root, folder, subfolder):
    """
    Parameters:
    - root: root folder path (string)
    - folder: selected folder in first column (relative path string, '' = root)
    - subfolder: selected folder in second column (relative path string, '' = none selected)

    Returns three lists:
    - col1_contents: list of folders/files in root (top-level)
    - col2_contents: list of folders/files inside 'folder'
    - col3_contents: list of folders/files inside 'folder/subfolder'
    """
    root = Path(root).resolve()

    with sqlite3.connect(DB_PATH) as conn:
        norm = normalize_folder

        # First column: top-level folders/files under root
        col1_contents = []

        # Get immediate subfolders of root (no slash)
        subfolders = set()
        for r in conn.execute("SELECT DISTINCT folder FROM videos"):
            f = norm(r[0])
            if "/" not in f and f != '':
                subfolders.add(f)

        for f in sorted(subfolders):
            vcount, totalsec = get_folder_stats(conn, f)
            col1_contents.append({
                'type': 'folder',
                'name': f,
                'rel_path': f,
                'total_videos': vcount,
                'total_seconds': totalsec,
            })

        # Also add files directly under root (folder='')
        col1_files = []
        cur = conn.execute("SELECT name, rel_path, abs_path, duration, mtime FROM videos WHERE folder = ''")
        for name, rel_path, abs_path, duration, mtime in cur.fetchall():
            mins, secs = divmod(duration or 0, 60)
            col1_files.append({
                'type': 'file',
                'name': name,
                'duration': f"{mins}m {secs}s",
                'seconds': duration or 0,
                'modified': datetime_fmt(mtime),
                'rel_path': rel_path,
                'abs_path': abs_path,
            })

        col1_contents += col1_files

        # Second column: contents of selected first-column folder
        col2_contents = get_folder_contents(conn, folder)

        # Third column: contents of selected second-column folder inside first-column folder
        if subfolder:
            combined_path = folder + "/" + subfolder if folder else subfolder
            col3_contents = get_folder_contents(conn, combined_path)
        else:
            col3_contents = []

    return col1_contents, col2_contents, col3_contents
