import streamlit as st
import subprocess
import time
import uuid
from twelvelabs import TwelveLabs
from snowflake_connect import get_snowflake_connection

# === API Keys ===
api_key = "tlk_1CPRENS1M7PJ1G2HTQ1QN2JHC2RS"
index_id = "67f69df0f42e97f625940bcd"
client = TwelveLabs(api_key=api_key)

from google.generativeai import configure, GenerativeModel
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
def download_youtube_video(url, video_id):
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

def store_data_in_snowflake(video_id, youtube_link, summary):
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
            """, (video_id, youtube_link, summary))
    except Exception as e:
        raise Exception(f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()

def query_summary(video_id, question):
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        # Use ILIKE for case-insensitive matching
        cursor.execute("""
            SELECT SUMMARY 
            FROM VIDEO_SUMMARY
            WHERE VIDEO_ID = %s AND SUMMARY ILIKE %s
        """, (video_id, f"%{question}%"))  # Add wildcards for partial match
        return cursor.fetchall()
    except Exception as e:
        raise Exception(f"Query failed: {str(e)}")
    finally:
        cursor.close()
        conn.close()

# === UI Setup ===
st.set_page_config(page_title="🎬 VideoIntel AI", layout="centered")
st.title("🎬 VideoIntel AI Processor & Chatbot")
st.subheader("YouTube Video Analysis with Gemini Q&A")

# === Video Processor Form ===
st.write("## 🎥 Process a YouTube Video")

with st.form("video_processor"):
    youtube_url = st.text_input("Enter YouTube Video URL", placeholder="https://cygrp-my.sharepoint.com/...")
    process_btn = st.form_submit_button("Process Video")

if process_btn and youtube_url:
    if not youtube_url.startswith(("https://cygrp-my.sharepoint.com/")):
        st.error("❌ Invalid YouTube URL.")
        st.stop()

    video_id = str(uuid.uuid4())

    st.session_state.processing = True
    st.session_state.results.append({
        "id": video_id,
        "url": youtube_url,
        "status": "processing",
        "summary": None,
        "error": None
    })

    try:
        with st.status("Processing video...", expanded=True) as status:
            st.write("1. Downloading video...")
            video_path = download_youtube_video(youtube_url, video_id)
            st.write("✅ Video downloaded")

            st.write("2. Uploading to AI engine...")
            task_id = upload_video(video_path)
            st.write(f"✅ Upload complete (Task ID: {task_id})")

            st.write("3. Indexing content...")
            wait_for_indexing(task_id)
            st.write("✅ Indexing done")

            st.write("4. Generating summary...")
            summary = summarize_video(task_id)
            st.write("✅ Summary generated")

            st.session_state.results[-1].update({
                "status": "complete",
                "summary": summary
            })

            store_data_in_snowflake(video_id, youtube_url, summary)

            status.update(label="✅ Processing complete!", state="complete")

    except Exception as e:
        st.error(f"❌ Processing failed: {str(e)}")
        st.session_state.results[-1].update({
            "status": "error",
            "error": str(e)
        })

# === Results Section ===
if st.session_state.results:
    st.write("## 📊 Results")
    for result in st.session_state.results:
        with st.container():
            col1, col2 = st.columns([1, 3])
            with col1:
                st.metric("Status", result['status'].upper())
                st.metric("Video ID", result['id'][:8])
            with col2:
                if result['status'] == "complete":
                    st.success("🎉 Video processed")
                    st.download_button(
                        label="📥 Download Summary",
                        data=result['summary'],
                        file_name=f"{result['id']}_summary.txt",
                        mime="text/plain"
                    )
                    st.text_area("📄 Summary Output", result['summary'], height=300)
                elif result['status'] == "error":
                    st.error(f"❌ Error: {result['error']}")
                else:
                    st.info("⏳ Processing...")

# === Gemini Q&A Chatbot ===
st.write("## 🤖 Ask Gemini about a Video")
import re 

col1, col2 = st.columns([1, 3])
with col1:
    video_id_input = st.text_input("Video ID (First few characters)")
with col2:
    user_question = st.text_input("Your Question")

matched_summary = None
full_video_id = None

# Setup a session flag to avoid rerunning Gemini on every refresh
if "question_asked" not in st.session_state:
    st.session_state.question_asked = False

# === 1. Fetch summary using LIKE ===
if video_id_input:
    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT VIDEO_ID, SUMMARY 
            FROM VIDEO_SUMMARY
            WHERE VIDEO_ID LIKE %s
        """, (video_id_input + '%',))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result:
            full_video_id = result[0]
            matched_summary = result[1]
            video_id_input = full_video_id  # Replace partial with full ID
        else:
            st.info("ℹ️ No summary found for this Video ID.")
    except Exception as e:
        st.error(f"❌ Error fetching summary: {str(e)}")

# === 2. Ask Gemini a question (only once per user action) ===
if user_question and matched_summary and not st.session_state.question_asked:
    try:
        prompt = f"""You are an intelligent video assistant. Based on the following summary, answer the user's question clearly with timestamps if possible.

Summary:
{matched_summary}

Question:
{user_question}
"""

        # Make sure this is at the top of your file

        gemini_response = gemini_model.generate_content(prompt)
        answer = gemini_response.text

        # Extract timestamp from Gemini's response using regex like [00:58-01:19]
        timestamp_match = re.search(r"(?:(?:from|at)?\s*)?(\d{2}:\d{2}(?::\d{2})?)\s*(?:to|-)?\s*(\d{2}:\d{2}(?::\d{2})?)?",answer)

        if timestamp_match:
            start = timestamp_match.group(1)
            end = timestamp_match.group(2)
            if end:
                timestamp_str = f"{start}–{end}"
            else:
                timestamp_str = start
        else:
            timestamp_str = "N/A"

        # Initialize chat history
        if video_id_input not in st.session_state.chat_history:
            st.session_state.chat_history[video_id_input] = []

        # Append user and assistant messages
        st.session_state.chat_history[video_id_input].append({
            'role': 'user',
            'content': user_question
        })
        st.session_state.chat_history[video_id_input].append({
            'role': 'assistant',
            'content': answer,
            'timestamp': timestamp_str
        })

        st.session_state.question_asked = True  # Stop Gemini from running again
          # Rerun to show conversation without re-hitting Gemini

    except Exception as e:
        st.error(f"❌ Gemini Error: {str(e)}")

# === 3. Show chat history ===
if video_id_input in st.session_state.chat_history:
    st.write("### 💬 Conversation History")
    for msg in st.session_state.chat_history[video_id_input]:
        with st.chat_message(msg['role']):
            st.write(msg['content'])
            if msg['role'] == 'assistant' and 'timestamp' in msg:
                st.caption(f"📍 Timestamp: {msg['timestamp']}")

# === 4. Reset on new question ===
if user_question and st.session_state.question_asked:
    st.session_state.question_asked = False
