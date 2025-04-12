import streamlit as st
import msal
import requests

# Config
CLIENT_ID = "cfa7fc3c-0a7c-4a45-aa87-f993ed70fd9e"
TENANT_ID = "94a76bb1-611b-4eb5-aee5-e312381c32cb"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_URI = "https://video-intel-cg.streamlit.app/"
SCOPE = ["User.Read", "Sites.Read.All"]

# Step 1: MSAL Auth
st.title("Microsoft Video Viewer")
video_url = st.text_input("Paste SharePoint Video URL")

if 'token' not in st.session_state:
    st.session_state.token = None

if st.button("Login with Microsoft"):
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
    result = app.acquire_token_interactive(scopes=SCOPE)
    if "access_token" in result:
        st.session_state.token = result["access_token"]
        st.success("Login successful!")

# Step 2: Fetch & Stream video
if video_url and st.session_state.token:
    # Convert SharePoint URL to Microsoft Graph API URL
    sharepoint_url = video_url.split('/sites/')[1]
    site_name, relative_path = sharepoint_url.split('/', 1)

    # Get site ID
    site_resp = requests.get(
        f"https://graph.microsoft.com/v1.0/sites/root:/sites/{site_name}",
        headers={"Authorization": f"Bearer {st.session_state.token}"}
    )
    site_id = site_resp.json().get("id")

    # Get item metadata
    item_resp = requests.get(
        f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:/{relative_path}",
        headers={"Authorization": f"Bearer {st.session_state.token}"}
    )
    item_data = item_resp.json()
    item_id = item_data.get("id")

    # Stream video content
    content_resp = requests.get(
        f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{item_id}/content",
        headers={"Authorization": f"Bearer {st.session_state.token}"},
        stream=True
    )

    with open("temp_video.mp4", "wb") as f:
        for chunk in content_resp.iter_content(chunk_size=8192):
            f.write(chunk)

    st.video("temp_video.mp4")
 