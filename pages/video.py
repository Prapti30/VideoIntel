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
twelve_api_key = "tlk_1CPRENS1M7PJ1G2HTQ1QN2JHC2RS"
index_id = "67f69df0f42e97f625940bcd"
client = TwelveLabs(api_key=twelve_api_key)

configure(api_key="AIzaSyD5avNnryzA6Y-sDTRS_vcj55O91Xlcq5o") 
gemini_model = GenerativeModel("gemini-1.5-pro")

# === Session States ===
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

# === Core Functions ===
def download_sharepoint_video(url, token):
    try:
        sharepoint_path = url.split("/personal/")[1]
        user_name, relative_path = sharepoint_path.split("/", 1)
        user_email = user_name.replace("_", ".").replace(".cginfinity.com", "@cginfinity.com")

        file_path = "/".join(relative_path.split("/")[1:])

        # Get user's OneDrive root folder
        site_resp = requests.get(
            f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root",
            headers={"Authorization": f"Bearer {token}"}
        )
        site_resp.raise_for_status()
        drive_id = site_resp.json().get("parentReference", {}).get("driveId")

        # Get file metadata
        item_resp = requests.get(
            f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{file_path}",
            headers={"Authorization": f"Bearer {token}"}
        )
        item_resp.raise_for_status()
        item_id = item_resp.json().get("id")

        # Download video
        content_resp = requests.get(
            f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/content",
            headers={"Authorization": f"Bearer {token}"},
            stream=True
        )
        content_resp.raise_for_status()

        output_path = f"temp_video_{uuid.uuid4()}.mp4"
        with open(output_path, "wb") as f:
            for chunk in content_resp.iter_content(chunk_size=8192):
                f.write(chunk)

        return output_path
    except Exception as e:
        st.error(f"Error downloading SharePoint video: {str(e)}")
        return None

def upload_video(filepath):
    task = client.task.create(index_id=index_id, file=filepath)
    return task.id

def wait_for_indexing(task_id):
    while True:
        task = client.task.retrieve(task_id)
        if task.status == "ready":
            return task
        time.sleep(5)

def store_video_info_in_snowflake(video_id, task_id, video_name):
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
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
    except Exception as e:
        st.error(f"Failed to store in Snowflake: {str(e)}")
    finally:
        cursor.close()
        conn.close()

def chat_with_gemini(prompt):
    chat = gemini_model.start_chat(history=st.session_state.chat_history)
    response = chat.send_message(prompt)
    st.session_state.chat_history.append({"role": "user", "parts": [prompt]})
    st.session_state.chat_history.append({"role": "model", "parts": [response.text]})
    return response.text

# === Streamlit UI ===
st.title("SharePoint Video Uploader + Chatbot")

sharepoint_url = st.text_input("Enter SharePoint Video URL:")
access_token = st.text_input("Enter Access Token (Microsoft Graph API):", type="password")

if st.button("Upload and Index Video"):
    if sharepoint_url and access_token:
        st.session_state.processing = True
        video_path = download_sharepoint_video(sharepoint_url, access_token)
        if video_path:
            st.success("Video downloaded successfully!")

            # Upload to TwelveLabs
            task_id = upload_video(video_path)
            st.info("Uploaded to TwelveLabs, waiting for indexing...")
            task_info = wait_for_indexing(task_id)

            video_id = str(uuid.uuid4())
            video_name = video_path.split("/")[-1]

            st.session_state.current_video_id = video_id

            # Store in Snowflake
            store_video_info_in_snowflake(video_id, task_id, video_name)
            st.success("Stored video info in Snowflake Database!")
            st.success("Video ready! Start chatting below 👇")

        st.session_state.processing = False
    else:
        st.error("Please enter both SharePoint URL and Access Token.")

# === Chatbot Section ===
if st.session_state.current_video_id:
    st.header("Chat with the Video 📽️🤖")
    user_prompt = st.text_input("Ask something about the video:")

    if st.button("Send"):
        if user_prompt:
            response = chat_with_gemini(user_prompt)
            st.markdown(f"**Gemini:** {response}")

    # Show chat history
    if st.session_state.chat_history:
        st.subheader("Chat History:")
        for message in st.session_state.chat_history:
            role = message["role"]
            text = message["parts"][0]
            if role == "user":
                st.markdown(f"**You:** {text}")
            else:
                st.markdown(f"**Gemini:** {text}")
