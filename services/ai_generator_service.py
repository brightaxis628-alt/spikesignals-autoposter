import os
import re
import time
import random
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

        system_prompt = (
            "You are an expert social media content creator. Given a trending topic, generate 3 different visual prompts for an AI Video Generator (like Kling or Sora). "
            "1 for Instagram (aesthetic, vertical), 1 for TikTok (trendy, fast-paced, vertical), and 1 for YouTube (detailed, cinematic, horizontal). "
            "Return ONLY a JSON object with keys: 'instagram', 'tiktok', 'youtube' containing the prompts."
        )

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
    Requires KLING_API_KEY to be set in .env.
    """
    if not KLING_API_KEY:
        raise ValueError("KLING_API_KEY is missing! Please provide the Kling API Key in the .env file.")

    print(f"Requesting Kling 3.0 video for {platform} with prompt: {prompt}")

    headers = {
        "Authorization": f"Bearer {KLING_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "kling-v1",
        "prompt": prompt,
        "aspect_ratio": "9:16" if platform in ["tiktok", "instagram"] else "16:9",
        "duration": "5"
    }

    submit_url = "https://api.klingai.com/v1/videos/text2video"
    submit_res = requests.post(submit_url, headers=headers, json=payload)

    if submit_res.status_code != 200:
        raise Exception(f"Kling API Error: {submit_res.text}")

    task_id = submit_res.json().get("data", {}).get("task_id")
    if not task_id:
        raise Exception("Failed to get task_id from Kling API")

    print(f"Task submitted! Task ID: {task_id}. Polling for completion...")

    poll_url = f"https://api.klingai.com/v1/videos/text2video/{task_id}"
    video_url = None

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

    print(f"Video generated successfully! Downloading from {video_url}...")
    import uuid
    output_filename = f"kling_{platform}_{uuid.uuid4().hex[:6]}.mp4"
    output_path = f"output/{output_filename}"

    video_data = requests.get(video_url).content
    with open(output_path, "wb") as f:
        f.write(video_data)

    return output_filename


def generate_viral_copy(title: str, topic: str = "", original_desc: str = "", uploader: str = "") -> dict:
    """
    Context-aware viral copy generator.
    Directly analyzes the ACTUAL video title, topic, entities, and context
    to generate customized viral titles, YouTube/TikTok descriptions, and Instagram captions.
    Uses OpenAI if configured; otherwise runs high-precision contextual NLP generation.
    """
    raw_title = (title or "").strip()
    clean_title = raw_title
    if " | " in raw_title:
        clean_title = raw_title.split(" | ")[0].strip()
    elif uploader and f" - {uploader}" in raw_title:
        clean_title = raw_title.replace(f" - {uploader}", "").strip()
    
    clean_title = re.sub(r'\[(Official|Music Video|HD|4K|Shorts|202\d).*?\]', '', clean_title, flags=re.IGNORECASE).strip()
    clean_title = re.sub(r'\((Official|Music Video|HD|4K|Shorts|202\d).*?\)', '', clean_title, flags=re.IGNORECASE).strip()
    if not clean_title or len(clean_title) < 4:
        clean_title = raw_title or "Trending Video"

    # 1. Try OpenAI if key is present
    if OPENAI_API_KEY and OPENAI_API_KEY != "":
        try:
            from openai import OpenAI
            import json
            client = OpenAI(api_key=OPENAI_API_KEY)
            system_prompt = (
                "You are an elite viral social media copywriter. Given a video title and creator context, create fresh, highly relevant content:\n"
                "1. 'title': High-CTR viral headline under 65 chars strictly focused on the video's actual subject (with relevant emoji).\n"
                "2. 'description': 2-sentence breakdown mentioning the specific subject + 6-8 targeted hashtags.\n"
                "3. 'caption': Attention-grabbing Instagram hook with an engagement question asking opinions about this exact topic, plus 12-15 relevant hashtags.\n"
                "Return ONLY valid JSON with keys 'title', 'description', 'caption'."
            )
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Original Video Title: {raw_title}\nTopic/Query: {topic}\nCreator: {uploader}\nDetails: {original_desc[:300]}"}
                ],
                response_format={"type": "json_object"},
                timeout=12
            )
            data = json.loads(response.choices[0].message.content)
            if data.get("title") and data.get("caption"):
                return {
                    "title": data.get("title"),
                    "description": data.get("description", ""),
                    "caption": data.get("caption", "")
                }
        except Exception as e:
            print(f"[COPYWRITER] OpenAI API error/skip: {e}, using contextual NLP engine.")

    # 2. CONTEXTUAL NLP COPYWRITING ENGINE (Derived directly from video title & topic)
    parts = [p.strip() for p in re.split(r'[\.\:\!\?\|]', clean_title) if p.strip()]
    lead_part = parts[0] if parts else clean_title
    punch_part = parts[1] if len(parts) > 1 else parts[0]
    numbers = re.findall(r'\b\d+\b', clean_title)

    # Dynamic viral titles maintaining 100% of the original video context
    if len(parts) >= 2 and len(numbers) >= 2:
        title_candidates = [
            f"{punch_part}! 📊 ({lead_part})",
            f"{clean_title} 🚀 (Breakdown)",
            f"{lead_part} — {punch_part} 🔥",
            f"Must-Watch: {clean_title} 💡",
            f"Wait Till You See: {clean_title} ✨"
        ]
    elif len(parts) >= 2:
        title_candidates = [
            f"{lead_part}: {punch_part} 💡",
            f"Must-Watch: {clean_title} 🔥",
            f"{punch_part}! ({lead_part}) 📊",
            f"{clean_title} 🚀",
            f"The Real Truth Behind {clean_title} ⚡"
        ]
    else:
        title_candidates = [
            f"Must-Watch: {clean_title} 🔥",
            f"{clean_title} 💡 (Explained)",
            f"The Truth About {clean_title} 📊",
            f"Why Everyone Is Watching: {clean_title} 🚀",
            f"{clean_title} ✨"
        ]

    chosen_title = random.choice(title_candidates)
    if len(chosen_title) > 75:
        chosen_title = f"{clean_title[:68]}... 🚀"

    # Contextual keywords and hashtags derived directly from title words
    words = re.findall(r'[a-zA-Z]{3,}', f"{clean_title} {topic}".lower())
    stop_words = {
        'the', 'and', 'for', 'that', 'this', 'with', 'from', 'have', 'only', 'ran', 
        'through', 'video', 'watch', 'are', 'was', 'were', 'will', 'you', 'your', 'about',
        'what', 'when', 'where', 'which', 'who', 'how', 'why', 'can', 'could'
    }
    extracted_keywords = [w for w in words if w not in stop_words][:6]
    hashtags = [f"#{k}" for k in extracted_keywords]

    # Add relevant niche community hashtags across all domains
    combined_ctx = f"{clean_title} {topic}".lower()
    if any(k in combined_ctx for k in ['stock', 'ai', 'invest', 'trad', 'wealth', 'money', 'filter', 'crypto', 'market', 'bitcoin', 'finance']):
        hashtags.extend(['#investing', '#stocks', '#stockmarket', '#wealth', '#finance', '#financialfreedom', '#moneytips'])
    elif any(k in combined_ctx for k in ['business', 'startup', 'entrepreneur', 'sales', 'marketing', 'agency', 'income', 'hustle']):
        hashtags.extend(['#business', '#entrepreneurship', '#startuptips', '#marketing', '#successmindset', '#growth'])
    elif any(k in combined_ctx for k in ['tech', 'code', 'software', 'app', 'robot', 'future', 'developer', 'hardware', 'cyber']):
        hashtags.extend(['#technology', '#techtrends', '#futuretech', '#innovation', '#smarttech', '#coding'])
    elif any(k in combined_ctx for k in ['fitness', 'gym', 'workout', 'muscle', 'health', 'diet', 'cardio', 'bodybuilding']):
        hashtags.extend(['#fitness', '#workout', '#gymlife', '#fitfam', '#healthylifestyle', '#bodybuilding'])
    elif any(k in combined_ctx for k in ['game', 'gaming', 'gamer', 'esports', 'playstation', 'xbox', 'nintendo', 'steam']):
        hashtags.extend(['#gaming', '#gamer', '#gamersofig', '#gameplay', '#esports', '#gamingcommunity'])
    elif any(k in combined_ctx for k in ['travel', 'trip', 'flight', 'destination', 'vacation', 'hotel']):
        hashtags.extend(['#travel', '#wanderlust', '#exploretheworld', '#travelgram', '#vacationvibes'])
    elif any(k in combined_ctx for k in ['food', 'recipe', 'cook', 'chef', 'kitchen', 'eat', 'dish', 'tasty']):
        hashtags.extend(['#foodie', '#recipes', '#homecooking', '#tasty', '#foodlover', '#instafood'])
    else:
        hashtags.extend(['#trending', '#viral', '#explore', '#mustwatch', '#viralvideo', '#dailyviral'])

    unique_tags = list(dict.fromkeys(hashtags))
    desc_tags = " ".join(unique_tags[:8])
    caption_tags = " ".join(unique_tags[:15])

    source_info = f" by {uploader}" if uploader and uploader != "YouTube Creator" else ""

    # Varied descriptions strictly focused on this video
    desc_templates = [
        f"Deep dive breakdown: {clean_title}{source_info}! Key takeaways, insights, and lessons you need to know.\n\n{desc_tags}",
        f"Everything you need to know about {clean_title}{source_info}. Watch the full breakdown!\n\n{desc_tags}",
        f"Breaking down: {clean_title}! An eye-opening look at this topic{source_info}. What are your thoughts?\n\n{desc_tags}"
    ]
    description = random.choice(desc_templates)

    # Varied Instagram captions with high-engagement hooks referencing the exact topic
    caption_templates = [
        (
            f"What do you think about this? 👀👇\n\n"
            f"💡 {clean_title}\n\n"
            f"Would you agree with this breakdown? Drop your thoughts, favorite picks, or questions below!\n\n"
            f"📌 Bookmark & save this reel for reference!\n"
            f"👥 Share with someone who needs to see this!\n\n"
            f"{caption_tags}"
        ),
        (
            f"Did you know about this? 🤯⚡\n\n"
            f"🔍 {clean_title}{source_info}\n\n"
            f"Tag a friend who needs to see this insight! What is your biggest takeaway?\n\n"
            f"💬 Let us know in the comments below! 👇\n"
            f"📌 Save this post to revisit anytime.\n\n"
            f"{caption_tags}"
        ),
        (
            f"Wait till you see this! 🔥\n\n"
            f"📊 {clean_title}\n\n"
            f"Key insights and takeaways that everyone is talking about.\n\n"
            f"👇 Drop a 'YES' if you agree or share your perspective!\n"
            f"📌 Don't forget to bookmark and share this reel.\n\n"
            f"{caption_tags}"
        )
    ]
    caption = random.choice(caption_templates)

    return {
        "title": chosen_title,
        "description": description,
        "caption": caption
    }
