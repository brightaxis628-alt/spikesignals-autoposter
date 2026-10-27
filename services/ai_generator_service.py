import os
import re
import time
import random
import shutil
import base64
import json
import subprocess
import requests
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
KLING_API_KEY = os.getenv("KLING_API_KEY")

GENERIC_CAMERA_PATTERN = re.compile(
    r'(whats\s*app\s*video|screen\s*recording|untitled|vid_\d+|img_\d+|pxl_\d+|\b\d{4}[-_]\d{2}[-_]\d{2}\b|at\s+\d{1,2}[\.:]\d{2}[\.:]\d{2}|video_\d+|mov_\d+)',
    re.IGNORECASE
)

def get_ffmpeg_exe():
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"

def get_ai_client():
    try:
        from openai import OpenAI
        if OPENROUTER_API_KEY and OPENROUTER_API_KEY.strip():
            return OpenAI(api_key=OPENROUTER_API_KEY.strip(), base_url="https://openrouter.ai/api/v1"), OPENROUTER_MODEL
        elif OPENAI_API_KEY and OPENAI_API_KEY.strip():
            return OpenAI(api_key=OPENAI_API_KEY.strip()), "gpt-4o-mini"
    except Exception as e:
        print(f"Error initializing AI client: {e}")
    return None, None

def get_video_duration(video_path: str) -> float:
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return float(res.stdout.strip())
    except Exception:
        return 5.0

def analyze_video_frames(video_path: str, hint_topic: str = "trading") -> Optional[dict]:
    """
    Extracts 2-3 key frames from a downloaded/uploaded video file on disk
    and passes them to Multimodal AI Vision to inspect the actual scenes.
    """
    if not video_path or not os.path.exists(video_path):
        return None

    client, model = get_ai_client()
    if not client:
        return None

    ffmpeg_bin = get_ffmpeg_exe()
    dur = get_video_duration(video_path)
    timestamps = [max(0.5, dur * 0.15), max(1.0, dur * 0.5), max(1.5, dur * 0.8)]

    temp_frames = []
    images = []

    pid = os.getpid()
    rnd = int(time.time() * 1000) % 100000

    for i, ts in enumerate(timestamps):
        out_f = f"temp_vframe_{pid}_{rnd}_{i}.jpg"
        cmd = [
            ffmpeg_bin, "-y", "-ss", str(ts), "-i", video_path,
            "-frames:v", "1", "-vf", "scale=640:-1", "-q:v", "3", out_f
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(out_f):
            temp_frames.append(out_f)
            try:
                with open(out_f, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                    images.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                    })
            except Exception as e:
                print(f"Error reading frame {out_f}: {e}")

    for f in temp_frames:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass

    if not images:
        return None

    topic_instruction = f"Topic hint: {hint_topic}." if hint_topic else ""

    prompt = (
        "You are an elite viral social media copywriter and growth strategist for TikTok, Instagram Reels, and YouTube Shorts.\n"
        "Look at these actual video visual frames and inspect what is happening inside the video (scene, action, subject, charts, text overlays, emotions, environment).\n"
        f"{topic_instruction}\n\n"
        "CRITICAL RULES:\n"
        "1. NEVER mention raw filenames, file extensions (.mp4), device names, camera tags, or timestamps (e.g. NEVER use words like 'WhatsApp Video', 'VID_', 'IMG_', 'Screen Recording', '2026-10-22', 'at 20.39.55').\n"
        "2. Identify the real subject matter (e.g. trading chart/indicators, market breakdown, podcast/interview, software demo, fitness, comedy, travel, nature, etc.).\n"
        "3. If trading charts or indicators (or SpikeSignals) are shown, focus on market momentum, technical setups, and risk management.\n"
        "4. Generate high-CTR, authentic, viral copy:\n"
        "   - 'title': Punchy viral title (under 65 chars with 1 relevant emoji). Never generic.\n"
        "   - 'description': Engaging 2-3 sentence description summarizing what the viewer is seeing, followed by 6-8 relevant hashtags.\n"
        "   - 'caption': High-converting Instagram caption with a visual hook, 2-3 bulleted key takeaways/observations, an engaging question prompting comments, and 12-15 targeted hashtags.\n\n"
        "Return ONLY a valid JSON object with keys: 'title', 'description', 'caption'."
    )

    content = [{"type": "text", "text": prompt}] + images

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],
            response_format={"type": "json_object"}
        )
        data = json.loads(resp.choices[0].message.content)
        if "title" in data and "description" in data and "caption" in data:
            data["analyzed_from"] = "multimodal_vision"
            return data
    except Exception as e:
        print(f"Multimodal vision analysis error: {e}")

    return None

def analyze_visual_content(video_path: Optional[str] = None, image_url: Optional[str] = None, hint_topic: str = "trading") -> Optional[dict]:
    return analyze_video_frames(video_path, hint_topic=hint_topic)

