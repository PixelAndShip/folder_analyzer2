from flask import Flask, render_template_string, request, redirect
from pathlib import Path
from datetime import datetime
from moviepy import VideoFileClip

def build_tree(path, base):
    """Recursively build tree structure, include relative path for links."""
    items = []
    for f in sorted(path.iterdir()):
        rel_path = str(f.relative_to(base))
        if f.is_dir():
            items.append({
                'type': 'folder',
                'name': f.name,
                'count': len(list(f.iterdir())),
                'modified': datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'rel_path': rel_path.replace("\\", "/"),
                'children': build_tree(f, base)
            })
        elif f.suffix.lower() == '.mp4':
            try:
                clip = VideoFileClip(str(f))
                seconds = int(clip.duration)
                mins, secs = divmod(seconds, 60)
                duration = f"{mins}m {secs}s"
                items.append({
                    'type': 'file',
                    'name': f.name,
                    'duration': duration,
                    'seconds': seconds,
                    'modified': datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
            except Exception as e:
                items.append({
                    'type': 'file',
                    'name': f.name,
                    'duration': f"Error: {e}",
                    'seconds': 0,
                    'modified': datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
    return items

def flatten_tree(tree):
    """Convert tree to columns for display."""
    columns = []
    level_nodes = tree
    total_videos = 0
    total_seconds = 0

    while level_nodes:
        columns.append(level_nodes)
        next_level = []
        for item in level_nodes:
            if item['type'] == 'folder':
                next_level.extend(item.get('children', []))
            elif item['type'] == 'file':
                total_videos += 1
                total_seconds += item.get('seconds', 0)
        level_nodes = next_level

    total_minutes = total_seconds // 60
    return columns, total_videos, total_minutes
