import os
import re
import json
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests
import yt_dlp
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

CACHE_FILE = Path(__file__).resolve().parent.parent / "search_cache.json"

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "27f16c30e1mshae916aae3b8eaf5p1cb2e4jsn956f1c20a6a6")
RAPIDAPI_INSTA_HOST = os.getenv("RAPIDAPI_INSTA_HOST", "instagram-best-scraper-data-extractor-api.p.rapidapi.com")
RAPIDAPI_TIKTOK_HOST = os.getenv("RAPIDAPI_TIKTOK_HOST", "scraptik.p.rapidapi.com")


# ---------------- CACHING HELPERS ----------------
def _cache_get(key: str) -> Optional[List[Dict[str, Any]]]:
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get(key)
    except Exception as e:
        logger.warning(f"Cache read error: {e}")
        return None

def _cache_set(key: str, value: List[Dict[str, Any]]) -> None:
    try:
        data = {}
        if CACHE_FILE.exists():
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        data[key] = value
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Cache write error: {e}")


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", name)[:60].strip()


def _slice_batch(items: List[Dict[str, Any]], max_results: int = 6, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Slices items by offset to support rotating batches of fresh videos on each click.
    """
    total = len(items)
    if total == 0:
        return []
    actual_offset = offset % total
    batch = items[actual_offset : actual_offset + max_results]
    if len(batch) < max_results and total > len(batch):
        batch.extend(items[: max_results - len(batch)])
    return batch[:max_results]


# ---------------- PLATFORM-SPECIFIC SEARCHERS ----------------

def _search_tiktok_rapidapi(keyword: str, max_results: int = 6, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Searches TikTok videos by keyword using RapidAPI ScrapTik.
    Checks search_cache.json first to conserve quota and supports offset batching.
    """
    keyword_clean = keyword.strip()
    if not keyword_clean:
        return []

    cache_key = f"tiktok::{keyword_clean.lower()}"
    cached = _cache_get(cache_key)
    if cached:
        print(f"[CACHE HIT] TikTok keyword: {keyword_clean} (offset {offset})")
        return _slice_batch(cached, max_results, offset)

    if not RAPIDAPI_KEY:
        print("[TIKTOK] No RAPIDAPI_KEY configured.")
        return []

    try:
        print(f"[TIKTOK] Querying RapidAPI ScrapTik for: {keyword_clean}")
        url = f"https://{RAPIDAPI_TIKTOK_HOST}/search-posts"
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": RAPIDAPI_TIKTOK_HOST
        }
        params = {"keyword": keyword_clean, "count": "20", "offset": "0"}
        res = requests.get(url, headers=headers, params=params, timeout=40)

        if res.status_code == 200:
            data = res.json()
            results = []
            for it in data.get("search_item_list") or []:
                a = it.get("aweme_info") or {}
                if not a.get("aweme_id"):
                    continue

                author = a.get("author") or {}
                video = a.get("video") or {}
                stats = a.get("statistics") or {}
                username = author.get("unique_id") or author.get("nickname") or "tiktok"
                covers = (video.get("cover") or {}).get("url_list") or []
                dur_ms = video.get("duration") or 0

                direct = None
                for k in ("download_no_watermark_addr", "play_addr_h264", "play_addr", "download_addr"):
                    ul = (video.get(k) or {}).get("url_list") or []
                    if ul:
                        direct = ul[0]
                        break

                desc = (a.get("desc") or "TikTok Video").strip().split("\n")[0][:80]
                results.append({
                    "id": str(a["aweme_id"]),
                    "platform": "tiktok",
                    "title": desc or "TikTok Video",
                    "url": f"https://www.tiktok.com/@{username}/video/{a['aweme_id']}",
                    "direct_video_url": direct,
                    "thumbnail": covers[0] if covers else "",
                    "duration": round(dur_ms / 1000) if dur_ms else 0,
                    "uploader": author.get("nickname") or username or "TikTok Creator",
                    "view_count": stats.get("play_count", 0)
                })

            if results:
                _cache_set(cache_key, results)
            return _slice_batch(results, max_results, offset)
        else:
            print(f"[TIKTOK API ERROR] HTTP {res.status_code}: {res.text[:120]}")
    except Exception as e:
        print(f"[TIKTOK API EXCEPTION] {e}")

    return []


