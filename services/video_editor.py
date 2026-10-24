import os
import shutil
import subprocess

def get_overlay_coords(position: str = "top-left", padding: int = 16) -> str:
    """
    Returns FFmpeg overlay coordinate expression for given position name.
    Supported: top-left, top-right, bottom-left, bottom-right, center.
    """
    pos = (position or "top-left").lower().replace("_", "-").strip()
    if pos == "top-right":
        return f"W-w-{padding}:{padding}"
    elif pos == "bottom-left":
        return f"{padding}:H-h-{padding}"
    elif pos == "bottom-right":
        return f"W-w-{padding}:H-h-{padding}"
    elif pos == "center":
        return f"(W-w)/2:(H-h)/2"
    else:  # default: top-left
        return f"{padding}:{padding}"

def add_logo(video_path: str, logo_path: str, output_path: str, position: str = "top-left"):
    """
    Overlays logo on chosen position using native FFmpeg for ultra-fast processing (< 5-10s).
    Position can be: top-left, top-right, bottom-left, bottom-right, center.
    Falls back to MoviePy if FFmpeg CLI is unavailable.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    coords = get_overlay_coords(position)

    if shutil.which("ffmpeg"):
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", logo_path,
            "-filter_complex", f"[1:v]scale=iw*0.15:-1[logo];[0:v][logo]overlay={coords}",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-c:a", "copy",
            output_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0 and os.path.exists(output_path):
            print(f"[VIDEO_EDITOR] Video branded successfully via FFmpeg ({position}): {output_path}")
            return output_path
        else:
            err_msg = res.stderr.decode("utf-8", errors="ignore")[-300:]
            print(f"[VIDEO_EDITOR] FFmpeg failed, falling back to moviepy: {err_msg}")

    # MoviePy Fallback
    try:
        from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip
    except ImportError:
        raise ImportError("moviepy is not installed. Please pip install moviepy")

    pos_map = {
        "top-left": ("left", "top"),
        "top-right": ("right", "top"),
        "bottom-left": ("left", "bottom"),
        "bottom-right": ("right", "bottom"),
        "center": ("center", "center")
    }
    mpy_pos = pos_map.get((position or "top-left").lower(), ("left", "top"))

    video = VideoFileClip(video_path)
    logo = (ImageClip(logo_path)
            .set_duration(video.duration)
            .resize(width=int(video.size[0] * 0.15))
            .margin(right=12, top=12, opacity=0)
            .set_pos(mpy_pos))

    final = CompositeVideoClip([video, logo])
    final.write_videofile(output_path, codec="libx264", audio_codec="aac")
    video.close()
    final.close()
    return output_path
