import streamlit as st
import requests
from urllib.parse import urlencode
import json
import msal
from azure.identity import ClientSecretCredential

# --- CONFIG for Microsoft Azure AD OAuth ---
client_id = "cfa7fc3c-0a7c-4a45-aa87-f993ed70fd9e"  # Azure AD Application Client ID
client_secret = "uAH8Q~RMG~Dy1hRt1dx6IOhtj39j-gmXImKlTaGr"  # Azure AD Application Client Secret
tenant_id = "94a76bb1-611b-4eb5-aee5-e312381c32cb"  # Azure AD Tenant ID
redirect_uri = "https://video-intel-cg.streamlit.app/"  # Make sure this matches in Azure

# authorize_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
# token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
# scope = "openid profile User.Read Files.Read.All Sites.Read.All offline_access"
scope = ["User.Read", "Sites.Read.All"]
authority = f"https://login.microsoftonline.com/{tenant_id}"

def log_screen():
    if st.button("Login with Microsoft"):
        app = msal.PublicClientApplication(client_id, authority=authority)
        result = app.acquire_token_interactive(scopes=scope)
        if "access_token" in result:
            token = result["access_token"]
            st.success("Login successful!")

def video_data(video_url,token):
    if video_url and token:
    # Convert SharePoint URL to Microsoft Graph API URL
        sharepoint_url = video_url.split('/sites/')[1]
        site_name, relative_path = sharepoint_url.split('/', 1)

        site_resp = requests.get(
        f"https://graph.microsoft.com/v1.0/sites/root:/sites/{site_name}",
        headers={"Authorization": f"Bearer {token}"}
        )
        site_id = site_resp.json().get("id")

        item_resp = requests.get(
        f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:/{relative_path}",
        headers={"Authorization": f"Bearer {token}"}
        )
        item_data = item_resp.json()
        item_id = item_data.get("id")

        content_resp = requests.get(
        f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{item_id}/content",
        headers={"Authorization": f"Bearer {token}"},
        stream=True
        )
        with open("temp_video.mp4", "wb") as f:
            for chunk in content_resp.iter_content(chunk_size=8192):
                f.write(chunk)

        st.video("temp_video.mp4")

    return

def main():
    if st.button("Login with Microsoft"):
        credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret
    )
    token = credential.get_token("https://graph.microsoft.com/.default")
    access_token = token.token
    #     app = msal.PublicClientApplication(
    #     client_id=client_id,
    #     client_credential=client_credential,
    #     authority=f"https://login.microsoftonline.com/{tenant_id}"
    # )

    # # Check if user already logged in
    # query_params = st.experimental_get_query_params()
    # if "code" in query_params:
    #     code = query_params["code"][0]

    #     result = app.acquire_token_by_authorization_code(
    #         code,
    #         scopes=["User.Read", "Sites.Read.All"],
    #         redirect_uri=redirect_uri
    #     )

        # if "access_token" in result:
        #     token = result["access_token"]
        #     st.success("Login successful!")

    if access_token is not None:
        st.title("Microsoft Video Viewer")
        video_url = st.text_input("Paste SharePoint Video URL")
        video_data(video_url,access_token)

if __name__ == "__main__":
    main()
