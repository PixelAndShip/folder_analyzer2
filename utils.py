import subprocess
#
def get_mp4_duration_in_seconds(filepath):
    try:
        # Using ffprobe for better speed than pymediainfo
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                filepath
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
        )
        return int(float(result.stdout.strip()))
    except Exception:
        return 0
