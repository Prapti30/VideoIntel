import requests
import streamlit as st

def video_data(video_url):
    if video_url:
        token = st.session_state.access_token
    # Convert SharePoint URL to Microsoft Graph API URL
        sharepoint_path = video_url.split("/personal/")[1]
        user_name, relative_path = sharepoint_path.split("/", 1)

        site_resp = requests.get(
        f"https://graph.microsoft.com/v1.0/sites/root:/sites/{user_name}",
        headers={"Authorization": f"Bearer {token}"}
    )
        site_id = site_resp.json().get("id")

        item_resp = requests.get(
        f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:/{relative_path}",
        headers={"Authorization": f"Bearer {token}"}
        )
        item_data = item_resp.json()
        item_id = item_data.get("id")

        content_resp = requests.get(
        f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{item_id}/content",
        headers={"Authorization": f"Bearer {token}"},
        stream=True
        )
        with open("temp_video.mp4", "wb") as f:
            for chunk in content_resp.iter_content(chunk_size=8192):
                f.write(chunk)

        st.video("temp_video.mp4")

if __name__ == "__main__":
    st.title("Microsoft Video Viewer")
    video_url = st.text_input("Paste SharePoint Video URL")
    video_data(video_url)