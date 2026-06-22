import os
import requests
from services.video_editor import add_logo
from services.youtube_service import upload_video

def main():
    print("--- SpikeSignals YouTube Test ---")
    
    # 1. Download a short dummy video for testing
    video_path = "uploads/sample_video.mp4"
    if not os.path.exists(video_path):
        print("Downloading a 10-second sample video...")
        sample_video_url = "https://www.w3schools.com/html/mov_bbb.mp4"
        with open(video_path, 'wb') as f:
            f.write(requests.get(sample_video_url).content)
    
    # 2. Check for logo (Create a temporary red square if it doesn't exist)
    logo_path = "logos/logo.png"
    if not os.path.exists(logo_path):
        print("No logo found in logos/ folder. Generating a temporary red square logo...")
        try:
            from PIL import Image
            img = Image.new('RGBA', (200, 200), color=(255, 0, 0, 255))
            img.save(logo_path)
        except ImportError:
            print("Pillow not installed. Please add a logo.png to the logos/ folder manually.")
            return

    # 3. Add the logo to the video
    output_path = "output/edited_sample_video.mp4"
    print("Editing video to add logo to the top left...")
    try:
        add_logo(video_path, logo_path, output_path)
        print(f"Video edited successfully! Saved to: {output_path}")
    except Exception as e:
        print(f"Error editing video: {e}")
        return

    # 4. Upload to YouTube
    print("\nAttempting to authenticate and upload to YouTube...")
    print("NOTE: A browser window should pop up asking you to log into Google.")
    try:
        video_id = upload_video(
            video_path=output_path,
            title="Automated Test Video - SpikeSignals",
            description="Testing the automated YouTube upload pipeline."
        )
        print(f"\n✅ SUCCESS! Video uploaded to YouTube.")
        print(f"🔗 Watch it here: https://youtu.be/{video_id}")
        print("Note: The video is set to Private by default for testing purposes.")
    except Exception as e:
        print(f"\n❌ Error uploading to YouTube: {e}")

if __name__ == "__main__":
    main()