def _search_instagram_rapidapi(keyword: str, max_results: int = 6, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Searches Instagram Reels by hashtag using RapidAPI 'Instagram Best Scraper'.
    Converts keyword to clean hashtag candidates (e.g. trade -> trading, stocks).
    Checks cache first to save quota, guarantee ultra-fast response, and rotate batches.
    """
    raw_tag = re.sub(r"[^\w]", "", keyword.strip().lower().lstrip("#"))
    if not raw_tag or raw_tag in ("trade", "trader", "trades", "trading"):
        raw_tag = "trading"
    elif raw_tag in ("stock", "stocks", "market", "markets", "share"):
        raw_tag = "stocks"
    elif raw_tag in ("crypto", "cryptos", "bitcoin", "btc"):
        raw_tag = "crypto"

    cache_key = f"instagram::{raw_tag}"
    cached = _cache_get(cache_key)
    if cached:
        print(f"[CACHE HIT] Instagram hashtag: #{raw_tag} (offset {offset})")
        return _slice_batch(cached, max_results, offset)

    # Check related high-affinity cache keys
    fallback_cache = _cache_get("instagram::trading") or _cache_get("instagram::market")

    if not RAPIDAPI_KEY:
        print("[INSTAGRAM] No RAPIDAPI_KEY configured; using verified Instagram cache.")
        return _slice_batch(fallback_cache, max_results, offset) if fallback_cache else []

    candidates = [raw_tag]
    if raw_tag.endswith("e"):
        candidates.append(raw_tag[:-1] + "ing")
    elif not raw_tag.endswith("ing"):
        candidates.append(raw_tag + "ing")
    candidates.append(f"{raw_tag}reels")
    candidates.append(f"{raw_tag}s")
    candidates.append("trading")

    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_INSTA_HOST,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }

    for tag in candidates:
        try:
            print(f"[INSTAGRAM] Querying RapidAPI Instagram Best Scraper for: #{tag}")
            url = f"https://{RAPIDAPI_INSTA_HOST}/main/hashtags/{tag}/top"
            res = requests.get(url, headers=headers, timeout=15)

            if res.status_code == 200 and res.text.strip():
                try:
                    data = res.json()
                except Exception:
                    continue

                posts = data.get("data") or []
                results = []
                for p in posts:
                    vids = [m for m in (p.get("media") or []) if m.get("kind") == "video"]
                    if not vids:
                        continue

                    caption = (p.get("caption") or "").strip()
                    first_line = caption.split("\n")[0][:80]
                    code = p.get("shortcode") or str(p.get("id", ""))
                    views = (p.get("counts") or {}).get("views") or 0
                    owner = (p.get("owner") or {}).get("username") or "Instagram"

                    results.append({
                        "id": str(p.get("id") or code),
                        "platform": "instagram",
                        "title": first_line or f"Instagram Reel #{code}",
                        "url": f"https://www.instagram.com/reel/{code}/",
                        "direct_video_url": vids[0].get("url"),
                        "thumbnail": vids[0].get("thumbnail_url") or "",
                        "duration": vids[0].get("duration_s") or 0,
                        "uploader": owner,
                        "view_count": views
                    })

                if results:
                    _cache_set(cache_key, results)
                    if tag != raw_tag:
                        _cache_set(f"instagram::{tag}", results)
                    return _slice_batch(results, max_results, offset)
        except Exception as e:
            print(f"[INSTAGRAM API EXCEPTION for #{tag}] {e}")
            continue

    # Fallback to verified Instagram cache so user ALWAYS sees Instagram reels on Instagram tab
    if fallback_cache:
        print("[INSTAGRAM] Using verified Instagram cache fallback.")
        return _slice_batch(fallback_cache, max_results, offset)

    return []


def _search_youtube(keyword: str, max_results: int = 6, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Searches YouTube for BOTH Short (<95s) and Long-form (>95s) content.
    Interleaves short-form clips and full-length videos for a complete discovery experience.
    Supports offset batching so every click returns fresh videos.
    """
    kw = (keyword or "").strip()
    cache_key = f"youtube::{kw.lower()}"
    cached = _cache_get(cache_key)
    if cached:
        print(f"[CACHE HIT] YouTube keyword: {kw} (offset {offset})")
        return _slice_batch(cached, max_results, offset)

    kw_gen = f"ytsearch15:{kw}" if kw else "ytsearch15:trending viral videos"
    kw_shorts = f"ytsearch15:{kw} #shorts" if kw else "ytsearch15:trending #shorts"

    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
        'no_warnings': True
    }

    long_list = []
    short_list = []
    seen_ids = set()

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # 1. Fetch general & long-form YouTube videos
        try:
            r_gen = ydl.extract_info(kw_gen, download=False) or {}
            for e in (r_gen.get('entries') or []):
                if not e:
                    continue
                vid = str(e.get('id', ''))
                if not vid or vid in seen_ids:
                    continue
                seen_ids.add(vid)
                dur = e.get('duration') or 0
                thumb = e.get('thumbnail')
                if not thumb and e.get('thumbnails'):
                    thumb = e['thumbnails'][-1].get('url')
                if not thumb:
                    thumb = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"

                long_list.append({
                    "id": vid,
                    "platform": "youtube",
                    "title": e.get('title', 'Trending Video'),
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "direct_video_url": None,
                    "thumbnail": thumb,
                    "duration": dur,
                    "uploader": e.get('uploader') or e.get('channel') or "YouTube Creator",
                    "view_count": e.get('view_count', 0),
                    "content_type": "Short" if (dur and dur <= 95) else "Video"
                })
        except Exception as e:
            print(f"Error searching general YouTube videos: {e}")

        # 2. Fetch viral YouTube Shorts
        try:
            r_short = ydl.extract_info(kw_shorts, download=False) or {}
            for e in (r_short.get('entries') or []):
                if not e:
                    continue
                vid = str(e.get('id', ''))
                if not vid or vid in seen_ids:
                    continue
                seen_ids.add(vid)
                dur = e.get('duration') or 0
                thumb = e.get('thumbnail')
                if not thumb and e.get('thumbnails'):
                    thumb = e['thumbnails'][-1].get('url')
                if not thumb:
                    thumb = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"

                short_list.append({
                    "id": vid,
                    "platform": "youtube",
                    "title": e.get('title', 'Trending Short'),
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "direct_video_url": None,
                    "thumbnail": thumb,
                    "duration": dur,
                    "uploader": e.get('uploader') or e.get('channel') or "YouTube Creator",
                    "view_count": e.get('view_count', 0),
                    "content_type": "Short"
                })
        except Exception as e:
            print(f"Error searching YouTube shorts: {e}")

    # Interleave: 1 short, 1 long for a balanced mix
    results = []
    s_i, l_i = 0, 0
    while s_i < len(short_list) or l_i < len(long_list):
        if s_i < len(short_list):
            results.append(short_list[s_i])
            s_i += 1
        if l_i < len(long_list):
            results.append(long_list[l_i])
            l_i += 1

    if results:
        _cache_set(cache_key, results)
    return _slice_batch(results, max_results, offset)


