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
    Since Kling API keys are pending from HR, this provides a fallback that copies
    our sample video to simulate a successful generation pipeline.
    """
    print(f"Requesting Kling 3.0 video for {platform} with prompt: {prompt}")
    
    if KLING_API_KEY:
        # Placeholder for actual Kling API HTTP request once keys are provided
        # Example: requests.post("https://api.klingai.com/v1/videos/text2video", ...)
        pass
    
    # Simulate API delay
    time.sleep(3)
    
    # Fallback to local sample video for demo purposes
    import shutil
    import uuid
    output_filename = f"kling_{platform}_{uuid.uuid4().hex[:6]}.mp4"
    output_path = f"output/{output_filename}"
    
    # Copy our sample video to act as the "generated" video
    try:
        shutil.copy("uploads/sample_video.mp4", output_path)
    except FileNotFoundError:
        # If sample_video doesn't exist, create a dummy file just to prevent crashes
        with open(output_path, "wb") as f:
            f.write(b"dummy video content")
            
    return output_filename
