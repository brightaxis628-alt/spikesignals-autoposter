import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
KLING_API_KEY = os.getenv("KLING_API_KEY")

def generate_video_prompts(search_heading: str) -> dict:
    """
    Generates 3 different video prompts based on a single search heading.
    If OpenAI API key is missing, falls back to a mock response for testing.
    """
    if not OPENAI_API_KEY or OPENAI_API_KEY == "":
        return {
            "instagram": f"A vertical, highly engaging cinematic video about {search_heading} optimized for Reels.",
            "tiktok": f"A fast-paced, trendy vertical video about {search_heading} with quick cuts.",
            "youtube": f"A detailed, high-quality landscape video exploring the topic of {search_heading}."
        }

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        system_prompt = "You are an expert social media content creator. Given a trending topic, generate 3 different visual prompts for an AI Video Generator (like Kling or Sora). 1 for Instagram (aesthetic, vertical), 1 for TikTok (trendy, fast-paced, vertical), and 1 for YouTube (detailed, cinematic, horizontal). Return ONLY a JSON object with keys: 'instagram', 'tiktok', 'youtube' containing the prompts."
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": search_heading}
            ],
            response_format={ "type": "json_object" }
        )
        import json
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"OpenAI Error: {e}")
        return {
            "instagram": f"IG Video for {search_heading}",
            "tiktok": f"TikTok Video for {search_heading}",
            "youtube": f"YT Video for {search_heading}"
        }

def generate_kling_video(prompt: str, platform: str) -> str:
    """
    Calls the Kling 3.0 API to generate a video.
    This is the FULL production code. It requires KLING_API_KEY to be set in .env.
    """
    if not KLING_API_KEY:
        raise ValueError("KLING_API_KEY is missing! Please tell Vineet to provide the Kling API Key so it can be added to the .env file. The architecture is fully ready.")

    print(f"Requesting Kling 3.0 video for {platform} with prompt: {prompt}")
    
    # 1. Submit the Text-to-Video Task
    headers = {
        "Authorization": f"Bearer {KLING_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "kling-v1",
        "prompt": prompt,
        # Depending on Kling API docs, you can adjust aspect ratio (e.g. 9:16 for TikTok/IG, 16:9 for YouTube)
        "aspect_ratio": "9:16" if platform in ["tiktok", "instagram"] else "16:9",
        "duration": "5" # Standard free tier duration
    }
    
    # NOTE: The exact endpoint URL might vary based on Kling's official documentation.
    # This uses the standard standard structure for AI Video APIs.
    submit_url = "https://api.klingai.com/v1/videos/text2video"
    submit_res = requests.post(submit_url, headers=headers, json=payload)
    
    if submit_res.status_code != 200:
        raise Exception(f"Kling API Error: {submit_res.text}")
        
    task_id = submit_res.json().get("data", {}).get("task_id")
    if not task_id:
        raise Exception("Failed to get task_id from Kling API")
        
    print(f"Task submitted! Task ID: {task_id}. Polling for completion...")
    
    # 2. Poll for Completion
    poll_url = f"https://api.klingai.com/v1/videos/text2video/{task_id}"
    video_url = None
    
    # Poll every 10 seconds for up to 5 minutes
    for _ in range(30):
        time.sleep(10)
        poll_res = requests.get(poll_url, headers=headers)
        if poll_res.status_code == 200:
            data = poll_res.json().get("data", {})
            status = data.get("task_status")
            
            if status == "succeed":
                video_url = data.get("task_result", {}).get("videos", [{}])[0].get("url")
                break
            elif status == "failed":
                raise Exception("Kling Video Generation Failed inside the API.")
        
    if not video_url:
        raise Exception("Kling Video Generation timed out after 5 minutes.")
        
    # 3. Download the Video
    print(f"Video generated successfully! Downloading from {video_url}...")
    import uuid
    output_filename = f"kling_{platform}_{uuid.uuid4().hex[:6]}.mp4"
    output_path = f"output/{output_filename}"
    
    video_data = requests.get(video_url).content
    with open(output_path, "wb") as f:
        f.write(video_data)
        
    return output_filename
