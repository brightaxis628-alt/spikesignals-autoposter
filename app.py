from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import shutil
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

from services.video_editor import add_logo
from services.downloader_service import download_video_from_url, search_trending_videos
from services.zernio_service import publish_video as zernio_publish_video
from services.youtube_service import upload_video as native_youtube_upload
from services.ai_generator_service import generate_video_prompts, generate_kling_video, generate_viral_copy

app = FastAPI(title="SpikeSignals Video Autoposter & Downloader")

os.makedirs("uploads", exist_ok=True)
os.makedirs("output", exist_ok=True)
os.makedirs("logos", exist_ok=True)

# Mount the output directory so we can serve videos statically for Ngrok/TikTok/Instagram/Render
app.mount("/output", StaticFiles(directory="output"), name="output")
app.mount("/static", StaticFiles(directory="static"), name="static")

def get_effective_base_url(custom_url: str = "", request: Request = None) -> str:
    """
    Automatically resolves the public URL of this server:
    1. Explicit custom URL if provided.
    2. RENDER_EXTERNAL_URL (Render automatically injects this on live deployments).
    3. PUBLIC_BASE_URL from .env if defined.
    4. request.base_url from the active incoming browser request.
    """
    if custom_url and custom_url.strip():
        return custom_url.strip().rstrip('/')
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    if render_url:
        return render_url.rstrip('/')
    env_public = os.getenv("PUBLIC_BASE_URL")
    if env_public:
        return env_public.rstrip('/')
    if request:
        return str(request.base_url).rstrip('/')
    return "http://localhost:55570"

@app.get("/")
def home():
    return FileResponse("static/index.html")

@app.get("/health")
def health_check():
    """Health check endpoint for Render and UptimeRobot heartbeat pings"""
    return {
        "status": "online",
        "service": "SpikeSignals Video Autoposter & Downloader",
        "version": "2.0.0"
    }

@app.get("/trending-videos")
def trending_videos():
    return {"status": "success", "message": "Zernio handles trending natively or we fetch from elsewhere later."}

@app.get("/search-trending")
def search_trending(query: str = "", platform: str = "youtube", max_results: int = 6):
    """
    Searches trending/viral videos matching given keywords or topic across YouTube, Instagram, or TikTok.
    Returns thumbnails, titles, duration, platform tags, and URLs for the user to pick from.
    """
    try:
        videos = search_trending_videos(keyword=query, platform=platform, max_results=max_results)
        return {"status": "success", "count": len(videos), "platform": platform, "videos": videos}
    except Exception as e:
        return {"status": "error", "message": str(e), "videos": []}

class CopyRequest(BaseModel):
    title: str
    topic: Optional[str] = ""

