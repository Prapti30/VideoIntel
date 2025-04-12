import requests
import streamlit as st

def video_data(video_url, token):
    if video_url and token:
        # Extract site and file path from the SharePoint URL
        sharepoint_path = video_url.split("/personal/")[1]
        user_name, relative_path = sharepoint_path.split("/", 1)
        st.write(sharepoint_path)
        st.write(user_name)

        # Get site ID using Microsoft Graph API
        site_resp = requests.get(
            f"https://graph.microsoft.com/v1.0/sites/root:/sites/{user_name}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if site_resp.status_code != 200:
            st.error("Failed to retrieve site information.")
            return
        
        site_id = site_resp.json().get("id")
        st.write(site_id)

        # Get file ID using Microsoft Graph API
        item_resp = requests.get(
            f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:/{relative_path}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if item_resp.status_code != 200:
            st.error("Failed to retrieve file information.")
            return
        
        item_data = item_resp.json()
        item_id = item_data.get("id")
        st.write(item_data)
        st.write(item_id)
        # Download the file content
        content_resp = requests.get(
            f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{item_id}/content",
            headers={"Authorization": f"Bearer {token}"},
            stream=True
        )
        st.write(content_resp)
        
        if content_resp.status_code == 200:
            with open("temp_video.mp4", "wb") as video_file:
                for chunk in content_resp.iter_content(chunk_size=8192):
                    video_file.write(chunk)
            st.success("Video downloaded successfully!")
            st.video("temp_video.mp4")
        else:
            st.error("Failed to download video.")

if __name__ == "__main__":
    st.title("Microsoft Video Viewer")
    video_url = st.text_input("Paste SharePoint Video URL")
    video_data(video_url,st.session_state.access_token)