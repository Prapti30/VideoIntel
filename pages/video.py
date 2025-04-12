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
    st.session_state.chat_history = []
if 'current_video_id' not in st.session_state:
    st.session_state.current_video_id = None
if 'current_summary' not in st.session_state:
    st.session_state.current_summary = None

# === Core Functions ===
def generate_video_id(url):
    """Generate consistent video ID from any URL"""
    parsed = urlparse(url)
    if "youtube.com" in parsed.netloc:
        return parse_qs(parsed.query).get('v', [parsed.path.split('/')[-1]])[0]
    return str(uuid.uuid5(uuid.NAMESPACE_URL, url))  # For non-YouTube URLs

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
        
        # Extract path after Documents
        file_path = "/".join(relative_path.split("/")[1:])
        
        # Get drive ID
        site_resp = requests.get(
            f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root",
            headers={"Authorization": f"Bearer {token}"}
        )
        site_resp.raise_for_status()
        
        drive_id = site_resp.json()["parentReference"]["driveId"]
        
        # Get file metadata
        item_resp = requests.get(
            f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{file_path}",
            headers={"Authorization": f"Bearer {token}"}
        )
        item_resp.raise_for_status()
        
        # Download file
        item_id = item_resp.json()["id"]
        content_resp = requests.get(
            f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/content",
            headers={"Authorization": f"Bearer {token}"},
            stream=True
        )
        content_resp.raise_for_status()
        
        output_path = f"sp_video_{item_id}.mp4"
        with open(output_path, "wb") as f:
            for chunk in content_resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return output_path
        
    except Exception as e:
        st.error(f"SharePoint download failed: {str(e)}")
        return None

def get_summary_from_db(video_id):
    conn = get_snowflake_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SUMMARY FROM VIDEO_SUMMARY 
            WHERE VIDEO_ID = %s
            LIMIT 1
        """, (video_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        st.error(f"Database error: {str(e)}")
        return None
    finally:
        conn.close()

def store_summary(video_id, video_link, summary):
    conn = get_snowflake_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO VIDEO_SUMMARY (VIDEO_ID, YOUTUBE_LINK, SUMMARY)
            VALUES (%s, %s, %s)
            ON CONFLICT (VIDEO_ID) DO UPDATE 
            SET SUMMARY = EXCLUDED.SUMMARY
        """, (video_id, video_link, summary))
        conn.commit()
    except Exception as e:
        st.error(f"Database error: {str(e)}")
    finally:
        conn.close()

# === UI Setup ===
st.set_page_config(page_title="🎬 VideoIntel AI", layout="wide")
st.title("🎬 VideoIntel AI Processor & Chatbot")

# === Video Processing ===
video_link = st.text_input("Paste Video URL here 👇")
token = st.session_state.get("access_token")

if video_link:
    video_id = generate_video_id(video_link)
    existing_summary = get_summary_from_db(video_id)
    
    if existing_summary:
        st.session_state.current_summary = existing_summary
        st.session_state.current_video_id = video_id
        st.success("Loaded existing summary from database!")
    
    if st.button("Analyze Video") and not existing_summary:
        try:
            st.session_state.processing = True
            
            # Download video based on platform
            if "youtube.com" in video_link or "youtu.be" in video_link:
                filepath = download_youtube_video(video_link, video_id)
            elif "sharepoint.com" in video_link:
                if not token:
                    raise Exception("Authentication required for SharePoint videos")
                filepath = download_sharepoint_video(video_link, token)
                if not filepath:
                    st.write("no file found")
            else:
                raise Exception("Unsupported video platform")
            
            # Process video
            task_id = client.task.create(index_id=index_id, file=filepath).id
            while client.task.retrieve(task_id).status != "ready":
                time.sleep(5)
            
            summary = client.generate.summarize(
                video_id=client.task.retrieve(task_id).video_id,
                type="summary",
                prompt="Generate summary with timestamps"
            ).data.summary
            
            store_summary(video_id, video_link, summary)
            st.session_state.current_summary = summary
            st.session_state.current_video_id = video_id
            st.success("Analysis complete!")
            
        except Exception as e:
            st.error(f"Processing failed: {str(e)}")
        finally:
            st.session_state.processing = False

# === Chat Interface ===
if st.session_state.current_summary:
    st.subheader("📄 Video Summary")
    st.write(st.session_state.current_summary)
    
    st.subheader("💬 Chat with Video")
    user_question = st.text_input("Ask about the video...")
    
    if user_question:
        prompt = f"""
        Video Summary: {st.session_state.current_summary}
        Question: {user_question}
        Answer clearly with timestamps where relevant:
        """
        
        response = gemini_model.generate_content(prompt)
        if response.text:
            st.session_state.chat_history.append({
                "question": user_question,
                "answer": response.text
            })
    
    if st.session_state.chat_history:
        st.subheader("Chat History")
        for chat in st.session_state.chat_history:
            st.markdown(f"**Q:** {chat['question']}")
            st.markdown(f"**A:** {chat['answer']}")
            st.divider()
