from flask import Flask, render_template, request, redirect
from pathlib import Path
from datetime import datetime
from moviepy import VideoFileClip
from column_tree import build_tree, flatten_tree
app = Flask(__name__)

@app.route('/')
def index():
    return redirect('/local')

@app.route('/local', methods=['GET'])
def local():
    error = None
    columns = []
    total_videos = 0
    total_minutes = 0

    base = request.args.get('base', '').strip()
    folder = request.args.get('folder', '').strip()
    video_price = float(request.args.get('video_price') or 0)
    minute_price = float(request.args.get('minute_price') or 0)

    if base and folder:
        path = Path(base) / folder
    elif base:
        path = Path(base)
    else:
        path = None

    if path:
        if not path.is_dir():
            error = "Invalid path."
        else:
            tree = build_tree(path, base)
            columns, total_videos, total_minutes = flatten_tree(tree)

    return render_template(
        'local.html',
        base=base,
        folder=folder,
        error=error,
        columns=columns,
        total_videos=total_videos,
        total_minutes=total_minutes,
        video_price=video_price,
        minute_price=minute_price
    )

if __name__ == '__main__':
    app.run(debug=True)