@app.post("/auto-make-copy")
def auto_make_copy(data: CopyRequest):
    """
    Automated copy generator: Takes the selected video title and context,
    and automatically crafts catchy viral headlines, description with hashtags, and IG caption.
    """
    try:
        copy_data = generate_viral_copy(data.title, data.topic)
        return {"status": "success", "data": copy_data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/process-video")
async def process_video(file: UploadFile = File(...)):
    input_path = f"uploads/{file.filename}"
    with open(input_path, "wb") as f:
        f.write(await file.read())

    output_filename = f"edited_{file.filename}"
    output_path = f"output/{output_filename}"
    logo_path = "logos/logo.png"

    if not os.path.exists(logo_path):
        return {"status": "error", "message": "Please place a logo.png inside the logos/ directory first!"}

    add_logo(input_path, logo_path, output_path)

    return {"status": "success", "output_file": output_filename}

class FetchVideoRequest(BaseModel):
    url: str
    direct_url: Optional[str] = None
    add_watermark: bool = True

@app.post("/fetch-video")
async def fetch_video(data: FetchVideoRequest):
    """
    Downloads a video from TikTok, Instagram, YouTube, or direct link,
    adds top-left logo, and makes it ready for publishing.
    """
    try:
        download_info = download_video_from_url(data.url, direct_url=data.direct_url)
        input_path = download_info["local_path"]
        
        output_filename = f"edited_{download_info['filename']}"
        output_path = f"output/{output_filename}"
        logo_path = "logos/logo.png"

        if data.add_watermark:
            if not os.path.exists(logo_path):
                return {"status": "error", "message": "Please place a logo.png inside the logos/ directory first!"}
            add_logo(input_path, logo_path, output_path)
            processed_file = output_filename
        else:
            shutil.copy(input_path, output_path)
            processed_file = output_filename

        return {
            "status": "success",
            "output_file": processed_file,
            "title": download_info.get("title", ""),
            "description": download_info.get("description", ""),
            "uploader": download_info.get("uploader", ""),
            "thumbnail": download_info.get("thumbnail", ""),
            "duration": download_info.get("duration", 0)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

class FetchAndPublishRequest(BaseModel):
    url: str
    direct_url: Optional[str] = None
    title: Optional[str] = ""
    description: Optional[str] = ""
    caption: Optional[str] = ""
    public_base_url: str = ""
    platforms: List[str] = ["instagram", "tiktok", "youtube"]

@app.post("/fetch-and-publish")
async def fetch_and_publish(data: FetchAndPublishRequest, request: Request):
    """
    One-click workflow: Fetches/downloads video, places top-left logo,
    and publishes directly to TikTok, Instagram, and YouTube.
    """
    try:
        # Step 1: Download video via direct stream or yt-dlp
        download_info = download_video_from_url(data.url, direct_url=data.direct_url)
        input_path = download_info["local_path"]
        
        # Step 2: Add logo
        output_filename = f"edited_{download_info['filename']}"
        output_path = f"output/{output_filename}"
        logo_path = "logos/logo.png"
        
        if os.path.exists(logo_path):
            add_logo(input_path, logo_path, output_path)
        else:
            shutil.copy(input_path, output_path)

        # Step 3: Metadata
        title = data.title.strip() if data.title else download_info.get("title", "Trending Video")
        description = data.description.strip() if data.description else download_info.get("description", "")
        caption = data.caption.strip() if data.caption else f"{title}\n\n{description}"
        
        # Determine Public URL automatically (works seamlessly on Render without typing links)
        base_url = get_effective_base_url(data.public_base_url, request)
        encoded_filename = urllib.parse.quote(output_filename)
        public_video_url = f"{base_url}/output/{encoded_filename}"

        results = {}

        # 1. Instagram Upload via Zernio
        if "instagram" in data.platforms:
            try:
                zernio_publish_video(public_video_url, caption, "instagram")
                results["instagram"] = {"status": "success", "result": "Published via Zernio"}
            except Exception as e:
                results["instagram"] = {"status": "error", "message": str(e)}

        # 2. TikTok Upload via Zernio
        if "tiktok" in data.platforms:
            try:
                zernio_publish_video(public_video_url, f"{title}\n{description}", "tiktok")
                results["tiktok"] = {"status": "success", "result": "Published via Zernio"}
            except Exception as e:
                results["tiktok"] = {"status": "error", "message": str(e)}

        # 3. YouTube Upload natively via google-api-python-client
        if "youtube" in data.platforms:
            try:
                yt_res = native_youtube_upload(output_path, title, description)
                results["youtube"] = {"status": "success", "result": f"Published natively. Video ID: {yt_res}"}
            except Exception as e:
                results["youtube"] = {"status": "error", "message": str(e)}

        return {
            "status": "success",
            "video_title": title,
            "output_file": output_filename,
            "public_video_url_used": public_video_url,
            "results": results
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

class PublishRequest(BaseModel):
    video_filename: str
    title: str
    description: str
    caption: str
    public_base_url: str = "" # Provide ngrok URL or Render URL
    platforms: List[str] = ["instagram", "tiktok", "youtube"]

class AIGenerationRequest(BaseModel):
    search_heading: str
    public_base_url: str = ""
    platforms: List[str] = ["instagram", "tiktok", "youtube"]

@app.post("/generate-ai-media")
async def generate_ai_media(data: AIGenerationRequest, request: Request):
    try:
        prompts = generate_video_prompts(data.search_heading)
        results = {}
        
        for platform in data.platforms:
            if platform not in prompts:
                continue
                
            prompt = prompts[platform]
            
            # Step A: Generate Video via Kling 3.0
            raw_video_filename = generate_kling_video(prompt, platform)
            
            # Step B: Add Logo
            input_path = f"output/{raw_video_filename}"
            final_filename = f"final_{raw_video_filename}"
            output_path = f"output/{final_filename}"
            logo_path = "logos/logo.png"
            
            add_logo(input_path, logo_path, output_path)
            
            # Step C: Publish
            base_url = data.public_base_url.strip().rstrip('/') if data.public_base_url else str(request.base_url).rstrip('/')
            encoded_filename = urllib.parse.quote(final_filename)
            public_video_url = f"{base_url}/output/{encoded_filename}"
            
            if platform == "instagram":
                try:
                    zernio_publish_video(public_video_url, f"Generated by AI: {prompt}", "instagram")
                    results["instagram"] = {"status": "success", "result": "Published AI video via Zernio"}
                except Exception as e:
                    results["instagram"] = {"status": "error", "message": str(e)}
                    
            elif platform == "tiktok":
                try:
                    zernio_publish_video(public_video_url, f"{data.search_heading}\n{prompt}", "tiktok")
                    results["tiktok"] = {"status": "success", "result": "Published AI video via Zernio"}
                except Exception as e:
                    results["tiktok"] = {"status": "error", "message": str(e)}
                    
            elif platform == "youtube":
                try:
                    yt_res = native_youtube_upload(output_path, data.search_heading, prompt)
                    results["youtube"] = {"status": "success", "result": f"Published natively. Video ID: {yt_res}"}
                except Exception as e:
                    results["youtube"] = {"status": "error", "message": str(e)}
                    
        return {
            "status": "success",
            "search_heading": data.search_heading,
            "prompts_used": prompts,
            "results": results
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/publish-all")
async def publish_all(data: PublishRequest, request: Request):
    try:
        edited_video_path = f"output/{data.video_filename}"
        
        if not os.path.exists(edited_video_path):
            return {"status": "error", "message": f"File {edited_video_path} not found. Please process the video first."}

        # Determine Public URL for Zernio to fetch media automatically
        base_url = get_effective_base_url(data.public_base_url, request)
        encoded_filename = urllib.parse.quote(data.video_filename)
        public_video_url = f"{base_url}/output/{encoded_filename}"

        results = {}

        # 1. Instagram Upload via Zernio
        if "instagram" in data.platforms:
            try:
                zernio_publish_video(public_video_url, data.caption, "instagram")
                results["instagram"] = {"status": "success", "result": "Published via Zernio"}
            except Exception as e:
                results["instagram"] = {"status": "error", "message": str(e)}

        # 2. TikTok Upload via Zernio
        if "tiktok" in data.platforms:
            try:
                zernio_publish_video(public_video_url, f"{data.title}\n{data.description}", "tiktok")
                results["tiktok"] = {"status": "success", "result": "Published via Zernio"}
            except Exception as e:
                results["tiktok"] = {"status": "error", "message": str(e)}

        # 3. YouTube Upload natively via google-api-python-client
        if "youtube" in data.platforms:
            try:
                yt_res = native_youtube_upload(edited_video_path, data.title, data.description)
                results["youtube"] = {"status": "success", "result": f"Published natively. Video ID: {yt_res}"}
            except Exception as e:
                results["youtube"] = {"status": "error", "message": str(e)}

        return {
            "status": "success",
            "public_video_url_used": public_video_url,
            "results": results
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
