from flask import Flask, render_template, request, redirect, jsonify
from media_utils import init_db, scan_and_index, get_tree_from_db
import threading
import webbrowser
app = Flask(__name__)
init_db()

@app.route('/local', methods=['GET'])
def local():
    root = request.args.get('root', '').strip()
    current_folder = request.args.get('folder', '').strip()
    video_price = float(request.args.get('video_price') or 0)
    minute_price = float(request.args.get('minute_price') or 0)
    error = None
    columns = []
    if root:
        import os
        if not os.path.isdir(root):
            error = "Invalid path."
        else:
            err, count = scan_and_index(root)
            if err:
                error = err
            else:
                columns = get_tree_from_db(root, current_folder)
    return render_template(
        'local.html',
        root=root,
        current_folder=current_folder,
        columns=columns,
        error=error,
        video_price=video_price,
        minute_price=minute_price
    )

@app.route('/')
def index():
    return redirect('/local')
@app.route('/shutdown', methods=['POST'])
def shutdown():
    # Only works with Flask's built-in server
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        return 'Not running with the Werkzeug Server'
    func()
    return 'Server shutting down...'
# Optional: debugging endpoint for dev use only!
@app.route('/debug_db')
def debug_db():
    import sqlite3
    rows = []
    with sqlite3.connect('media_index.db') as conn:
        for r in conn.execute('SELECT folder, name, rel_path, abs_path, duration FROM videos LIMIT 50'):
            rows.append(r)
    return f"<pre>{chr(10).join(str(row) for row in rows)}</pre>"

if __name__ == '__main__':
    import os

    # Prevent browser launch on Flask's auto-reloader spawn
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        # Prevent browser on child process
        pass
    else:
        import threading, webbrowser
        threading.Timer(1, lambda: webbrowser.open('http://127.0.0.1:5001/local')).start()
    
    app.run(debug=False, port=5001, use_reloader=False)

