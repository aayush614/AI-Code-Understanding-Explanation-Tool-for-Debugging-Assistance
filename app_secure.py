import streamlit as st
import streamlit_authenticator as stauth
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# 1. SETUP LOGIN CREDENTIALS 
# In a real app, this would live in a secure database or config file.
# Passwords are hashed securely using streamlit_authenticator's Hasher.
hashed_passwords = stauth.Hasher.hash_list(["admin123", "password123"])
admin_pw_hash, student_pw_hash = hashed_passwords

credentials = {
    "usernames": {
        "admin": {
            "name": "Project Supervisor",
            "password": admin_pw_hash,
            "email": "supervisor@college.edu"
        },
        "student": {
            "name": "Aditya Tiwari",
            "password": student_pw_hash,
            "email": "student@college.edu"
        }
    }
}

# Initialize the Authenticator Module
authenticator = stauth.Authenticate(
    credentials=credentials,
    cookie_name="devai_session_cookie",
    cookie_key="signature_protection_key_123",  # Random signature string
    cookie_expiry_days=1,
    auto_hash=False
)

# 2. RENDER LOGIN INTERFACE
# This places a clean, native login portal on the center screen
name, authentication_status, username = authenticator.login(location='main')

# Streamlit-authenticator stores login state in session_state.
authentication_status = st.session_state.get("authentication_status", authentication_status)
name = st.session_state.get("name", name)
username = st.session_state.get("username", username)

if authentication_status is False:
    st.error("Authentication Failed: Username/password combination is incorrect.")

elif authentication_status is None:
    st.warning("Access Restricted: Please enter institutional credentials to proceed.")

elif authentication_status:
    # -------------------------------------------------------------
    # WELCOME / SECURE APPLICATION CONTENT
    # Everything inside this 'if' block is protected and hidden from guests.
    # -------------------------------------------------------------
    
    # Header area featuring a logout element in the sidebar
    with st.sidebar:
        st.write(f"🌐 Logged in as: **{name}**")
        authenticator.logout("Terminate Session 🔓", location="sidebar")
        st.markdown("---")
        
        # API Token Configuration
        api_key = st.text_input("Enter Gemini API Key", type="password")
        model_choice = "gemini-2.5-flash"
        st.caption("Secure pipeline authorized.")

    # Main Tool Dashboard Logic
    st.title("🤖 DevAI Enterprise Workspace")
    st.subheader(f"Welcome back, Developer {name}!")
    st.markdown("---")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📝 Source Sandbox")
        language = st.selectbox("Language", ["Python", "Java", "C++", "JavaScript"])
        code_input = st.text_area("Input Matrix:", height=350, placeholder="def compute()...")
        analyze_button = st.button("Execute Static Analysis")

    with col2:
        st.subheader("💡 Engine Insights")
        if analyze_button:
            if not api_key:
                st.warning("Provide an authorized API key token strings in the sidebar.")
            elif not code_input.strip():
                st.error("Matrix Empty: Cannot run diagnostics on empty scripts.")
            else:
                try:
                    client = genai.Client(api_key=api_key)
                    with st.spinner("Compiling structural properties..."):
                        response = client.models.generate_content(
                            model=model_choice,
                            contents=f"Explain this {language} code step-by-step and fix flaws:\n\n{code_input}"
                        )
                        st.markdown(response.text)
                except Exception as e:
                    st.error(f"Runtime Exception: {e}")