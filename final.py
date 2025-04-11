import streamlit as st
import subprocess
import time
import uuid
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

# === Core Functions ===
def download_video(url, video_id):
    output_path = f"video_{video_id}.mp4"
    command = f"yt-dlp -f best -o {output_path} {url}"
    subprocess.run(command, shell=True, check=True)
    return output_path

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
        if video_id:
            cursor.execute("""
                INSERT INTO VIDEO_SUMMARY (VIDEO_ID, YOUTUBE_LINK, SUMMARY, CREATED_AT, IS_ACTIVE)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP(), TRUE)
            """, (video_id, video_link, summary))
    except Exception as e:
        raise Exception(f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()

def query_summary(video_id, question):
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT SUMMARY 
            FROM VIDEO_SUMMARY
            WHERE VIDEO_ID = %s AND SUMMARY ILIKE %s
        """, (video_id, f"%{question}%"))
        return cursor.fetchall()
    except Exception as e:
        raise Exception(f"Query failed: {str(e)}")
    finally:
        cursor.close()
        conn.close()

# === UI Setup ===
st.set_page_config(page_title="🎬 VideoIntel AI", layout="centered")
st.title("🎬 VideoIntel AI Processor & Chatbot")
st.subheader("Analyze YouTube/SharePoint Videos + Gemini Q&A")

# === Video Processor Form ===
st.write("## 🎥 Process a Video")

with st.form("video_processor"):
    video_source = st.selectbox("Select Video Source", ["YouTube", "SharePoint"])
    video_url = st.text_input("Enter Video URL", placeholder="Enter full URL...")
    process_btn = st.form_submit_button("Process Video")

if process_btn and video_url:
    valid = False
    if video_source == "YouTube" and video_url.startswith(("https://www.youtube.com", "https://youtu.be")):
        valid = True
    elif video_source == "SharePoint" and video_url.startswith("https://cygrp-my.sharepoint.com/"):
        valid = True

    if not valid:
        st.error(f"❌ Invalid URL for selected source: {video_source}")
        st.stop()

    video_id = str(uuid.uuid4())

    st.session_state.processing = True
    st.session_state.results.append({
        "id": video_id,
        "url": video_url,
        "status": "processing",
        "summary": None,
        "error": None
    })

    try:
        st.info("📥 Downloading video...")
        filepath = download_video(video_url, video_id)

        st.info("🚀 Uploading and indexing video...")
        task_id = upload_video(filepath)
        wait_for_indexing(task_id)

        st.info("🧠 Summarizing video...")
        summary = summarize_video(task_id)

        st.success("✅ Video summarized successfully!")
        st.session_state.results[-1]["status"] = "completed"
        st.session_state.results[-1]["summary"] = summary

        st.info("💾 Saving summary to database...")
        store_data_in_snowflake(video_id, video_url, summary)
        st.success("✅ Data saved successfully!")

    except Exception as e:
        st.session_state.results[-1]["status"] = "error"
        st.session_state.results[-1]["error"] = str(e)
        st.error(f"❌ Error: {str(e)}")

# === Chatbot Section ===
st.write("---")
st.write("## 🤖 Chat with Video Summary")

if st.session_state.results:
    latest_result = st.session_state.results[-1]
    if latest_result["status"] == "completed":
        st.success("Video is ready! Start asking questions about the video.")
        user_question = st.text_input("Ask a question about the video:")

        if user_question:
            try:
                matched_summaries = query_summary(latest_result["id"], user_question)
                if matched_summaries:
                    combined_text = " ".join([row[0] for row in matched_summaries])
                else:
                    combined_text = latest_result["summary"]

                response = gemini_model.generate_content(f"Answer the following question based on the video summary also give timestamp of which point has occured when in video: {user_question}\n\nSummary:\n{combined_text}")

                if hasattr(response, 'text'):
                    st.write(response.text)
                else:
                    st.write(response.candidates[0]['content']['parts'][0]['text'])
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
