import os
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


def generate_viral_copy(title: str, topic: str = "") -> dict:
    """
    Auto-generates catchy title, hashtag-rich description, and Instagram caption.
    Uses OpenAI GPT-4o if key is present, with smart algorithmic niche copywriting fallback.
    Never copy-pastes raw scraping metadata or foreign store codes.
    """
    if OPENAI_API_KEY and OPENAI_API_KEY != "":
        try:
            from openai import OpenAI
            import json
            client = OpenAI(api_key=OPENAI_API_KEY)
            system_prompt = (
                "You are an elite viral social media copywriter. Given a video topic/title, create fresh, original brand content in English:\n"
                "1. 'title': High-CTR, curiosity-driven viral headline under 65 chars (with relevant emoji).\n"
                "2. 'description': Engaging 2-3 sentence overview for YouTube Shorts/TikTok + 6-8 trending hashtags.\n"
                "3. 'caption': Attention-grabbing Instagram hook, engagement question, call to action, and 15 niche hashtags.\n"
                "Do NOT just copy foreign words or store codes. Return ONLY valid JSON with keys 'title', 'description', 'caption'."
            )
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Topic: {topic}\nOriginal Video Context: {title}"}
                ],
                response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content)
            return {
                "title": data.get("title", "Must-Watch Viral Insight 🔥"),
                "description": data.get("description", ""),
                "caption": data.get("caption", "")
            }
        except Exception as e:
            print(f"OpenAI copy generation error: {e}")

    # --- ADVANCED NICHE-AWARE COPYWRITING ENGINE ---
    combined_ctx = f"{topic} {title}".lower()

    is_finance = any(w in combined_ctx for w in ["trad", "stock", "invest", "crypto", "forex", "market", "wealth", "fund", "money", "bull", "bear"])
    is_shopping = any(w in combined_ctx for w in ["shop", "deal", "haul", "bim", "discount", "sale", "store", "price", "buy", "save", "offer"])
    is_fitness = any(w in combined_ctx for w in ["gym", "fit", "workout", "muscle", "train", "health", "exercise", "diet", "lift"])
    is_tech = any(w in combined_ctx for w in ["ai", "tech", "code", "future", "app", "software", "robot", "cyber"])

    if is_finance:
        titles = [
            "The 1 Trading Rule Top Investors Never Break 📈",
            "Mastering The Market: Essential Strategy Revealed 💡",
            "Why 90% Of Traders Struggle (And How To Win) 🚀",
            "Key Market Breakdown You Can't Afford To Miss 📊"
        ]
        descriptions = [
            "Consistency, patience, and risk management separate winning traders from the crowd. Study the setup and stay disciplined with your strategy.\n\n#trading #stocks #investing #forextrading #wealthmindset #cryptocurrency #financialfreedom #finance",
            "Every major market move leaves clues. Here's a key principle for building a high-probability trading routine.\n\n#daytrading #stockmarket #crypto #investingforbeginners #forexsignals #marketanalysis #wealth"
        ]
        captions = [
            "Drop a 🚀 if you're building your portfolio this year!\n\nSuccess in trading isn't about guessing—it's about discipline when emotions run high.\n\n💬 What's your #1 trading rule? Let us know below!\n📌 Save this post for your next trading session.\n\n#stockmarket #daytrader #forexsignals #tradingtips #investor #financialgoals #traderlife #wealth #investing",
            "Tag a fellow trader who needs to see this! 📊\n\nProtect your capital first, let the profits follow. Consistency is everything.\n\n👇 Drop your favorite ticker in the comments!\n📌 Bookmark for market open.\n\n#tradingstrategy #marketmindset #forexlife #stockstowatch #cryptotrading #wealthbuilding"
        ]
    elif is_shopping:
        titles = [
            "Insane Store Deals You Won't Believe! 🛒🔥",
            "Secret Shopping Hack That Saves You Serious Cash! ✨",
            "Best Bargain Finds Of The Week: Don't Miss Out! 🛍️",
            "Everyone Is Rushing To Grab This Deal! 💥"
        ]
        descriptions = [
            "Unbeatable store deals and budget finds that give you the most value for your money. Check out these must-grab items before they sell out!\n\n#shoppinghacks #budgetshopping #groceryhaul #bargainhunter #smartshopper #dealsandsteals #savings",
            "Why pay full price when you can snag steals like this? Share with a friend who loves saving money on everyday essentials!\n\n#bargainfinds #deals #smartshopper #groceryshopping #discounts #savemoney #haul"
        ]
        captions = [
            "Would you grab this deal? 👀 Drop your thoughts below! 👇\n\nTag a friend who loves finding secret bargains! 🛍️💥\n\n📌 Save this reel so you don't forget next time you go shopping!\n\n#deals #shoppinghaul #smartshopper #budgetfriendly #viraldeals #bargainfinds #instashopping #savemoney",
            "Deal alert! 🚨 Is this the best find of the week?\n\nDouble tap if you love smart shopping hacks! Comment which item you'd pick up first 👇🛒\n\n#dealsandsteals #bargainhunt #grocerysavings #smartspending #viralreels #shophacks"
        ]
    elif is_fitness:
        titles = [
            "Game-Changing Fitness Form Hack You Need! 💪🔥",
            "Stop Making This Workout Mistake Right Now 🏋️",
            "The Secret To Faster Muscle Recovery Revealed ✨",
            "Transform Your Routine With This 1 Adjustment 🚀"
        ]
        descriptions = [
            "Level up your training with proper technique, progressive overload, and consistent daily habits. No shortcuts, just smart work!\n\n#fitness #gymmotivation #workouttips #fitfam #musclebuilding #strengthtraining #healthylifestyle",
            "Small form corrections lead to massive strength gains and injury prevention. Give this a shot on your next session!\n\n#gymlife #workoutroutine #fitnessgoals #bodybuilding #trainingtips #fitinspiration"
        ]
        captions = [
            "Are you trying this on your next workout? Drop a 💪 below!\n\nConsistency inside and outside the gym is what brings real progress.\n\n📌 Save this reel for leg/push day!\n👥 Share with your gym partner!\n\n#fitnesstips #gymroutine #workoutmotivation #gains #fitnessjourney #trainhard #fitlifestyle",
            "Save this for your next gym session! 📌\n\nFocus on form before heavy weight. Your future self will thank you.\n\n💬 Drop your current fitness goal in the comments!\n\n#workoutgoals #fitnesscoach #strengthandconditioning #fitlife #dailygym"
        ]
    elif is_tech:
        titles = [
            "Mind-Blowing Tech Innovation You Must See! 🤖🔥",
            "The AI Tool Changing Everything In 2026 💡",
            "Wait Till You See What Technology Can Do Now! 🚀",
            "Is This The Future? Game-Changing Tech Reveal ✨"
        ]
        descriptions = [
            "The pace of innovation is accelerating faster than ever. Here's a breakthrough technology redefining what's possible.\n\n#tech #artificialintelligence #futuretech #innovation #technews #gadgets #digitaltransformation",
            "From automation to smart tools, modern tech is transforming everyday workflows. What are your thoughts on this?\n\n#technology #aitools #futureisnow #techtrends #software #smarttech"
        ]
        captions = [
            "Would you use this in your daily life? 👀 Drop your thoughts below!\n\nDouble tap if tech innovation excites you! Share with a tech lover 🚀\n\n📌 Save this reel for the latest tech updates!\n\n#techupdates #airevolution #futuretech #technews #smarttools #gadgetlover #techcommunity",
            "The future is happening right in front of us! 🤖⚡\n\nWhat do you think is next for this technology? Let's discuss in the comments 👇\n\n#innovations #techrevolution #digitalfuture #smarttechnology #techtalk"
        ]
    else:
        titles = [
            "You Need To See This: Viral Moment! 🔥",
            "Wait Till The Very End... Completely Unbelievable! 😱",
            "The Life Hack Everyone Is Talking About ✨",
            "This Changes Everything: Must-Watch! 💡"
        ]
        descriptions = [
            "An unforgettable trending moment that you have to watch twice! Follow along for the freshest viral clips and daily highlights.\n\n#viral #trending #mustwatch #fyp #explorepage #dailyvideo #shorts #trendingnow",
            "Trending highlights and top viral moments making waves across social media today. Check this out!\n\n#virals #trendalert #explore #entertainment #topvideo #reelsviral #popular"
        ]
        captions = [
            "Rate this from 1 to 10 in the comments! 👇🔥\n\nDouble tap if this caught you by surprise! Tag someone who needs to see this! 🤯\n\n📌 Save this reel for later!\n\n#viralreels #reelsinstagram #explore #trendingvideo #fyp #instadaily #viralcontent #mustsee",
            "Did not see that coming! 😱 Drop your reaction below!\n\nFollow for more viral trends every day! ✨\n📌 Bookmark to share with friends!\n\n#trendingreels #viralvideos #entertainment #dailytrend #explorepage #fypage"
        ]

    return {
        "title": random.choice(titles),
        "description": random.choice(descriptions),
        "caption": random.choice(captions)
    }
