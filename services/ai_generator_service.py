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
    Directly analyzes the video title, topic, entities, and context
    to generate customized viral titles, YouTube/TikTok descriptions, and Instagram captions.
    Cleans raw filenames and Instagram CTA strings into clean, high-CTR social content.
    """
    raw_title = (title or "").strip()
    t = raw_title

    # 1. Strip leading emojis & decorative symbols
    t = re.sub(r'^[\U00010000-\U0010ffff\u2600-\u27ff\u200d\s\💭\👇\🔥\🚀\📈\💡\⚡\📊\✨]+', '', t).strip()

    # 2. Normalize and clean uploaded filenames (e.g. SpikeSignals_CompletePicture_Real_35s.mp4)
    is_filename = '_' in t or t.endswith('.mp4') or re.search(r'\b\d+s\b', t, re.IGNORECASE)
    if is_filename:
        t = re.sub(r'\.(mp4|mov|avi|mkv)$', '', t, flags=re.IGNORECASE)
        t = re.sub(r'[\_\-]+(real|\d+s|final|v\d+|\d+p|cut|edit).*$', '', t, flags=re.IGNORECASE)
        t = t.replace('_', ' ')
        t = re.sub(r'([a-z])([A-Z])', r'\1 \2', t)
        t = t.strip()

    # 3. Detect and purify Instagram CTA captions (e.g. 'Drop a "Start" below and I will send you a free PDF...')
    is_cta = False
    cta_keyword = "START"
    m_cta = re.search(r'(drop|comment|dm|type|reply)\s+(?:a\s+|an\s+)?[\"\'\“\”]?([A-Za-z0-9]+)[\"\'\“\”]?\s+(below|and|to|for|in)\s*(.*)', t, re.IGNORECASE)
    if m_cta:
        is_cta = True
        cta_keyword = m_cta.group(2).upper()
        rest = m_cta.group(4).lower()
        if 'pdf' in rest or 'guide' in rest or 'roadmap' in rest:
            t = "The Free Step-By-Step Trading Roadmap"
        elif 'strategy' in rest:
            t = "The Complete Trading Strategy Blueprint"
        else:
            t = "Step-By-Step Trading Mastery Guide"

    # 4. Clean channel tags and boilerplate suffixes
    if " | " in t:
        t = t.split(" | ")[0].strip()
    elif uploader and f" - {uploader}" in t:
        t = t.replace(f" - {uploader}", "").strip()
    
    clean_title = re.sub(r'\[(Official|Music Video|HD|4K|Shorts|202\d).*?\]', '', t, flags=re.IGNORECASE).strip()
    clean_title = re.sub(r'\((Official|Music Video|HD|4K|Shorts|202\d).*?\)', '', clean_title, flags=re.IGNORECASE).strip()
    if not clean_title or len(clean_title) < 4:
        clean_title = "SpikeSignals Trading Strategy"

    # Context analysis
    combined_ctx = f"{clean_title} {topic}".lower()
    is_spikesignals = 'spikesignal' in combined_ctx.replace(' ', '') or 'spike signal' in combined_ctx
    is_trading = is_spikesignals or is_cta or any(k in combined_ctx for k in ['trad', 'stock', 'invest', 'forex', 'crypto', 'wealth', 'market', 'filter', 'chart', 'profit'])
    is_tech = any(k in combined_ctx for k in ['ai', 'tech', 'software', 'app', 'code', 'future', 'robot'])

    # 5. GENERATE TITLE VARIATIONS (Similar, High-CTR, NEVER Raw/Identical)
    if is_spikesignals:
        title_candidates = [
            "SpikeSignals: The Complete Trading System Overview 📈",
            "How SpikeSignals Confirms High-Probability Setups 🚀",
            "The Ultimate Confirmation Tool For Traders: SpikeSignals 💡",
            "SpikeSignals In Action: Precision Algorithmic Signals ⚡"
        ]
    elif is_cta:
        title_candidates = [
            "The Free Step-By-Step Trading Roadmap (Full PDF Guide) 📊",
            "How To Trade With A Proven Blueprint: Free Guide 🚀",
            "Stop Trading Without A Plan: The Step-By-Step Roadmap 💡",
            "The Exact Roadmap Every Profitable Trader Follows 🔥"
        ]
    else:
        title_candidates = []
        # Pattern A: 'Why [Subject] [Verb] [Action]'
        m_why = re.match(r'^Why\s+(.+?)\s+(is|are|will|could|might)\s+(.+)$', clean_title, re.IGNORECASE)
        if m_why:
            subj = m_why.group(1).strip()
            act = m_why.group(3).strip()
            verb_agree = "Are" if (subj.lower().endswith('s') or " and " in subj.lower()) else "Is"
            act_phrase = "Rally" if 'rebound' in act.lower() else ("Drop" if 'crash' in act.lower() else act)
            title_candidates.extend([
                f"The Massive {subj} {act_phrase} Nobody Sees Coming 📈",
                f"Is A Huge {subj} Move Starting Right Now? 🚀",
                f"What Most Investors Miss About The {subj} {act_phrase} 💡",
                f"Get Ready: {subj} {verb_agree} Gearing Up For A Big Run ⚡",
                f"The {subj} Reversal You Need To Watch 📊",
                f"Why Smart Money Is Eyeing {subj} Right Now 🔥"
            ])
        # Pattern B: 'How To [Action]'
        m_how = re.match(r'^How\s+To\s+(.+)$', clean_title, re.IGNORECASE)
        if m_how:
            act = m_how.group(1).strip()
            title_candidates.extend([
                f"The Smart Way To {act} (Step-By-Step) 💡",
                f"Master {act}: Key Secrets Revealed 🚀",
                f"Stop Doing It Wrong: How To Actually {act} ✨",
                f"The Proven Blueprint To {act} 📈"
            ])
        # Pattern C: 'I [Did X]... [Result]'
        m_i = re.match(r'^I\s+(.+?)\s*[\.\,\;\:\-]\s*(.+)$', clean_title, re.IGNORECASE)
        if m_i:
            did, outcome = m_i.group(1).strip(), m_i.group(2).strip()
            title_candidates.extend([
                f"{outcome}! (Testing {did}) 📊",
                f"What Happened When I Tested: {did} 🚀",
                f"The Shocking Result: {outcome} 💡",
                f"Testing {did} — Here Are The Only Winners 🔥"
            ])
        # Pattern D: Numbers
        m_num = re.match(r'^(\d+)\s+(.+)$', clean_title, re.IGNORECASE)
        if m_num:
            num, rest = m_num.group(1), m_num.group(2).strip()
            title_candidates.extend([
                f"The Top {num} {rest} You Need To Know 💡",
                f"{num} Essential {rest} That Actually Work 🚀",
                f"Ranking The {num} Best {rest} (Honest Review) 📊"
            ])
        if not title_candidates:
            title_candidates.extend([
                f"What Most People Miss About {clean_title} 💡",
                f"The Real Truth Behind {clean_title} 📊",
                f"Deep Dive Breakdown: {clean_title} ⚡",
                f"Why Everyone Is Watching {clean_title} 🚀"
            ])

    # Filter out any exact duplicate of raw title
    filtered = [c for c in title_candidates if c.strip().lower() != raw_title.strip().lower()]
    chosen_title = random.choice(filtered if filtered else title_candidates)
    if len(chosen_title) > 75:
        chosen_title = f"{chosen_title[:70]}... 🚀"

    # 6. EXTRACT KEYWORDS & HASHTAGS
    words = re.findall(r'[a-zA-Z]{3,}', f"{clean_title} {topic}".lower())
    stop_words = {
        'the', 'and', 'for', 'that', 'this', 'with', 'from', 'have', 'only', 'ran', 
        'through', 'video', 'watch', 'are', 'was', 'were', 'will', 'you', 'your', 'about',
        'what', 'when', 'where', 'which', 'who', 'how', 'why', 'can', 'could', 'drop', 'start', 'send'
    }
    extracted_keywords = [w for w in words if w not in stop_words][:6]
    hashtags = [f"#{k}" for k in extracted_keywords]

    if is_spikesignals:
        hashtags = ['#spikesignals', '#tradingbot', '#tradingindicators', '#stockmarket', '#forextrading', '#crypto', '#tradingstrategy']
    elif is_trading:
        hashtags.extend(['#trading', '#stocks', '#stockmarket', '#investing', '#forex', '#wealthbuilding', '#daytrader'])
    elif is_tech:
        hashtags.extend(['#technology', '#techtrends', '#futuretech', '#innovation', '#smarttech', '#ai'])
    else:
        hashtags.extend(['#trending', '#viral', '#explore', '#mustwatch', '#viralvideo'])

    unique_tags = list(dict.fromkeys(hashtags))
    desc_tags = " ".join(unique_tags[:8])
    caption_tags = " ".join(unique_tags[:15])

    # 7. GENERATE PROFESSIONAL DESCRIPTIONS
    if is_spikesignals:
        description = (
            "A complete overview of SpikeSignals in action. Learn how real-time momentum indicators, "
            "algorithmic confirmations, and disciplined risk management help traders capture major trends.\n\n"
            f"{desc_tags}"
        )
    elif is_cta:
        description = (
            "Looking for a structured roadmap to level up your trading? Here is the exact framework to follow, "
            "covering market structure, high-probability execution, and capital protection.\n\n"
            f"{desc_tags}"
        )
    elif is_trading:
        description = (
            f"Deep dive breakdown on {clean_title}. Discover key levels, market sentiment, "
            f"and actionable insights to help you navigate upcoming price action.\n\n"
            f"{desc_tags}"
        )
    else:
        description = (
            f"Comprehensive breakdown on {clean_title}. Exploring the key lessons, industry shifts, "
            f"and what this means moving forward.\n\n"
            f"{desc_tags}"
        )

    # 8. GENERATE HIGH-CONVERTING INSTAGRAM CAPTIONS
    if is_spikesignals:
        caption = (
            "Ready to see the complete picture in your trading? 📊⚡\n\n"
            "Consistent trading isn't about guessing—it's about having reliable confirmation when volatility hits.\n\n"
            "💡 SpikeSignals delivers real-time algorithmic confirmations to give you clarity on every entry and exit.\n\n"
            "💬 Drop a comment below if you want more details on the setup!\n"
            "📌 Bookmark and share this reel with a fellow trader.\n\n"
            f"{caption_tags}"
        )
    elif is_cta:
        caption = (
            "Want the complete step-by-step trading roadmap? 📈👇\n\n"
            "Most traders get overwhelmed trying to piece together random strategies. "
            "Having a single, disciplined blueprint is what separates consistent execution from costly mistakes.\n\n"
            f"💬 Drop '{cta_keyword}' in the comments below to receive the complete guide!\n"
            "📌 Save this post so you don't lose it on your feed.\n\n"
            f"{caption_tags}"
        )
    else:
        caption = (
            f"What are your thoughts on this? 👀👇\n\n"
            f"💡 Key Takeaways from {clean_title}:\n"
            "• Understand the underlying trends driving the move\n"
            "• Protect your capital and manage your positioning\n"
            "• Focus on high-probability setups rather than chasing noise\n\n"
            "💬 Do you agree with this perspective? Drop your thoughts below!\n"
            "📌 Bookmark this reel to keep this breakdown handy.\n\n"
            f"{caption_tags}"
        )

    return {
        "title": chosen_title,
        "description": description,
        "caption": caption
    }
