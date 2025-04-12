import streamlit as st
from msal_streamlit_authentication import msal_authentication

# Configuration for Microsoft Azure AD OAuth
client_id = "cfa7fc3c-0a7c-4a45-aa87-f993ed70fd9e"
tenant_id = "94a76bb1-611b-4eb5-aee5-e312381c32cb"
redirect_uri = "https://video-intel-cg.streamlit.app/"

authority = f"https://login.microsoftonline.com/{tenant_id}"
scopes = ["User.Read", "Sites.Read.All"]

def main():
    st.title("Azure AD SSO Integration")

    # DIRECTLY CALL msal_authentication without extra button
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
        key="1",
    )

    # Now if login is successful
    if login_token:
        st.success("Login successful! 🎉")
        
        # Show user's name
        user_name = login_token.get('account', {}).get('name', 'User')
        st.write(f"Hi, {user_name} 👋")

        # Optional: Video section
        video_url = st.text_input("Paste SharePoint Video URL")
        if video_url:
            st.write(f"Video URL: {video_url}")
            # Handle video logic here

if __name__ == "__main__":
    main()
