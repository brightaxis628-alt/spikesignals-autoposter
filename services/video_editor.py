import os
import shutil
import subprocess

def add_logo(video_path: str, logo_path: str, output_path: str):
    """
    Overlays logo on top-left of video using native FFmpeg for ultra-fast processing (< 5-10s).
    Falls back to MoviePy if FFmpeg CLI is unavailable.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    if shutil.which("ffmpeg"):
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", logo_path,
            "-filter_complex", "[1:v]scale=iw*0.15:-1[logo];[0:v][logo]overlay=12:12",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-c:a", "copy",
            output_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0 and os.path.exists(output_path):
            print(f"[VIDEO_EDITOR] Video branded successfully via FFmpeg in seconds: {output_path}")
            return output_path
        else:
            err_msg = res.stderr.decode("utf-8", errors="ignore")[-300:]
            print(f"[VIDEO_EDITOR] FFmpeg failed, falling back to moviepy: {err_msg}")

    # MoviePy Fallback
    try:
        from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip
    except ImportError:
        raise ImportError("moviepy is not installed. Please pip install moviepy")

    video = VideoFileClip(video_path)
    logo = (ImageClip(logo_path)
            .set_duration(video.duration)
            .resize(width=int(video.size[0] * 0.15))
            .margin(right=8, top=8, opacity=0)
            .set_pos(("left", "top")))

    final = CompositeVideoClip([video, logo])
    final.write_videofile(output_path, codec="libx264", audio_codec="aac")
    video.close()
    final.close()
    return output_path
