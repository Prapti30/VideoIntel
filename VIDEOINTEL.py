import streamlit as st
import subprocess
import time
import uuid
import requests
from urllib.parse import urlparse, parse_qs
from twelvelabs import TwelveLabs
from snowflake_connect import get_snowflake_connection
from google.generativeai import configure, GenerativeModel
import os

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
    if 'v' in query:
        return query['v'][0]
    return parsed_url.path.split('/')[-1]

def download_youtube_video(url, video_id):
    output_path = f"video_{video_id}.mp4"
    try:
        command = f"yt-dlp -f best -o {output_path} {url}"
        subprocess.run(command, shell=True, check=True)
        if not os.path.exists(output_path):
            raise Exception(f"Video file was not downloaded: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to download YouTube video. {str(e)}")

def download_sharepoint_video(url, video_id):
    output_path = f"sharepoint_video_{video_id}.mp4"
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return output_path
        else:
            raise Exception(f"Failed to download SharePoint video. Status code: {response.status_code}")
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
            MERGE INTO VIDEO_SUMMARY AS target
            USING (SELECT %(video_id)s AS VIDEO_ID) AS source
            ON target.VIDEO_ID = source.VIDEO_ID
            WHEN NOT MATCHED THEN
              INSERT (VIDEO_ID, YOUTUBE_LINK, SUMMARY, CREATED_AT, IS_ACTIVE)
              VALUES (%(video_id)s, %(video_link)s, %(summary)s, CURRENT_TIMESTAMP(), TRUE)
        """, {
            'video_id': video_id,
            'video_link': video_link,
            'summary': summary
        })
    finally:
        cursor.close()
        conn.close()

# === Streamlit UI ===
st.title("🎥 Video Summarization App")

source_type = st.selectbox("Select Video Source:", ["YouTube", "SharePoint"])
video_link = st.text_input("Enter the Video Link:")

if st.button("Process Video") and video_link:
    st.session_state.processing = True
    try:
        video_id = str(uuid.uuid4())[:8]

        # Download based on selection
        if source_type == "YouTube":
            st.info("Downloading YouTube video...")
            video_path = download_youtube_video(video_link, video_id)
        else:
            st.info("Downloading SharePoint video...")
            video_path = download_sharepoint_video(video_link, video_id)

        st.success("Video downloaded successfully!")

        st.info("Uploading video to TwelveLabs...")
        task_id = upload_video(video_path)
        wait_for_indexing(task_id)

        st.info("Generating summary...")
        summary = summarize_video(task_id)

        st.success("Summary generated!")

        # Save results
        st.session_state.current_video_id = video_id
        st.session_state.current_summary = summary

        # Display
        st.subheader("Video Summary:")
        st.write(summary)

        # Store in Snowflake
        store_data_in_snowflake(video_id, video_link, summary)
        st.success("Summary stored in Snowflake database!")

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
    finally:
        st.session_state.processing = False
