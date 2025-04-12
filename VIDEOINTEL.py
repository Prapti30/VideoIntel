import streamlit as st
import requests
import urllib
import json

# Your app registration details
CLIENT_ID = "cfa7fc3c-0a7c-4a45-aa87-f993ed70fd9e"
CLIENT_SECRET = "uAH8Q~RMG~Dy1hRt1dx6IOhtj39j-gmXImKlTaGr"
REDIRECT_URI = "https://video-intel-cg.streamlit.app/"  # Same as your app's redirect URI
AUTHORITY = "https://login.microsoftonline.com/common"
AUTH_ENDPOINT = "/oauth2/v2.0/authorize"
TOKEN_ENDPOINT = "/oauth2/v2.0/token"
SCOPE = ["User.Read", "Sites.Read.All"]

def build_auth_url():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "response_mode": "query",
        "scope": " ".join(SCOPE),
    }
    request_url = f"{AUTHORITY}{AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"
    return request_url

def get_token_from_code(code):
    post_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": " ".join(SCOPE),
    }
    response = requests.post(f"{AUTHORITY}{TOKEN_ENDPOINT}", data=post_data)
    return response.json()

def get_user_info(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers)
    return response.json()

def get_organization_name(user_email):
    # Dummy logic - you can replace this based on your org's naming
    if "yourorg.com" in user_email:
        return "Your Organization"
    else:
        return "External User"

def correct_sharepoint_link(user_link, organization_name):
    # Dummy correction logic
    if "sharing" in user_link:
        corrected_link = user_link.split("?")[0]
        return corrected_link
    else:
        return user_link

def extract_sharepoint_ids(corrected_link):
    # Dummy extract logic (You need to customize this)
    site_id = "site_id_placeholder"
    file_id = "file_id_placeholder"
    return site_id, file_id

def main():
    st.set_page_config(page_title="SharePoint Video Access via Microsoft SSO", page_icon="🎥")
    st.title("🎥 Access SharePoint Videos with Microsoft Office Login")

    query_params = st.experimental_get_query_params()

    # Initialize session state
    if "access_token" not in st.session_state:
        st.session_state.access_token = None

    # If access token is not already stored
    if st.session_state.access_token is None:
        if "code" not in query_params:
            auth_url = build_auth_url()
            st.markdown(f"[Login with Microsoft]({auth_url})", unsafe_allow_html=True)
        else:
            code = query_params["code"][0]
            token_response = get_token_from_code(code)

            if "access_token" in token_response:
                st.session_state.access_token = token_response["access_token"]
            else:
                st.error(f"Failed to get Access Token. Details: {token_response}")
                return  # Stop here if token failed

    # If access token is available
    if st.session_state.access_token:
        access_token = st.session_state.access_token
        user_info = get_user_info(access_token)
        user_email = user_info.get("mail") or user_info.get("userPrincipalName")
        st.success(f"Logged in as: {user_email}")

        organization_name = get_organization_name(user_email)
        st.info(f"Detected Organization: **{organization_name}**")

        st.subheader("🔗 Enter Your SharePoint Video Link")
        user_link = st.text_input("Paste your SharePoint video link here:")

        if user_link:
            corrected_link = correct_sharepoint_link(user_link, organization_name)
            st.write(f"✅ Corrected SharePoint Link: {corrected_link}")

            # Extract Site ID and File ID from the SharePoint URL
            site_id, file_id = extract_sharepoint_ids(corrected_link)
            st.write(f"Site ID: {site_id}")
            st.write(f"File ID: {file_id}")

if __name__ == "__main__":
    main()
