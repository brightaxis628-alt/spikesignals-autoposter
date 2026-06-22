from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import os
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

from services.video_editor import add_logo
from services.zernio_service import publish_video as zernio_publish_video
from services.youtube_service import upload_video as native_youtube_upload

app = FastAPI()

os.makedirs("uploads", exist_ok=True)
os.makedirs("output", exist_ok=True)
os.makedirs("logos", exist_ok=True)

# Mount the output directory so we can serve videos statically for Ngrok/TikTok/Instagram
app.mount("/output", StaticFiles(directory="output"), name="output")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def home():
    return FileResponse("static/index.html")

@app.get("/trending-videos")
def trending_videos():
    return {"status": "success", "message": "Zernio handles trending natively or we fetch from elsewhere later."}

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

class PublishRequest(BaseModel):
    video_filename: str
    title: str
    description: str
    caption: str
    public_base_url: str = "" # Provide ngrok URL if not using AWS S3
    platforms: List[str] = ["instagram", "tiktok", "youtube"]

@app.post("/publish-all")
async def publish_all(data: PublishRequest, request: Request):
    try:
        edited_video_path = f"output/{data.video_filename}"
        
        if not os.path.exists(edited_video_path):
            return {"status": "error", "message": f"File {edited_video_path} not found. Please process the video first."}

        # Determine Public URL for Zernio to fetch media
        base_url = data.public_base_url.rstrip('/') if data.public_base_url else str(request.base_url).rstrip('/')
        encoded_filename = urllib.parse.quote(data.video_filename)
        public_video_url = f"{base_url}/output/{encoded_filename}"

        results = {}

        # 1. Instagram Upload via Zernio
        if "instagram" in data.platforms:
            try:
                ig_res = zernio_publish_video(public_video_url, data.caption, "instagram")
                results["instagram"] = {"status": "success", "result": "Published via Zernio"}
            except Exception as e:
                results["instagram"] = {"status": "error", "message": str(e)}

        # 2. TikTok Upload via Zernio
        if "tiktok" in data.platforms:
            try:
                tk_res = zernio_publish_video(public_video_url, f"{data.title}\n{data.description}", "tiktok")
                results["tiktok"] = {"status": "success", "result": "Published via Zernio"}
            except Exception as e:
                results["tiktok"] = {"status": "error", "message": str(e)}

        # 3. YouTube Upload natively via google-api-python-client
        if "youtube" in data.platforms:
            try:
                # We need the local file path for native upload
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
