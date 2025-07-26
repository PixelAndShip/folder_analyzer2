from flask import Flask, render_template, request, redirect
from media_utils import init_db, scan_and_index, get_data_for_local, get_folder_stats, get_folder_contents, DB_PATH

import threading
import webbrowser
import os
import sqlite3


app = Flask(__name__)
init_db()

def get_first_level_folders(root):
    try:
        # List only directory names in the root directory (first-level folders)
        return sorted([e.name for e in os.scandir(root) if e.is_dir()])
    except Exception:
        return []
@app.context_processor
def utility_processor():
    def get_folder_contents_obj(folder):
        with sqlite3.connect(DB_PATH) as conn:
            from media_utils import get_folder_contents
            return get_folder_contents(conn, folder)
    return dict(get_folder_contents_obj=get_folder_contents_obj)

@app.route('/local', methods=['GET'])
def local():
    root = request.args.get('root', '').strip()
    folder = request.args.get('folder', '').strip()          # selected first column folder
    subfolder = request.args.get('subfolder', '').strip()    # selected second column folder

    video_price = float(request.args.get('video_price') or 0)
    minute_price = float(request.args.get('minute_price') or 0)
    error = None

    col1_contents = col2_contents = col3_contents = []

    if root:
        if not os.path.isdir(root):
            error = "Invalid path."
        else:
            try:
                # Index videos in the DB before querying
                scan_and_index(root)
            except Exception as e:
                error = f"Error during indexing: {e}"

            if not error:
                # Get first level folders from actual filesystem (first column)
                first_level_folders = get_first_level_folders(root)

                with sqlite3.connect(DB_PATH) as conn:
                    col1_contents = []
                    for f in first_level_folders:
                        # Get stats from DB for each folder under root
                        vcount, totalsec = get_folder_stats(conn, f)
                        col1_contents.append({
                            'type': 'folder',
                            'name': f,
                            'rel_path': f,
                            'total_videos': vcount,
                            'total_seconds': totalsec,
                        })

                    # Second column: contents of selected folder in the first column
                    col2_contents = get_folder_contents(conn, folder)

                    # Third column: contents of selected folder inside the second column folder
                    if subfolder:
                        combined_path = folder + "/" + subfolder if folder else subfolder
                        col3_contents = get_folder_contents(conn, combined_path)
                    else:
                        col3_contents = []
    print("col1_contents count:", len(col1_contents))
    print("col2_contents count:", len(col2_contents))
    print("col3_contents count:", len(col3_contents))

    return render_template(
        'local.html',
        root=root,
        folder=folder,
        subfolder=subfolder,
        col1_contents=col1_contents,
        col2_contents=col2_contents,
        col3_contents=col3_contents,
        video_price=video_price,
        minute_price=minute_price,
        error=error
    )


@app.route('/')
def index():
    return redirect('/local')


@app.route('/shutdown', methods=['POST'])
def shutdown():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        return 'Not running with the Werkzeug Server'
    func()
    return 'Server shutting down...'


@app.route('/debug_db')
def debug_db():
    import sqlite3
    rows = []
    with sqlite3.connect('media_index.db') as conn:
        for r in conn.execute('SELECT folder, name, rel_path, abs_path, duration FROM videos LIMIT 50'):
            rows.append(r)
    return f"<pre>{chr(10).join(str(row) for row in rows)}</pre>"


if __name__ == '__main__':
    # Prevent browser launch on Flask reloader spawn
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        pass
    else:
        threading.Timer(1, lambda: webbrowser.open('http://127.0.0.1:5001/local')).start()

    app.run(debug=False, port=5001, use_reloader=False)
