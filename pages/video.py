import requests
import streamlit as st

def download_and_play_video(video_url, token):
    try:
        # Extract user email and relative file path from SharePoint URL
        sharepoint_path = video_url.split("/personal/")[1]
        user_name, relative_path = sharepoint_path.split("/", 1)
        user_email = user_name.replace("_", ".").replace(".cginfinity.com", "@cginfinity.com")
        st.write(f"User Email: {user_email}")

        # Extract relative file path after "/Documents/"
        file_path = "/".join(relative_path.split("/")[1:])
        st.write(f"File Path: {file_path}")

        # Get user's OneDrive root folder
        site_resp = requests.get(
            f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root",
            headers={"Authorization": f"Bearer {token}"}
        )

        if site_resp.status_code != 200:
            st.error(f"Failed to retrieve OneDrive site. Error: {site_resp.json()}")
            return

        # Extract drive ID
        drive_id = site_resp.json().get("parentReference", {}).get("driveId")
        if not drive_id:
            st.error("Could not retrieve drive ID.")
            return

        # Get file metadata using drive ID and relative file path
        item_resp = requests.get(
            f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{file_path}",
            headers={"Authorization": f"Bearer {token}"}
        )

        if item_resp.status_code != 200:
            st.error(f"File not found. Error: {item_resp.json()}")
            return

        item_id = item_resp.json().get("id")
        st.write(f"Item ID: {item_id}")

        # Download the file content
        content_resp = requests.get(
            f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/content",
            headers={"Authorization": f"Bearer {token}"},
            stream=True
        )

        if content_resp.status_code == 200:
            with open("temp_video.mp4", "wb") as f:
                for chunk in content_resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            st.success("Video downloaded!")
            st.video("temp_video.mp4")
        else:
            st.error(f"Download failed. Status: {content_resp.status_code}")
    except Exception as e:
        st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    st.title("Microsoft Video Viewer")
    video_url = st.text_input("Paste SharePoint Video URL")
    token = st.session_state.get("access_token")  # Replace with actual token retrieval logic
    if video_url and token:
        download_and_play_video(video_url, token)
