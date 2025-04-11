# auth.py
import streamlit as st
import msal
import uuid

CLIENT_ID = "cfa7fc3c-0a7c-4a45-aa87-f993ed70fd9e"
TENANT_ID = "94a76bb1-611b-4eb5-aee5-e312381c32cb"
CLIENT_SECRET = "uAH8Q~RMG~Dy1hRt1dx6IOhtj39j-gmXImKlTaGr"  # optional if confidential client
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_URI = "https://video-intel-cg.streamlit.app/"  # or your deployed URL
SCOPE = ["User.Read"]

def build_msal_app(cache=None):
    return msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
        token_cache=cache
    )

def get_auth_url(app):
    return app.get_authorization_request_url(
        scopes=SCOPE,
        state=str(uuid.uuid4()),
        redirect_uri=REDIRECT_URI
    )

def main():
    st.title("Azure SSO Login Example")

    cache = msal.SerializableTokenCache()

    app = build_msal_app(cache)

    # Step 1: Get login URL
    login_url = get_auth_url(app)

    # Step 2: Display Login button
    if st.button("Login with Microsoft"):
        st.markdown(f"[Click here to login]({login_url})")

    # Step 3: Handle Redirect (after login)
    query_params = st.experimental_get_query_params()
    if "code" in query_params:
        code = query_params["code"][0]

        result = app.acquire_token_by_authorization_code(
            code,
            scopes=SCOPE,
            redirect_uri=REDIRECT_URI
        )

        if "access_token" in result:
            st.success("Login successful!")
            st.write("User Info:", result)
        else:
            st.error("Login failed.")
            st.json(result)

if __name__ == "__main__":
    main()
