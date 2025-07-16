from flask import Flask, render_template, request, redirect
from pathlib import Path
from column_tree import build_tree, flatten_tree

app = Flask(__name__)

@app.route('/')
def index():
    return redirect('/local')

@app.route('/local', methods=['GET'])
def local():
    # SINGLE input field for path called 'root'
    root = request.args.get('root', '').strip()
    video_price = float(request.args.get('video_price') or 0)
    minute_price = float(request.args.get('minute_price') or 0)
    error = None
    columns = []
    abs_root = None

    if root:
        abs_root = Path(root)
        if not abs_root.exists() or not abs_root.is_dir():
            error = "Invalid path."
            abs_root = None
        else:
            # Pass both 'path' and 'base' to keep relative paths for links
            tree = build_tree(abs_root, abs_root)
            columns = flatten_tree(tree)

    return render_template(
        'local.html',
        root=root,
        columns=columns,
        error=error,
        video_price=video_price,
        minute_price=minute_price
    )

if __name__ == '__main__':
    app.run(debug=True)