# ---------------- MAIN SEARCH FUNCTION ----------------

def search_trending_videos(keyword: str = "", platform: str = "youtube", max_results: int = 6, offset: int = 0) -> list:
    """
    Searches for trending videos matching keyword tailored for the chosen platform.
    Supports offset batching so every click returns fresh videos.
    - TikTok: ScrapTik RapidAPI (cached) with direct CDN mp4
    - Instagram: Instagram Best Scraper RapidAPI (cached) with direct CDN mp4
    - YouTube: Both Shorts & Long videos interleaved via yt-dlp
    """
    keyword = (keyword or "").strip()
    platform = (platform or "youtube").lower()

    # If empty keyword, supply default trending topic
    if not keyword:
        if platform == "tiktok":
            keyword = "stocks"
        elif platform == "instagram":
            keyword = "trading"
        else:
            keyword = "trending"

    # Direct URL fallback
    if keyword.startswith("http://") or keyword.startswith("https://"):
        try:
            ydl_opts = {'quiet': True, 'skip_download': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(keyword, download=False)
                vid = info.get("id", str(uuid.uuid4())[:8])
                thumb = info.get("thumbnail") or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"

                detected_platform = platform
                if "instagram.com" in keyword:
                    detected_platform = "instagram"
                elif "tiktok.com" in keyword:
                    detected_platform = "tiktok"
                elif "youtube.com" in keyword or "youtu.be" in keyword:
                    detected_platform = "youtube"

                dur = info.get("duration", 0)
                return [{
                    "id": str(vid),
                    "platform": detected_platform,
                    "title": info.get("title", "Direct Video"),
                    "url": keyword,
                    "direct_video_url": None,
                    "thumbnail": thumb,
                    "duration": dur,
                    "uploader": info.get("uploader", "Creator"),
                    "view_count": info.get("view_count", 0),
                    "content_type": "Short" if (dur and dur <= 95) else "Video"
                }]
        except Exception:
            pass

    if platform == "tiktok":
        results = _search_tiktok_rapidapi(keyword, max_results, offset=offset)
        if results:
            return results
        return _search_youtube(f"{keyword} tiktok", max_results, offset=offset)

    elif platform == "instagram":
        return _search_instagram_rapidapi(keyword, max_results, offset=offset)

    else:
        return _search_youtube(keyword, max_results, offset=offset)


# ---------------- DOWNLOAD HELPERS ----------------

def download_direct_stream(direct_url: str, output_path: str, platform: str = "tiktok") -> bool:
    """
    Directly streams video mp4 from CDN (TikTok/Instagram) using requests.
    Bypasses yt-dlp restrictions and anti-bot blocks.
    """
    try:
        referer = "https://www.tiktok.com/" if platform == "tiktok" else "https://www.instagram.com/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Referer': referer,
            'Accept': '*/*',
        }
        with requests.get(direct_url, headers=headers, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(output_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)

        if os.path.exists(output_path) and os.path.getsize(output_path) > 10_000:
            return True
    except Exception as e:
        logger.warning(f"Direct stream download failed: {e}")
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass
    return False


def _find_cached_direct_url(url: str) -> Optional[str]:
    """Looks up cached direct_video_url in search_cache.json if available."""
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for items in data.values():
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and item.get("url") == url:
                            return item.get("direct_video_url")
    except Exception:
        pass
    return None


def get_youtube_cookiefile() -> Optional[str]:
    """
    Finds or restores cookies.txt to authenticate yt-dlp on YouTube.
    Bypasses datacenter bot blocks ('Sign in to confirm you're not a bot').
    Sources checked:
    1. Local cookies.txt file
    2. YOUTUBE_COOKIES_BASE64 environment variable (Render env)
    3. YOUTUBE_COOKIES raw string environment variable
    """
    cookie_file = "cookies.txt"
    if os.path.exists(cookie_file) and os.path.getsize(cookie_file) > 10:
        return cookie_file

    b64_cookies = os.getenv("YOUTUBE_COOKIES_BASE64")
    if b64_cookies:
        try:
            import base64
            decoded = base64.b64decode(b64_cookies.strip()).decode("utf-8")
            with open(cookie_file, "w", encoding="utf-8") as f:
                f.write(decoded)
            print("[YOUTUBE] Successfully created cookies.txt from YOUTUBE_COOKIES_BASE64")
            return cookie_file
        except Exception as e:
            print(f"[YOUTUBE] Error decoding YOUTUBE_COOKIES_BASE64: {e}")

    raw_cookies = os.getenv("YOUTUBE_COOKIES")
    if raw_cookies:
        try:
            with open(cookie_file, "w", encoding="utf-8") as f:
                f.write(raw_cookies)
            print("[YOUTUBE] Successfully created cookies.txt from raw YOUTUBE_COOKIES")
            return cookie_file
        except Exception as e:
            print(f"[YOUTUBE] Error writing raw YOUTUBE_COOKIES: {e}")

    return None


def download_video_from_url(url: str, output_dir: str = "uploads", direct_url: Optional[str] = None) -> dict:
    """
    Downloads a video from TikTok, Instagram, YouTube, or direct CDN stream.
    Prioritizes direct CDN streaming for TikTok and Instagram to avoid yt-dlp failures.
    Uses mobile/iOS player client emulation + cookies for YouTube to bypass datacenter bot-checks.
    Returns metadata including local file path, title, description, and thumbnail.
    """
    os.makedirs(output_dir, exist_ok=True)
    unique_id = str(uuid.uuid4())[:8]

    # Check for direct CDN URL
    effective_direct_url = direct_url or _find_cached_direct_url(url)
    is_direct_link = (
        "tiktokcdn" in url or
        "cdn.routexapi.com" in url or
        "cdninstagram.com" in url or
        (url.startswith("http") and ".mp4" in url.split("?")[0])
    )
    if is_direct_link and not effective_direct_url:
        effective_direct_url = url

    # Method 1: Direct CDN Stream (Reliable for TikTok & Instagram)
    if effective_direct_url:
        stream_filename = f"dl_{unique_id}_stream.mp4"
        stream_path = os.path.join(output_dir, stream_filename)
        platform_hint = "tiktok" if "tiktok" in url or "tiktokcdn" in effective_direct_url else "instagram"
        print(f"[DOWNLOAD] Attempting direct stream download for: {platform_hint}")
        if download_direct_stream(effective_direct_url, stream_path, platform=platform_hint):
            return {
                "status": "success",
                "filename": stream_filename,
                "local_path": stream_path,
                "title": f"Viral {platform_hint.capitalize()} Video",
                "description": f"Trending short video from {platform_hint.capitalize()}",
                "uploader": f"{platform_hint.capitalize()} Creator",
                "thumbnail": "",
                "duration": 0
            }
        print("[DOWNLOAD] Direct stream download failed; falling back to yt-dlp.")

    # Method 2: yt-dlp Download with Mobile/iOS Extractor & Cookie Support
    cookie_path = get_youtube_cookiefile()
    output_template = os.path.join(output_dir, f"dl_{unique_id}_%(title).50s.%(ext)s")

    ydl_opts = {
        'format': 'best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
        'outtmpl': output_template,
        'noplaylist': True,
        'quiet': False,
        'no_warnings': True,
        'merge_output_format': 'mp4',
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android', 'mweb'],
                'player_skip': ['webpage', 'configs', 'js']
            }
        },
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
    }
    if cookie_path:
        ydl_opts['cookiefile'] = cookie_path
        print(f"[YOUTUBE] Using cookiefile: {cookie_path}")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'Downloaded Video')
            description = info.get('description', '') or ''
            uploader = info.get('uploader', '') or ''
            thumbnail = info.get('thumbnail', '') or ''
            duration = info.get('duration', 0)

            filename = ydl.prepare_filename(info)
            base_name, _ = os.path.splitext(filename)
            mp4_filename = f"{base_name}.mp4"

            actual_path = mp4_filename if os.path.exists(mp4_filename) else filename
            if not os.path.exists(actual_path):
                for f in os.listdir(output_dir):
                    if f.startswith(f"dl_{unique_id}"):
                        actual_path = os.path.join(output_dir, f)
                        break

            file_basename = os.path.basename(actual_path)
            return {
                "status": "success",
                "filename": file_basename,
                "local_path": actual_path,
                "title": title,
                "description": description[:500] if description else "",
                "uploader": uploader,
                "thumbnail": thumbnail,
                "duration": duration
            }

    except Exception as e:
        print(f"[YOUTUBE] Standard yt-dlp download failed: {e}. Trying fallback mobile format...")
        fallback_opts = {
            'format': 'worst[ext=mp4]/best[ext=mp4]/best',
            'outtmpl': os.path.join(output_dir, f"dl_{unique_id}_%(id)s.%(ext)s"),
            'noplaylist': True,
            'quiet': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios', 'mweb']
                }
            }
        }
        if cookie_path:
            fallback_opts['cookiefile'] = cookie_path

        try:
            with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                file_basename = os.path.basename(filename)
                return {
                    "status": "success",
                    "filename": file_basename,
                    "local_path": filename,
                    "title": info.get('title', 'Downloaded Video'),
                    "description": (info.get('description', '') or '')[:500],
                    "uploader": info.get('uploader', '') or '',
                    "thumbnail": info.get('thumbnail', '') or '',
                    "duration": info.get('duration', 0)
                }
        except Exception as fallback_err:
            raise Exception(f"Failed to download video from URL: {str(e)} | Fallback: {str(fallback_err)}")
