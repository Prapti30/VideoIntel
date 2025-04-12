import streamlit as st
import requests
from urllib.parse import urlencode, urlparse, parse_qs
import re

# --- CONFIG for Microsoft Azure AD OAuth ---
client_id = "cfa7fc3c-0a7c-4a45-aa87-f993ed70fd9e"        # <-- PUT your real client_id
client_secret = "uAH8Q~RMG~Dy1hRt1dx6IOhtj39j-gmXImKlTaGr" # <-- PUT your real client_secret
tenant_id = "94a76bb1-611b-4eb5-aee5-e312381c32cb"         # <-- PUT your real tenant_id
redirect_uri = "https://video-intel-cg.streamlit.app/"  # <-- Must match exactly in Azure

authorize_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
scope = "openid profile User.Read offline_access"

# --- FUNCTIONS ---
def build_auth_url():
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "response_mode": "query",
        "scope": scope,
        "state": "12345"  # Random state value
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

def get_organization_name(email):
    domain = email.split('@')[-1]
    organization = domain.split('.')[0]
    return organization

def correct_sharepoint_link(user_link, organization_name):
    pattern = rf"https://{organization_name}\.sharepoint\.com/sites/.*"
    if re.match(pattern, user_link):
        return user_link
    else:
        parsed_url = re.sub(r"https://.*\.sharepoint\.com", f"https://{organization_name}.sharepoint.com", user_link)
        return parsed_url

def extract_sharepoint_ids(sharepoint_url):
    parsed_url = urlparse(sharepoint_url)
    path_parts = parsed_url.path.split('/')
    if len(path_parts) > 2:
        site_id = path_parts[2]  # site name
        file_id = path_parts[-1]  # file or item
        return site_id, file_id
    return None, None

# --- MAIN APP ---
def main():
    st.set_page_config(page_title="SharePoint Video Access via Microsoft SSO", page_icon="🎥")
    st.title("🎥 Access SharePoint Videos with Microsoft Office Login")

    query_params = st.experimental_get_query_params()

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

                organization_name = get_organization_name(user_email)
                st.info(f"Detected Organization: **{organization_name}**")

                st.subheader("🔗 Enter Your SharePoint Video Link")
                user_link = st.text_input("Paste your SharePoint video link here:")

                if user_link:
                    corrected_link = correct_sharepoint_link(user_link, organization_name)
                    st.write(f"✅ Corrected SharePoint Link: {corrected_link}")

                    site_id, file_id = extract_sharepoint_ids(corrected_link)
                    st.write(f"Site ID: {site_id}")
                    st.write(f"File ID: {file_id}")
            else:
                st.error("Failed to retrieve user info.")
        else:
            st.error("No access token found. Authorization failed.")

if __name__ == "__main__":
    main()
