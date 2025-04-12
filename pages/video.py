import requests
import streamlit as st
import subprocess
import time
import uuid
from urllib.parse import urlparse, parse_qs
from twelvelabs import TwelveLabs
from snowflake_connect import get_snowflake_connection
from google.generativeai import configure, GenerativeModel

# === API Keys ===
api_key = "tlk_1CPRENS1M7PJ1G2HTQ1QN2JHC2RS"
index_id = "67f69df0f42e97f625940bcd"
client = TwelveLabs(api_key=api_key)

configure(api_key="AIzaSyD5avNnryzA6Y-sDTRS_vcj55O91Xlcq5o") 
gemini_model = GenerativeModel("gemini-1.5-pro")

# === Session States ===
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'results' not in st.session_state:
    st.session_state.results = []
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = {}
if 'current_video_id' not in st.session_state:
    st.session_state.current_video_id = None
if 'current_summary' not in st.session_state:
    st.session_state.current_summary = None

# === Core Functions ===
def get_video_id(url):
    parsed_url = urlparse(url)
    query = parse_qs(parsed_url.query)
    if 'v' in query:  # For YouTube URLs
        return query['v'][0]
    return parsed_url.path.split('/')[-1]  # For SharePoint or other links

def download_youtube_video(url, video_id):
    output_path = f"video_{video_id}.mp4"
    command = f"yt-dlp -f best -o {output_path} {url}"
    subprocess.run(command, shell=True, check=True)
    return output_path

def download_sharepoint_video(url, token):
    try:
        sharepoint_path = url.split("/personal/")[1]
        user_name, relative_path = sharepoint_path.split("/", 1)
        user_email = user_name.replace("_", ".").replace(".cginfinity.com", "@cginfinity.com")
        file_path = "/".join(relative_path.split("/")[1:])

        site_resp = requests.get(
            f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root",
            headers={"Authorization": f"Bearer {token}"}
        )

        if site_resp.status_code != 200:
            raise Exception(f"Failed to retrieve OneDrive site. Error: {site_resp.json()}")

        drive_id = site_resp.json().get("parentReference", {}).get("driveId")
        if not drive_id:
            raise Exception("Could not retrieve drive ID.")

        item_resp = requests.get(
            f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{file_path}",
            headers={"Authorization": f"Bearer {token}"}
        )

        if item_resp.status_code != 200:
            raise Exception(f"File not found. Error: {item_resp.json()}")

        item_id = item_resp.json().get("id")

        content_resp = requests.get(
            f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/content",
            headers={"Authorization": f"Bearer {token}"},
            stream=True
        )

        if content_resp.status_code == 200:
            output_path = "temp_video.mp4"
            with open(output_path, "wb") as f:
                for chunk in content_resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return output_path
        else:
            raise Exception(f"Download failed. Status: {content_resp.status_code}")
    except Exception as e:
        raise Exception(f"Error downloading SharePoint video: {str(e)}")

def upload_video(filepath):
    task = client.task.create(index_id=index_id, file=filepath)
    return task.id

def wait_for_task(task_id):
    while True:
        task = client.task.retrieve(task_id)
        if task.status == "completed":
            return task
        elif task.status == "failed":
            raise Exception("Task failed")
        time.sleep(5)

def generate_summary(captions):
    input_text = f"Summarize the following video transcript:\n\n{captions}"
    response = gemini_model.generate_content(input_text)
    return response.text

def save_summary_to_snowflake(video_id, summary_text):
    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS video_summaries (
                video_id VARCHAR,
                summary TEXT
            )
        """)
        
        cursor.execute("""
            INSERT INTO video_summaries (video_id, summary)
            VALUES (%s, %s)
        """, (video_id, summary_text))
        
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        st.error(f"Error saving summary to Snowflake: {str(e)}")

def process_video(url, token=None):
    video_id = get_video_id(url)
    st.session_state.current_video_id = video_id

    if "youtube.com" in url or "youtu.be" in url:
        filepath = download_youtube_video(url, video_id)
    else:
        filepath = download_sharepoint_video(url, token)

    task_id = upload_video(filepath)
    wait_for_task(task_id)

    captions = client.caption.search(index_id=index_id, query="*", filters={"video_ids": [task_id]})
    all_text = " ".join([caption.text for caption in captions.matches])

    summary = generate_summary(all_text)
    st.session_state.current_summary = summary

    save_summary_to_snowflake(video_id, summary)

    st.success("Video processed and summary saved!")

# === Streamlit UI ===
st.title("Video Summarizer and Storage App")

video_url = st.text_input("Enter YouTube or SharePoint video URL:")
sharepoint_token = st.text_input("Enter SharePoint OAuth Token (if using SharePoint):", type="password")

if st.button("Process Video"):
    if not video_url:
        st.error("Please provide a video URL.")
    else:
        try:
            process_video(video_url, sharepoint_token)
        except Exception as e:
            st.error(f"Error: {str(e)}")
