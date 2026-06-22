import os

def add_logo(video_path: str, logo_path: str, output_path: str):
    """
    Uses moviepy to add a logo to the top left of the video.
    """
    try:
        from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip
    except ImportError:
        raise ImportError("moviepy is not installed. Please pip install moviepy")

    video = VideoFileClip(video_path)
    
    # Load the logo and resize it if needed (e.g., 10% of video width)
    logo = (ImageClip(logo_path)
            .set_duration(video.duration)
            .resize(width=int(video.size[0] * 0.15)) # 15% of width
            .margin(right=8, top=8, opacity=0) # Add a small margin
            .set_pos(("left", "top")))

    # Composite the logo on top of the video
    final = CompositeVideoClip([video, logo])
    
    # Write the result to a file
    final.write_videofile(output_path, codec="libx264", audio_codec="aac")
    
    video.close()
    final.close()
