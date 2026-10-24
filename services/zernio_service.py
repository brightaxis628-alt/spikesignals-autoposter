import os
from pathlib import Path
from dotenv import load_dotenv
from zernio import Zernio

load_dotenv()

def get_zernio_client() -> Zernio:
    api_key = os.getenv("ZERNIO_API_KEY")
    if not api_key:
        raise Exception("ZERNIO_API_KEY is missing in .env")
    return Zernio(api_key=api_key)

def publish_video(video_source: str, caption: str, platform: str):
    """
    Publishes a video to Instagram or TikTok using Zernio.
    - If video_source is a local file (e.g. in output/), uploads it directly to Zernio CDN.
    - Automatically discovers connected Instagram and TikTok account IDs from Zernio.
    """
    client = get_zernio_client()
    platform_clean = platform.lower()

    # 1. Discover connected account ID for the platform
    account_id = None
    accounts_res = client.accounts.list()
    for account in accounts_res.accounts:
        p_val = getattr(account.platform, "value", str(account.platform)).lower()
        if p_val == platform_clean or str(account.platform).endswith(platform_clean.upper()):
            account_id = account.field_id
            break

    if not account_id:
        raise Exception(f"No connected account found in Zernio for platform: {platform}")

    # 2. Resolve media URL: Upload local video directly to Zernio CDN if available
    media_url = video_source
    local_path = None

    if os.path.exists(video_source):
        local_path = video_source
    elif "/output/" in video_source:
        candidate = os.path.join("output", video_source.split("/output/")[-1].split("?")[0])
        if os.path.exists(candidate):
            local_path = candidate

    if local_path and os.path.exists(local_path):
        print(f"[ZERNIO] Uploading local file '{local_path}' directly to Zernio CDN...")
        upload_resp = client.media.upload(file_path=local_path)
        if upload_resp.files:
            media_url = str(upload_resp.files[0].url)
            print(f"[ZERNIO] File uploaded to Zernio CDN: {media_url}")

    # 3. Create and publish the post immediately
    print(f"[ZERNIO] Publishing post to {platform_clean} (account: {account_id})...")
    result = client.posts.create_post(
        content=caption,
        media_items=[{"type": "video", "url": media_url}],
        platforms=[
            {"platform": platform_clean, "accountId": account_id}
        ],
        publish_now=True
    )

    return result