def generate_video_prompts(search_heading: str) -> dict:
    """
    Generates 3 different video prompts based on a single search heading.
    If OpenAI / OpenRouter key is missing, falls back to a mock response for testing.
    """
    client, model = get_ai_client()
    if not client:
        return {
            "instagram": f"A vertical, highly engaging cinematic video about {search_heading} optimized for Reels.",
            "tiktok": f"A fast-paced, trendy vertical video about {search_heading} with quick cuts.",
            "youtube": f"A detailed, high-quality landscape video exploring the topic of {search_heading}."
        }

    try:
        system_prompt = (
            "You are an expert social media content creator. Given a trending topic, generate 3 different visual prompts for an AI Video Generator (like Kling or Sora). "
            "1 for Instagram (aesthetic, vertical), 1 for TikTok (trendy, fast-paced, vertical), and 1 for YouTube (detailed, cinematic, horizontal). "
            "Return ONLY a JSON object with keys: 'instagram', 'tiktok', 'youtube' containing the prompts."
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": search_heading}
            ],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"AI Prompt Error: {e}")
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

def rephrase_with_ai(title: str, topic: str = "", uploader: str = "") -> Optional[dict]:
    """
    Intelligently rewrites and rephrases any video title stating the exact same topic
    in a fresh, punchy, viral, and 100% complete way using the AI model.
    """
    client, model = get_ai_client()
    if not client:
        return None

    try:
        prompt = (
            f"You are an elite viral social media copywriter for YouTube Shorts, TikTok, and Instagram Reels.\n"
            f"Original Video Title: \"{title}\".\n"
            f"Topic: {topic or 'general'}. Channel/Creator: {uploader or 'creator'}.\n\n"
            "TASK: Rephrase and rewrite the title stating the EXACT SAME core topic/message, but in a fresh, punchy, viral, and complete way.\n\n"
            "CRITICAL RULES:\n"
            "1. 'title': Must be a 100% COMPLETE sentence or phrase (between 40 and 65 characters) with 1 fitting emoji at the end.\n"
            "   - NEVER cut off words. NEVER use ellipses like 'Rig...'.\n"
            "   - NEVER use lazy prefix wrappers like 'The Real Truth Behind [entire original sentence]'.\n"
            "   - It must state the same topic/hook as the original, but rewritten to maximize curiosity and clicks.\n"
            "2. 'description': An engaging 2-sentence description summarizing the insights, followed by 6-8 relevant hashtags.\n"
            "3. 'caption': A high-converting Instagram caption with a strong hook, 3 bulleted takeaways/observations, an engaging question prompting comments, and 12-15 targeted hashtags.\n\n"
            "Return ONLY a valid JSON object with keys: 'title', 'description', 'caption'."
        )

        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        data = json.loads(resp.choices[0].message.content)
        if "title" in data and "description" in data and "caption" in data:
            data["analyzed_from"] = "ai_rephrase"
            return data
    except Exception as e:
        print(f"AI Rephrase Error: {e}")

    return None

