import os
import requests
from dotenv import load_dotenv
from services.video_editor import add_logo
from zernio import Zernio

def main():
    load_dotenv()
    print("--- SpikeSignals Zernio Test ---")
    
    # 1. Download a short dummy video for testing
    video_url = "https://www.w3schools.com/html/mov_bbb.mp4"
    video_path = "sample_video.mp4"
    print("Downloading sample video...")
    response = requests.get(video_url)
    with open(video_path, "wb") as f:
        f.write(response.content)

    # 2. Add logo
    print("Editing video to add logo to the top left...")
    logo_path = os.path.join("logos", "logo.png")
    edited_video_path = os.path.join("output", "edited_sample_video.mp4")
    
    # Create required folders and dummy logo if missing
    os.makedirs("output", exist_ok=True)
    os.makedirs("logos", exist_ok=True)
    if not os.path.exists(logo_path):
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='red')
        img.save(logo_path)

    add_logo(video_path, logo_path, edited_video_path)
    print(f"Video edited successfully! Saved to: {edited_video_path}")

    # 3. Publish via Zernio
    print("\nConnecting to Zernio...")
    api_key = os.getenv("ZERNIO_API_KEY")
    if not api_key:
        print("ERROR: ZERNIO_API_KEY is missing in your .env file!")
        return

    client = Zernio(api_key=api_key)
    
    print("Uploading media to Zernio...")
    try:
        # Use upload_large for videos as they usually exceed 4MB
        upload_res = client.media.upload(file_path=edited_video_path)
        media_url = str(upload_res.files[0].url)
        print(f"Media uploaded successfully! Zernio URL: {media_url}")
    except Exception as e:
        print(f"Failed to upload media to Zernio: {e}")
        return

    # Check connected accounts
    print("Fetching connected Zernio accounts...")
    accounts_res = client.accounts.list()
    yt_account_id = None
    for acc in accounts_res.accounts:
        if acc.platform.value == "youtube" or str(acc.platform).endswith("YOUTUBE"):
            yt_account_id = acc.field_id
            break

    if not yt_account_id:
        print("ERROR: Could not find a connected YouTube account on Zernio.")
        print("Please link your YouTube account on the Zernio dashboard.")
        return

    print(f"Found YouTube Account ID: {yt_account_id}")

    # Create post
    print("\nPublishing post to YouTube via Zernio...")
    caption = "This is an automated test video posted via Zernio! #AI #Automation"
    try:
        result = client.posts.create_post(
            content=caption,
            media_items=[{"type": "video", "url": media_url}],
            platforms=[
                {"platform": "youtube", "accountId": yt_account_id}
            ],
            publish_now=True
        )
        print(f"\nZernio Raw Response: {result}")
    except Exception as e:
        print(f"\nERROR: Failed to create post via Zernio: {e}")

if __name__ == "__main__":
    main()
