import streamlit as st
from msal_streamlit_authentication import msal_authentication
import jwt  # To decode the token and extract user info

# Configuration for Microsoft Azure AD OAuth
client_id = "cfa7fc3c-0a7c-4a45-aa87-f993ed70fd9e"
tenant_id = "94a76bb1-611b-4eb5-aee5-e312381c32cb"
redirect_uri = "https://video-intel-cg.streamlit.app/"

authority = f"https://login.microsoftonline.com/{tenant_id}"

# Define scopes for access permissions
scopes = ["User.Read", "Sites.Read.All"]

def main():
    st.title("Azure AD SSO Integration")

    # Directly authenticate the user when they visit the page
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
        key="1",  # key must be a string
    )

    # If login is successful
    if login_token:
        st.success("Login successful!")

        # Decode the Access Token to get user's information
        try:
            decoded_token = jwt.decode(login_token["idToken"], options={"verify_signature": False})
            username = decoded_token.get("name", "User")  # You can also use "preferred_username" for email
            st.write(f"Hi, {username} 👋")
        except Exception as e:
            st.error(f"Error decoding token: {e}")

        # Additional functionality
        video_url = st.text_input("Paste SharePoint Video URL")
        if video_url:
            st.write(f"Video URL: {video_url}")

if __name__ == "__main__":
    main()
