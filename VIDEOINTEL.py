import streamlit as st
import requests
from urllib.parse import urlencode

# --- CONFIG ---
client_id = "cfa7fc3c-0a7c-4a45-aa87-f993ed70fd9e"
client_secret = "uAH8Q~RMG~Dy1hRt1dx6IOhtj39j-gmXImKlTaGr"
tenant_id = "94a76bb1-611b-4eb5-aee5-e312381c32cb"
redirect_uri = "https://video-intel-cg.streamlit.app/"
sharepoint_file_url = "https://cygrp-my.sharepoint.com/:v:/r/personal/sanchit_arora_cginfinity_com/Documents/Microsoft%20Teams%20Chat%20Files/DOCINTEL.MP4?csf=1&web=1&e=5AjE0k"

# Azure endpoints
authorize_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
scope = "openid profile User.Read Files.Read.All Sites.Read.All offline_access"

# --- HELPER FUNCTIONS ---
def build_auth_url():
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": "12345"
    }
    return f"{authorize_url}?{urlencode(params)}"

def get_token(code):
    data = {
        "client_id": client_id,
        "scope": scope,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "client_secret": client_secret,
    }
    response = requests.post(token_url, data=data)
    return response.json() if response.status_code == 200 else None

def get_file_content(access_token, file_url):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(file_url, headers=headers)
    if response.status_code == 200:
        return response.content
    else:
        st.error(f"Failed to fetch file: {response.text}")
        return None

# --- MAIN APP ---
def main():
    st.set_page_config(page_title="SharePoint File Viewer", page_icon="📄")
    st.title("📄 View SharePoint File")

    query_params = st.experimental_get_query_params()
    
    if "code" not in query_params:
        st.markdown(f"[🔐 Login with Microsoft]({build_auth_url()})", unsafe_allow_html=True)
    else:
        code = query_params["code"][0]
        token_data = get_token(code)
        
        if token_data and "access_token" in token_data:
            access_token = token_data["access_token"]
            
            # Fetch file content
            file_content = get_file_content(access_token, sharepoint_file_url)
            
            if file_content:
                st.subheader("🎬 DOCINTEL.MP4")
                st.video(file_content)
            else:
                st.error("⚠️ Unable to display the file.")
                
        else:
            st.error("⚠️ Login failed. Please try again.")

if __name__ == "__main__":
    main()
