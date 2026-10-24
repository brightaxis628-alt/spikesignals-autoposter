import os
import base64
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_authenticated_service():
    creds = None

    # 1. Try Environment Variable (For Render cloud deployment)
    env_token = os.getenv("YOUTUBE_TOKEN_BASE64")
    if env_token:
        try:
            creds = pickle.loads(base64.b64decode(env_token))
        except Exception as e:
            print(f"[YOUTUBE] Error loading token from YOUTUBE_TOKEN_BASE64: {e}")

    # 2. Try local token.pickle file
    if not creds and os.path.exists('token.pickle'):
        try:
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        except Exception as e:
            print(f"[YOUTUBE] Error loading token.pickle: {e}")

    # 3. Refresh expired credentials
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            print(f"[YOUTUBE] Error refreshing token: {e}")
            creds = None

    # 4. If still invalid and running locally with display, run OAuth flow
    if not creds or not creds.valid:
        if os.path.exists('client_secret.json'):
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        else:
            raise Exception("No valid YouTube credentials found and client_secret.json is missing.")

    return build('youtube', 'v3', credentials=creds)

def upload_video(video_path, title, description, category="22", privacy_status="public"):
    """
    Uploads a video to YouTube natively via API.
    Category 22 is 'People & Blogs'.
    """
    youtube = get_authenticated_service()

    body = {
        'snippet': {
            'title': title,
            'description': description,
            'categoryId': category
        },
        'status': {
            'privacyStatus': privacy_status,
            'selfDeclaredMadeForKids': False
        }
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploaded {int(status.progress() * 100)}%")

    print(f"Video id '{response['id']}' was successfully uploaded.")
    return response['id']
