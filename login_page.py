import streamlit as st
import requests
from urllib.parse import urlencode
import json
import msal



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

if st.button("Login with Microsoft"):
    #     credential = ClientSecretCredential(
    #     tenant_id=tenant_id,
    #     client_id=client_id,
    #     client_secret=client_secret
    # )
    # token = credential.get_token("https://graph.microsoft.com/.default")
    # access_token = token.token
        app = msal.PublicClientApplication(
        client_id=client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}"
        )

        # Check if user already logged in
        query_params = st.experimental_get_query_params()
        if "code" in query_params:
            code = query_params["code"][0]

            result = app.acquire_token_by_authorization_code(
                code,
                scopes=["User.Read", "Sites.Read.All"],
                redirect_uri=redirect_uri
            )

            if "access_token" in result:
                token = result["access_token"]
                st.success("Login successful!")
            else:
                st.write("Failed to authenticate")
        else:
            # Redirect user for authentication
            auth_url = app.get_authorization_request_url(scopes=["User.Read", "Sites.Read.All"], redirect_uri=redirect_uri)
            st.write(f"Please authenticate by clicking [here]({auth_url})")