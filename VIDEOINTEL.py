import streamlit as st
from msal_streamlit_authentication import msal_authentication

# Configuration for Microsoft Azure AD OAuth
client_id = "cfa7fc3c-0a7c-4a45-aa87-f993ed70fd9e"  # Azure AD Application Client ID
tenant_id = "94a76bb1-611b-4eb5-aee5-e312381c32cb"  # Azure AD Tenant ID
redirect_uri = "https://video-intel-cg.streamlit.app/"  # Ensure this matches your Azure configuration

authority = f"https://login.microsoftonline.com/{tenant_id}"

# Define scopes for access permissions
scopes = ["User.Read", "Sites.Read.All"]

def main():
    st.title("Azure AD SSO Integration")
    
    # Use msal_streamlit_authentication for SSO
    login_token = msal_authentication(
        auth={
            "clientId": client_id,
            "authority": authority,
            "redirectUri": redirect_uri,
            "postLogoutRedirectUri": redirect_uri,
        },
        cache={
            "cacheLocation": "sessionStorage",
            "storeAuthStateInCookie": False,
        },
        login_request={
            "scopes": scopes,
        },
        logout_request={},
        login_button_text="Login with Microsoft",
        logout_button_text="Logout",
        key=1,  # Optional, if multiple instances are needed
    )

    # Display user information upon successful login
    if login_token:
        st.success("Login successful!")
        st.write("Received login token:", login_token)

        # Add functionality to handle video data if required
        video_url = st.text_input("Paste SharePoint Video URL")
        if video_url:
            st.write(f"Video URL: {video_url}")
            # Implement video handling logic here

if __name__ == "__main__":
    main()
