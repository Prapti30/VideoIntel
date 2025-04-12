import streamlit as st
import requests
from urllib.parse import urlencode, urlparse
import re

# --- CONFIG for Microsoft Azure AD OAuth ---
client_id = "cfa7fc3c-0a7c-4a45-aa87-f993ed70fd9e"
client_secret = "uAH8Q~RMG~Dy1hRt1dx6IOhtj39j-gmXImKlTaGr"
tenant_id = "94a76bb1-611b-4eb5-aee5-e312381c32cb"
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

def get_site_id(access_token, hostname, site_path):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    endpoint = f"https://graph.microsoft.com/v1.0/sites/{hostname}:/sites/{site_path}"
    response = requests.get(endpoint, headers=headers)
    if response.status_code == 200:
        return response.json().get('id')
    else:
        st.error(f"Failed to get Site ID: {response.text}")
        return None

def list_drive_items(access_token, site_id):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    endpoint = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root/children"
    response = requests.get(endpoint, headers=headers)
    if response.status_code == 200:
        return response.json().get('value', [])
    else:
        st.error(f"Failed to get SharePoint files: {response.text}")
        return []

# --- MAIN APP ---
def main():
    st.set_page_config(page_title="SharePoint Files Browser", page_icon="🗂️")
    st.title("🗂️ Browse Your SharePoint Files (No Links)")

    query_params =  st.query_params()

    if "code" not in query_params:
        auth_url = build_auth_url()
        st.markdown(f"[Login with Microsoft]({auth_url})", unsafe_allow_html=True)
    else:
        code = query_params["code"][0]
        token_response = get_token_from_code(code)

        if token_response and "access_token" in token_response:
            access_token = token_response["access_token"]
            user_info = get_user_info(access_token)

            if user_info:
                user_email = user_info.get("mail") or user_info.get("userPrincipalName")
                st.success(f"Logged in as: {user_email}")

                st.subheader("📁 Enter SharePoint Site Details")

                hostname = st.text_input("Enter SharePoint Hostname (example: yourcompany.sharepoint.com)", "")
                site_path = st.text_input("Enter Site Name (example: YourSiteName)", "")

                if hostname and site_path:
                    site_id = get_site_id(access_token, hostname, site_path)

                    if site_id:
                        st.success(f"Found Site ID: {site_id}")
                        st.subheader("📂 Files and Folders:")

                        drive_items = list_drive_items(access_token, site_id)

                        if drive_items:
                            for item in drive_items:
                                if item.get('folder'):
                                    st.write(f"📁 {item['name']}")
                                else:
                                    st.write(f"📄 {item['name']}")
                        else:
                            st.info("No files or folders found.")
        else:
            st.error("Login failed. Please try again.")

if __name__ == "__main__":
    main()
