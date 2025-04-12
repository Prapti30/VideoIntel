import streamlit as st
import requests
from urllib.parse import urlencode
import json

# --- CONFIG for Microsoft Azure AD OAuth ---
client_id = "cfa7fc3c-0a7c-4a45-aa87-f993ed70fd9e"  # Azure AD Application Client ID
client_secret = "uAH8Q~RMG~Dy1hRt1dx6IOhtj39j-gmXImKlTaGr"  # Azure AD Application Client Secret
tenant_id = "94a76bb1-611b-4eb5-aee5-e312381c32cb"  # Azure AD Tenant ID
redirect_uri = "https://video-intel-cg.streamlit.app/"  # Make sure this matches in Azure

authorize_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
scope = "openid profile User.Read Files.Read.All Sites.Read.All offline_access"

# --- FUNCTIONS ---
def build_auth_url():
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "response_mode": "query",
        "scope": scope,
        "state": "12345"
    }
    return f"{authorize_url}?{urlencode(params)}"

def get_token_from_code(code):
    data = {
        "client_id": client_id,
        "scope": scope,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "client_secret": client_secret,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response = requests.post(token_url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to get Access Token. Status Code: {response.status_code}, Details: {response.text}")
        return None

def get_user_info(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch user info: {response.text}")
        return None

# def get_video_folder_id(access_token, user_email):
#     headers = {
#         "Authorization": f"Bearer {access_token}"
#     }
#     # Replace with actual folder path for work videos
#     endpoint = f"https://graph.microsoft.com/v1.0/users/{user_email}/drives"
#     response = requests.get(endpoint, headers=headers)
#     if response.status_code == 200:
#         files = response.json().get('value', [])
#         return files
#     else:
#         st.error(f"Failed to fetch video folder: {response.text}")
#         return []

# --- MAIN APP ---
def main():
    video_url = st.text_input("Paste SharePoint Video URL")

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

if __name__ == "__main__":
    main()




