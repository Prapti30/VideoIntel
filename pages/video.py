import requests
import streamlit as st
import subprocess
import time
import uuid
from urllib.parse import urlparse, parse_qs
from twelvelabs import TwelveLabs
from snowflake_connect import get_snowflake_connection
from google.generativeai import configure, GenerativeModel
import os
#from yt-dlp import YoutubeDL
 
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
    command = ["yt-dlp", "-f", "best", url]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
 
    if result.returncode != 0:
        raise Exception(f"yt-dlp failed: {result.stderr}")
    # Find most recently modified video file (assumes it's the one downloaded)
    files = [f for f in os.listdir('.') if f.endswith(".mp4")]
    if not files:
        raise Exception("No video file downloaded.")
    latest_file = max(files, key=os.path.getctime)
    return latest_file
 
def download_sharepoint_video(url, token):
    try:
        sharepoint_path = url.split("/personal/")[1]
        user_name, relative_path = sharepoint_path.split("/", 1)
        user_email = user_name.replace("_", ".").replace(".cginfinity.com", "@cginfinity.com")
        st.write(f"User Email: {user_email}")
 
        file_path = "/".join(relative_path.split("/")[1:])
        st.write(f"File Path: {file_path}")
 
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
 
def wait_for_indexing(task_id):
    while True:
        task = client.task.retrieve(task_id)
        if task.status == "ready":
            break
        time.sleep(10)
 
def summarize_video(task_id):
    task = client.task.retrieve(task_id)
    if task.status != "ready":
        raise Exception("Video not ready for summarization.")
    response = client.generate.summarize(
        video_id=task.video_id,
        type="summary",
        prompt="Generate summary in document format with timestamps."
    )
    return response.data.summary if hasattr(response, 'data') else response.summary
 
def store_data_in_snowflake(video_id, video_link, summary):
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS VIDEO_SUMMARY (
                VIDEO_ID VARCHAR PRIMARY KEY,
                YOUTUBE_LINK STRING,
                SUMMARY STRING,
                CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                IS_ACTIVE BOOLEAN DEFAULT TRUE
            )
        """)
        cursor.execute("""
            INSERT INTO VIDEO_SUMMARY (VIDEO_ID, YOUTUBE_LINK, SUMMARY, CREATED_AT, IS_ACTIVE)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP(), TRUE)
        """, (video_id, video_link, summary))
    except Exception as e:
        raise Exception(f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()
 
def get_summary_by_link(video_link):
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT VIDEO_ID, SUMMARY
            FROM VIDEO_SUMMARY
            WHERE YOUTUBE_LINK = %s
            LIMIT 1
        """, (video_link,))
        result = cursor.fetchone()
        if result:
            return result[0], result[1]
        return None, None
    except Exception as e:
        raise Exception(f"Query failed: {str(e)}")
    finally:
        cursor.close()
        conn.close()
 
# === UI Setup ===
st.set_page_config(page_title="🎬 VideoIntel AI", layout="wide")
st.title("🎬 VideoIntel AI Processor & Chatbot")
 
# === Two Columns Layout ===
col1, col2 = st.columns(2)
 
with col1:
    st.subheader("Smart Video Assistant")
 
    video_type = st.selectbox("Select Video Type", ["YouTube", "SharePoint"])
    video_link = st.text_input("Paste Video URL here 👇")
    token = st.session_state.get("access_token")  # Replace with actual token retrieval logic
 
    if video_link:
        video_id, summary = get_summary_by_link(video_link)
 
        if video_id and summary:
            st.success("Video summary already available!")
            st.session_state.current_video_id = video_id
            st.session_state.current_summary = summary
        else:
            if st.button("Analyze Video"):
                try:
                    st.session_state.processing = True
                    video_id = get_video_id(video_link)
                    filepath = None
 
                    if video_type == "YouTube":
                        with st.spinner("Downloading YouTube video..."):
                            filepath = download_youtube_video(video_link, video_id)
                    elif video_type == "SharePoint" and token:
                        with st.spinner("Downloading SharePoint video..."):
                            filepath = download_sharepoint_video(video_link, token)
 
                    with st.spinner("Uploading video to TwelveLabs..."):
                        task_id = upload_video(filepath)
 
                    with st.spinner("Indexing video..."):
                        wait_for_indexing(task_id)
 
                    with st.spinner("Summarizing video..."):
                        summary = summarize_video(task_id)
 
                    st.session_state.current_video_id = video_id
                    st.session_state.current_summary = summary
 
                    with st.spinner("Saving summary to Snowflake..."):
                        store_data_in_snowflake(video_id, video_link, summary)
 
                    st.success("Video processed and summary saved!")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                finally:
                    st.session_state.processing = False
 
    if st.session_state.current_summary:
        st.subheader("📄 Video Summary")
        st.write(st.session_state.current_summary)
 
with col2:
    st.subheader("Ask Questions about the Video")
 
    if st.session_state.current_summary:
        user_question = st.text_input("Ask your question here...")
 
        if user_question:
            chat_input = {
                "role": "user",
                "parts": [f"You are an intelligent video assistant. Based on the following summary, answer the user's question clearly with timestamps if possible.: {st.session_state.current_summary}\n\nQuestion: {user_question}"]
            }
 
            with st.spinner("Thinking..."):
                response = gemini_model.generate_content([chat_input])
 
            if hasattr(response, 'text'):
                st.session_state.chat_history[user_question] = response.text
                st.success("Answer generated!")
            else:
                st.error("Failed to get response from Gemini.")
 
    if st.session_state.chat_history:
        st.subheader("💬 Chat History")
        for question, answer in st.session_state.chat_history.items():
            st.markdown(f"**Q:** {question}")
            st.markdown(f"**A:** {answer}")
            st.markdown("---")