# app.py

import streamlit as st
import requests
import uuid
import time
import os
from twelvelabs import TwelveLabs
from snowflake.connector import connect
from google.generativeai import configure, GenerativeModel

# ==== API Keys & Configurations ====
twelve_api_key = "YOUR_TWELVE_LABS_API_KEY"
index_id = "YOUR_TWELVE_LABS_INDEX_ID"
gemini_api_key = "YOUR_GEMINI_API_KEY"

snowflake_user = "YOUR_SNOWFLAKE_USER"
snowflake_password = "YOUR_SNOWFLAKE_PASSWORD"
snowflake_account = "YOUR_SNOWFLAKE_ACCOUNT"
snowflake_database = "YOUR_DATABASE"
snowflake_schema = "YOUR_SCHEMA"
snowflake_warehouse = "YOUR_WAREHOUSE"

# ==== Initialize Clients ====
client = TwelveLabs(api_key=twelve_api_key)
configure(api_key=gemini_api_key)
gemini_model = GenerativeModel(model_name="gemini-1.5-pro")

# ==== Session State Initialization ====
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'results' not in st.session_state:
    st.session_state.results = []
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'current_video_id' not in st.session_state:
    st.session_state.current_video_id = None
if 'current_summary' not in st.session_state:
    st.session_state.current_summary = None

# ==== Functions ====

def download_sharepoint_video_direct(url):
    """Download video from SharePoint if publicly accessible"""
    try:
        temp_filename = f"temp_video_{uuid.uuid4()}.mp4"
        with requests.get(url, stream=True) as response:
            response.raise_for_status()
            with open(temp_filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        return temp_filename
    except Exception as e:
        st.error(f"Failed to download video: {e}")
        return None

def upload_video(filepath):
    """Upload video to TwelveLabs"""
    try:
        task = client.task.create(index_id=index_id, file=filepath)
        return task.id
    except Exception as e:
        st.error(f"Failed to upload video: {e}")
        return None

def wait_for_indexing(task_id):
    """Wait for TwelveLabs to finish indexing"""
    st.info("Waiting for TwelveLabs to index the video...")
    while True:
        task = client.task.retrieve(task_id)
        if task.status == "ready":
            st.success("Video indexing completed.")
            return task
        elif task.status == "failed":
            st.error("Video indexing failed.")
            return None
        time.sleep(5)

def get_snowflake_connection():
    """Connect to Snowflake"""
    conn = connect(
        user=snowflake_user,
        password=snowflake_password,
        account=snowflake_account,
        warehouse=snowflake_warehouse,
        database=snowflake_database,
        schema=snowflake_schema,
    )
    return conn

def store_video_info_in_snowflake(video_id, task_id, video_name):
    """Store video info in Snowflake"""
    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS uploaded_videos (
                video_id STRING,
                task_id STRING,
                video_name STRING,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            INSERT INTO uploaded_videos (video_id, task_id, video_name)
            VALUES (%s, %s, %s)
        """, (video_id, task_id, video_name))
        conn.commit()
        st.success("Video info stored in Snowflake.")
    except Exception as e:
        st.error(f"Failed to store video info in Snowflake: {e}")
    finally:
        cursor.close()
        conn.close()

# ==== Streamlit UI ====

st.title("📹 SharePoint Video Processor")

sharepoint_url = st.text_input("Enter SharePoint Video URL:")

if st.button("Process Video"):
    if not sharepoint_url:
        st.warning("⚠️ Please enter a valid SharePoint URL.")
    else:
        st.session_state.processing = True

        filepath = download_sharepoint_video_direct(sharepoint_url)

        if filepath:
            st.success("✅ Video downloaded successfully!")

            task_id = upload_video(filepath)

            if task_id:
                task = wait_for_indexing(task_id)

                if task:
                    video_id = task.metadata.video_id
                    video_name = os.path.basename(filepath)

                    st.session_state.current_video_id = video_id
                    store_video_info_in_snowflake(video_id, task_id, video_name)

                    st.balloons()
                    st.success(f"🎉 Video '{video_name}' processed and stored successfully!")
                    
                    # Clean up downloaded video
                    if os.path.exists(filepath):
                        os.remove(filepath)
                else:
                    st.error("❌ Video processing failed during indexing.")
            else:
                st.error("❌ Failed to upload video to TwelveLabs.")
        else:
            st.error("❌ Failed to download video from SharePoint.")