def generate_viral_copy(
    title: str,
    topic: str = "",
    original_desc: str = "",
    uploader: str = "",
    video_path: Optional[str] = None
) -> dict:
    """
    Context-aware viral copy generator.
    1. If video_path is provided and exists on disk, runs Multimodal AI Vision analysis to see inside the video.
    2. Rewrites titles intelligently using AI so they state the same topic in a catchy, 100% complete way.
    3. Purifies generic filenames, phone exports (WhatsApp Video, VID_, IMG_, timestamps), and Instagram CTAs.
    """
    # 1. Check if we have an actual video file on disk to inspect with Vision AI
    if video_path and os.path.exists(video_path):
        vision_result = analyze_video_frames(video_path, hint_topic=topic)
        if vision_result:
            return vision_result

    raw_title = (title or "").strip()
    t = raw_title

    # 2. Check if the title is a raw camera/phone/WhatsApp export
    is_generic_export = bool(GENERIC_CAMERA_PATTERN.search(t))

    # Strip leading & trailing emojis & decorative symbols
    t = re.sub(r'^[\U00010000-\U0010ffff\u2600-\u27ff\u200d\s\💭\👇\🔥\🚀\📈\💡\⚡\📊\✨\💗\🧿]+', '', t).strip()
    t = re.sub(r'[\U00010000-\U0010ffff\u2600-\u27ff\u200d\s\💭\👇\🔥\🚀\📈\💡\⚡\📊\✨\💗\🧿]+$', '', t).strip()

    # Normalize and clean uploaded filenames (e.g. SpikeSignals_CompletePicture_Real_35s.mp4)
    is_filename = '_' in t or t.endswith('.mp4') or re.search(r'\b\d+s\b', t, re.IGNORECASE)
    if is_filename:
        t = re.sub(r'\.(mp4|mov|avi|mkv)$', '', t, flags=re.IGNORECASE)
        t = re.sub(r'[\_\-]+(real|\d+s|final|v\d+|\d+p|cut|edit).*$', '', t, flags=re.IGNORECASE)
        t = t.replace('_', ' ')
        t = re.sub(r'([a-z])([A-Z])', r'\1 \2', t)
        t = t.strip()

    # 3. Detect and purify Instagram CTA captions
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

    # Clean channel tags and boilerplate suffixes
    if " | " in t:
        t = t.split(" | ")[0].strip()
    elif uploader and f" - {uploader}" in t:
        t = t.replace(f" - {uploader}", "").strip()
    
    clean_title = re.sub(r'\[(Official|Music Video|HD|4K|Shorts|202\d).*?\]', '', t, flags=re.IGNORECASE).strip()
    clean_title = re.sub(r'\((Official|Music Video|HD|4K|Shorts|202\d).*?\)', '', clean_title, flags=re.IGNORECASE).strip()

    # 4. IF TITLE IS GENERIC PHONE/APP EXPORT, OVERRIDE TO REAL HIGH-CONVERTING TOPIC
    combined_ctx = f"{clean_title} {topic}".lower()
    is_spikesignals = 'spikesignal' in combined_ctx.replace(' ', '') or 'spike signal' in combined_ctx

    if is_generic_export or not clean_title or len(clean_title) < 4:
        if is_spikesignals:
            clean_title = "SpikeSignals Algorithmic Market Indicators"
        elif any(k in combined_ctx for k in ['tech', 'ai', 'software', 'app', 'code']):
            clean_title = "Breakthrough AI & Next-Gen Technology Insights"
        else:
            clean_title = "High-Probability Market Setup & Trading Strategy"

    # 5. REPHRASE INTELLIGENTLY VIA AI MODEL (IF NOT SPECIAL COMPANY/CTA)
    if not is_spikesignals and not is_cta and not is_generic_export:
        ai_res = rephrase_with_ai(clean_title, topic=topic, uploader=uploader)
        if ai_res:
            return ai_res

    is_trading = is_spikesignals or is_cta or any(k in combined_ctx for k in ['trad', 'stock', 'invest', 'forex', 'crypto', 'wealth', 'market', 'filter', 'chart', 'profit'])
    is_tech = any(k in combined_ctx for k in ['ai', 'tech', 'software', 'app', 'code', 'future', 'robot'])

    # 5. GENERATE TITLE VARIATIONS (Similar, High-CTR, NEVER Raw/Identical, NEVER Generic WhatsApp)
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
    elif is_generic_export:
        if is_trading:
            title_candidates = [
                "The Exact Strategy Smart Traders Use Every Single Day 📈",
                "How To Spot High-Probability Entries Like A Pro ⚡",
                "The #1 Trading Rule Every Profitable Trader Follows 💡",
                "Mastering Price Action: The Ultimate Breakdown 🚀"
            ]
        elif is_tech:
            title_candidates = [
                "The Future Of Tech: Breakthrough Insights You Need To Know 🚀",
                "Inside The Next Big Shift In Artificial Intelligence 💡",
                "Why Everyone Is Watching This New Tech Revolution ⚡"
            ]
        else:
            title_candidates = [
                "Key Insights You Don't Want To Miss 💡",
                "The Real Truth Behind This Trend 📊",
                "Why Everyone Is Talking About This Setup 🚀"
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
        # Truncate strictly at word boundaries so words are never sliced mid-sentence
        words = chosen_title.split()
        shortened = []
        cur_len = 0
        for w in words:
            if cur_len + len(w) + 1 > 65:
                break
            shortened.append(w)
            cur_len += len(w) + 1
        chosen_title = " ".join(shortened)
        if not re.search(r'[\U00010000-\U0010ffff\u2600-\u27ff]$', chosen_title):
            chosen_title += " 🚀"

    # 6. EXTRACT KEYWORDS & HASHTAGS (Banning phone export junk)
    words = re.findall(r'[a-zA-Z]{3,}', f"{clean_title} {topic}".lower())
    stop_words = {
        'the', 'and', 'for', 'that', 'this', 'with', 'from', 'have', 'only', 'ran', 
        'through', 'video', 'watch', 'are', 'was', 'were', 'will', 'you', 'your', 'about',
        'what', 'when', 'where', 'which', 'who', 'how', 'why', 'can', 'could', 'drop', 'start', 'send',
        'whatsapp', 'whats', 'app', 'video', 'videos', 'vid', 'img', 'pxl', 'screen', 'recording',
        'untitled', 'temp', 'camera', 'file', 'clip', 'cut', 'edit', 'real', 'final'
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
    elif is_generic_export and is_trading:
        description = (
            "A deep dive breakdown into high-probability market structure and disciplined execution. "
            "Discover key levels, entry triggers, and capital protection rules to trade with confidence.\n\n"
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
            f"Comprehensive breakdown on {clean_title}. Exploring key lessons, industry shifts, "
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
    elif is_generic_export and is_trading:
        caption = (
            "What is your #1 rule when trading volatile markets? 👀👇\n\n"
            "💡 Key Trading Principles from this breakdown:\n"
            "• Wait for clear confirmation at key price levels\n"
            "• Protect your capital first—profits follow discipline\n"
            "• Never chase extended moves without a defined risk setup\n\n"
            "💬 Drop a comment below with your trading plan for this week!\n"
            "📌 Bookmark & save this reel for your trading journal.\n\n"
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
