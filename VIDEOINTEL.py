import streamlit as st
import requests
from urllib.parse import urlencode
import json
import msal
from streamlit_extras.switch_page_button import switch_page

# --- CONFIG for Microsoft Azure AD OAuth ---
client_id = "cfa7fc3c-0a7c-4a45-aa87-f993ed70fd9e"  # Azure AD Application Client ID
client_credential = "uAH8Q~RMG~Dy1hRt1dx6IOhtj39j-gmXImKlTaGr"  # Azure AD Application Client Secret
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



def main():
    # st.button("test")
    access_token = None
    query_params = st.experimental_get_query_params()
    app = msal.ConfidentialClientApplication (
        client_id=client_id,
        client_credential=client_credential,
        authority=f"https://login.microsoftonline.com/{tenant_id}"
        )
    if "code" in query_params:
        code = query_params["code"][0]
        

        
        # Now, exchange the authorization code for an access token
        result = app.acquire_token_by_authorization_code(
            code,
            scopes=["User.Read", "Sites.Read.All"],
            redirect_uri=redirect_uri
        )

        # If token is received, store and use it
        if "access_token" in result:
            st.session_state.access_token = result["access_token"]
            st.experimental_set_query_params()
            switch_page("video")
              # Clear the URL query parameters
        else:
            st.write("Error: Could not acquire token.")
            st.write(result)
    
    #     credential = ClientSecretCredential(
    #     tenant_id=tenant_id,
    #     client_id=client_id,
    #     client_secret=client_secret
    # )
    # token = credential.get_token("https://graph.microsoft.com/.default")
    # access_token = token.token
        # app = msal.PublicClientApplication(
        # client_id=client_id,
        # authority=f"https://login.microsoftonline.com/{tenant_id}"
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

        #     if "access_token" in result:
        #         token = result["access_token"]
        #         st.success("Login successful!")

        #         if token is not None:
        #             st.title("Microsoft Video Viewer")
        #             video_url = st.text_input("Paste SharePoint Video URL")
        #             video_data(video_url,token)
        #     else:
        #         st.write("Failed to authenticate")
        # else:
        #     # Redirect user for authentication
        #     auth_url = app.get_authorization_request_url(scopes=["User.Read", "Sites.Read.All"], redirect_uri=redirect_uri)
        #     st.write(f"Please authenticate by clicking [here]({auth_url})")

if __name__ == "__main__":
    main()
