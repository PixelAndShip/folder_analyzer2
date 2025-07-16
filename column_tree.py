from pathlib import Path
from pymediainfo import MediaInfo
from datetime import datetime

def get_mp4_duration_in_seconds(filepath):
    try:
        media_info = MediaInfo.parse(filepath)
        for track in media_info.tracks:
            if track.track_type == "Video" and track.duration:
                return int(track.duration // 1000)  # duration in seconds
        return 0
    except Exception:
        return 0

def build_tree(path, base):
    items = []
    for f in sorted(path.iterdir()):
        rel_path = str(f.relative_to(base)).replace("\\", "/")
        if f.is_dir():
            children = build_tree(f, base)
            # Compute recursive totals for this folder by summing children
            total_videos = 0
            total_seconds = 0
            for child in children:
                if child['type'] == 'folder':
                    total_videos += child.get('total_videos', 0)
                    total_seconds += child.get('total_seconds', 0)
                elif child['type'] == 'file':
                    total_videos += 1
                    total_seconds += child.get('seconds', 0)
            items.append({
                'type': 'folder',
                'name': f.name,
                'count': len(list(f.iterdir())),
                'modified': datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'rel_path': rel_path,
                'abs_path': str(f.resolve()),
                'children': children,
                'total_videos': total_videos,
                'total_seconds': total_seconds,
            })
        elif f.suffix.lower() == '.mp4':
            seconds = get_mp4_duration_in_seconds(str(f))
            mins, secs = divmod(seconds, 60)
            duration = f"{mins}m {secs}s"
            items.append({
                'type': 'file',
                'name': f.name,
                'duration': duration,
                'seconds': seconds,
                'modified': datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })
    return items


def flatten_tree(tree):
    """
    For display, returns list of column lists.
    Each column is immediate children for a folder level.
    """
    columns = []
    level_nodes = tree
    while level_nodes:
        if not isinstance(level_nodes, list):
            raise TypeError(f"Flatten_tree: expected list but got {type(level_nodes)}")
        columns.append(level_nodes)
        next_level = None
        for item in level_nodes:
            children = item.get('children')
            if item['type'] == 'folder' and isinstance(children, list) and children:
                next_level = children
                break
        level_nodes = next_level if next_level else []
    return columns
