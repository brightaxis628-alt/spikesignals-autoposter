import os
from zernio import Zernio

def get_zernio_client():
    api_key = os.getenv("ZERNIO_API_KEY")
    if not api_key:
        raise Exception("ZERNIO_API_KEY is missing in .env")
    return Zernio(api_key=api_key)

def publish_video(video_url: str, caption: str, platform: str):
    """
    Publishes a video to the specified platform using Zernio.
    Automatically fetches the connected account for that platform.
    """
    client = get_zernio_client()
    
    # Fetch all connected accounts to find the account ID for the platform
    accounts_res = client.accounts.list()
    
    account_id = None
    for account in accounts_res.accounts:
        if account.platform.value == platform or str(account.platform).endswith(platform.upper()):
            account_id = account.field_id
            break
            
    if not account_id:
        raise Exception(f"No connected account found for platform: {platform}")

    # Create and publish the post
    result = client.posts.create_post(
        content=caption,
        media_items=[{"type": "video", "url": video_url}],
        platforms=[
            {"platform": platform, "accountId": account_id}
        ],
        publish_now=True
    )
    
    return result
