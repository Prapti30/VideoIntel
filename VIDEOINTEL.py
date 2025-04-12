import streamlit as st
import requests
from urllib.parse import urlencode, urlparse, parse_qs
import re

# --- CONFIG for Microsoft Azure AD OAuth ---
client_id = "cfa7fc3c-0a7c-4a45-aa87-f993ed70fd9e"
client_secret = "uAH8Q~RMG~Dy1hRt1dx6IOhtj39j-gmXImKlTaGr"
tenant_id = "94a76bb1-611b-4eb5-aee5-e312381c32cb"  # Your Azure AD Tenant ID
redirect_uri = "https://video-intel-cg.streamlit.app/"

authorize_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
scope = "https://graph.microsoft.com/.default"  # Updated scope for SharePoint access

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
    response = requests.post(token_url, data=data)
    return response.json()

def get_user_info(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers)
    return response.json()

def get_sharepoint_items(site_id, access_token):
    # Get all items in the site's document library
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    graph_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root/children"
    response = requests.get(graph_url, headers=headers)

    if response.status_code == 200:
        items = response.json().get('value', [])
        return items
    else:
        st.error("Failed to retrieve items from SharePoint.")
        return []

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
    # Assuming the URL is of the format "https://<organization>.sharepoint.com/sites/<site_name>/..."
    parsed_url = urlparse(sharepoint_url)
    path_parts = parsed_url.path.split('/')
    site_id = path_parts[2]  # Extract site_id from the URL
    file_id = path_parts[-1]  # Extract file_id from the URL
    return site_id, file_id

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
        access_token = token_response.get("access_token")

        if access_token:
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

                # List all items in the SharePoint site
                items = get_sharepoint_items(site_id, access_token)
                
                if items:
                    st.subheader("📂 SharePoint Files and Folders")
                    for item in items:
                        st.write(f"- **{item['name']}** (Type: {item['file']['mimeType'] if 'file' in item else 'Folder'})")
                        if 'file' in item:
                            st.markdown(f"[Download File]({item['@microsoft.graph.downloadUrl']})")
                else:
                    st.error("No items found in SharePoint.")

        else:
            st.error("Failed to get Access Token from Microsoft.")

if __name__ == "__main__":
    main()
