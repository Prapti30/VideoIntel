# === Imports ===
import requests
import streamlit as st
import subprocess
import time
from urllib.parse import urlparse, parse_qs
from twelvelabs import TwelveLabs
from snowflake_connect import get_snowflake_connection  # <-- Make sure this is correct
from google.generativeai import configure, GenerativeModel

# === API Keys ===
api_key = "tlk_1CPRENS1M7PJ1G2HTQ1QN2JHC2RS"
index_id = "67f69df0f42e97f625940bcd"
client = TwelveLabs(api_key=api_key)

configure(api_key="AIzaSyD5avNnryzA6Y-sDTRS_vcj55O91Xlcq5o")
gemini_model = GenerativeModel("gemini-1.5-pro")

# === Session State Initialization ===
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'results' not in st.session_state:
    st.session_state.results = []
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'current_summary' not in st.session_state:
    st.session_state.current_summary = None

# === Utility Functions ===
def get_video_id(url):
    parsed_url = urlparse(url)
    query = parse_qs(parsed_url.query)
    if 'v' in query:  # YouTube
        return query['v'][0]
    return parsed_url.path.split('/')[-1]

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
        time.sleep(5)

def search_video(query, video_id):
    search = client.search.query(index_id=index_id, query=query)
    return search.matches

def insert_summary_to_snowflake(video_id, video_url, summary_text):
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    insert_query = """
    INSERT INTO video_summaries (video_id, video_url, summary_text)
    VALUES (%s, %s, %s)
    """
    cursor.execute(insert_query, (video_id, video_url, summary_text))
    conn.commit()
    cursor.close()
    conn.close()

def generate_summary(matches):
    if matches:
        highlights = "\n".join([match.text for match in matches])
        response = gemini_model.generate_content(f"Summarize this content: {highlights}")
        return response.text
    else:
        return "No relevant matches found."

def chat_with_summary(user_input, context_summary):
    prompt = f"Context: {context_summary}\n\nUser: {user_input}\nBot:"
    response = gemini_model.generate_content(prompt)
    return response.text

# === Main Streamlit App ===
st.title("📹 Video Summarizer + Chatbot Assistant")

video_url = st.text_input("Enter YouTube or SharePoint Video URL")

if st.button("Process Video"):
    if not video_url:
        st.error("Please provide a video URL.")
    else:
        st.session_state.processing = True
        try:
            video_id = get_video_id(video_url)
            st.info("Downloading video...")
            filepath = download_youtube_video(video_url, video_id)

            st.success("Video downloaded. Uploading to TwelveLabs...")
            task_id = upload_video(filepath)

            st.info("Indexing video, please wait...")
            wait_for_indexing(task_id)

            st.success("Video indexed. Searching for summary points...")
            matches = search_video("summarize the video", video_id)

            st.session_state.current_summary = generate_summary(matches)
            st.success("Summary generated!")

            st.write("### Summary")
            st.write(st.session_state.current_summary)

            # Insert into Snowflake
            insert_summary_to_snowflake(video_id, video_url, st.session_state.current_summary)
            st.success("Summary saved to database! ✅")

        except Exception as e:
            st.error(f"Error: {str(e)}")
        finally:
            st.session_state.processing = False

# === Chatbot Section ===
st.divider()
st.header("💬 Chat with the Video Summary")

user_query = st.text_input("Ask something about the video...")

if st.button("Ask"):
    if not st.session_state.current_summary:
        st.error("First process a video and generate summary!")
    elif not user_query:
        st.error("Please type your question.")
    else:
        bot_response = chat_with_summary(user_query, st.session_state.current_summary)
        st.session_state.chat_history.append(("You", user_query))
        st.session_state.chat_history.append(("Bot", bot_response))

# Display chat history
for speaker, text in st.session_state.chat_history:
    if speaker == "You":
        st.markdown(f"**You:** {text}")
    else:
        st.markdown(f"**Bot:** {text}")

