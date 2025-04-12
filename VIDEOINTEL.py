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
    video_url="https://cygrp-my.sharepoint.com/:v:/r/personal/sanchit_arora_cginfinity_com/Documents/Microsoft%20Teams%20Chat%20Files/DOCINTEL.MP4?csf=1&web=1&e=JJhwEf&nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJTdHJlYW1XZWJBcHAiLCJyZWZlcnJhbFZpZXciOiJTaGFyZURpYWxvZy1MaW5rIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXcifX0%3D&xsdata=MDV8MDJ8fDlhNjMwOWNkMjZlYzQyMTM3ZjAwMDhkZDc5ODJmYzAwfDk0YTc2YmIxNjExYjRlYjVhZWU1ZTMxMjM4MWMzMmNifDB8MHw2Mzg4MDAzMjU2MzcwNzg3ODR8VW5rbm93bnxWR1ZoYlhOVFpXTjFjbWwwZVZObGNuWnBZMlY4ZXlKV0lqb2lNQzR3TGpBd01EQWlMQ0pRSWpvaVYybHVNeklpTENKQlRpSTZJazkwYUdWeUlpd2lWMVFpT2pFeGZRPT18MXxMMk5vWVhSekx6RTVPbU00Wm1NNE5qVmlMV1V5WW1JdE5EQTNaUzFpTWpCa0xXUmhOR1ZsWlRWbU1HVmtObDltTWpBMU56VTFZeTAwTldFeExUUm1PR1l0T1RBeVpDMWhNakkxWldRNFkySTBZalpBZFc1eExtZGliQzV6Y0dGalpYTXZiV1Z6YzJGblpYTXZNVGMwTkRRek5UYzJNakV6TkE9PXw4MjI1MmJlNzBhOGU0YjMyMzA5MDA4ZGQ3OTgyZmMwMHw3ODIyYWMxMjI5MDI0NDExYjUxZDM3MGNlODFjMTA3Yg%3D%3D&sdata=ejhqTWs0WktaRk5RQ3VwUG5iRGFUL2g4MFh2TDVzQ1RSTHRyMmlOVTNWRT0%3D&ovuser=94a76bb1-611b-4eb5-aee5-e312381c32cb%2Cprapti.more%40cginfinity.com"
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




