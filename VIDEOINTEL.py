import streamlit as st
import requests
from urllib.parse import urlencode

# --- CONFIG ---
client_id = "cfa7fc3c-0a7c-4a45-aa87-f993ed70fd9e"
client_secret = "uAH8Q~RMG~Dy1hRt1dx6IOhtj39j-gmXImKlTaGr"
tenant_id = "94a76bb1-611b-4eb5-aee5-e312381c32cb"
redirect_uri = "https://video-intel-cg.streamlit.app/"

# Graph API endpoint for the file
graph_file_endpoint = (
    "https://graph.microsoft.com/v1.0/users/sanchit_arora_cginfinity_com/"
    "drive/root:/Microsoft Teams Chat Files/DOCINTEL.MP4:/content"
)

# Azure endpoints
authorize_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
scope = "Files.Read.All Sites.Read.All User.Read.All"

def build_auth_url():
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": scope,
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

def get_file_content(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(graph_file_endpoint, headers=headers)
    if response.status_code == 200:
        return response.content
    st.error(f"401 UNAUTHORIZED - Verify: 1) API Permissions 2) File URL 3) App Registration")
    return None

def main():
    st.set_page_config(page_title="SharePoint File Viewer", page_icon="📄")
    query_params = st.experimental_get_query_params()
    
    if "code" not in query_params:
        st.markdown(f"[🔐 Login with Microsoft]({build_auth_url()})", unsafe_allow_html=True)
    else:
        token_data = get_token(query_params["code"][0])
        if token_data and "access_token" in token_data:
            file_content = get_file_content(token_data["access_token"])
            if file_content:
                st.video(file_content)
        else:
            st.error("Authentication failed")

if __name__ == "__main__":
    main()
