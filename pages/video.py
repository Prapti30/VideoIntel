import requests
import streamlit as st

def video_data(video_url, token):
    if video_url and token:
        try:
            # Extract user email from the SharePoint URL
            sharepoint_path = video_url.split("/personal/")[1]
            user_name, relative_path = sharepoint_path.split("/", 1)
            user_name = user_name.split("_",".")
            user_email = user_name.replace(".cginfinity.com","@cginfinity.com")
            st.write(user_email) # Convert sanchit_arora_cginfinity_com → sanchit@arora.cginfinity.com

            # Get site ID for the user"s OneDrive
            site_resp = requests.get(
                f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root",  # Use OneDrive endpoint
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if site_resp.status_code != 200:
                st.error(f"Failed to retrieve OneDrive site. Error: {site_resp.json()}")
                return

            # Extract drive ID from the response
            drive_id = site_resp.json().get("parentReference", {}).get("driveId")
            if not drive_id:
                st.error("Could not retrieve drive ID.")
                return

            # Extract file path from the URL
            file_path = "/".join(video_url.split("/personal/")[1].split("/")[3:])  # Skip user/email/Documents/...

            # Get file metadata using the drive ID and file path
            item_resp = requests.get(
                f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{file_path}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if item_resp.status_code != 200:
                st.error(f"File not found. Error: {item_resp.json()}")
                return

            item_id = item_resp.json().get("id")
            
            # Download the file
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
    video_data(video_url,st.session_state.access_token)