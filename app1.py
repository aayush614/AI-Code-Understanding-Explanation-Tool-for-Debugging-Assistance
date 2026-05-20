import streamlit as st
import google.genai as genai
from google.genai import types
from pydantic import BaseModel, Field
import pymongo
from streamlit_authenticator import Hasher
from datetime import datetime

st.set_page_config(page_title="AI code understanding", layout="wide", initial_sidebar_state="expanded")

# Connect to MongoDB
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["ai_debugger_db"]
users_collection = db["users"]
users_collection.create_index("username", unique=True)
users_collection.create_index("email", unique=True)

class CodeAnalysisSchema(BaseModel):
    summary: str = Field(description="A brief high-level overview of what the code does.")
    complexity: str = Field(description="Time and Space complexity in Big O notation (e.g., O(N) time, O(1) space).")
    explanation_steps: list[str] = Field(description="Step-by-step breakdown of the logic.")
    bugs_found: list[str] = Field(description="List of bugs, logical flaws, or edge-case handling issues.")
    fixed_code: str = Field(description="The complete, fully optimized and corrected version of the code.")


USERS = {
    "admin": {"password": "admin123", "name": "Project Supervisor"},
    "student": {"password": "password123", "name": "Student User"},
}


def register_user() -> None:
    """Register a new user in MongoDB."""
    st.title("Register")
    st.caption("Create a new account for the AI code analysis tool.")

    with st.form("register_form", clear_on_submit=True):
        name = st.text_input("Full name")
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Register", use_container_width=True)

    if not submitted:
        return

    username = username.strip().lower()
    email = email.strip().lower()
    name = name.strip()

    if not username or not name or not email or not password:
        st.error("Please fill in all fields.")
        return
    if password != confirm_password:
        st.error("Passwords do not match.")
        return
    if len(password) < 6:
        st.error("Password must be at least 6 characters long.")
        return
    if users_collection.find_one({"username": username}):
        st.error("Username already exists.")
        return
    if users_collection.find_one({"email": email}):
        st.error("Email is already registered.")
        return

    users_collection.insert_one(
        {
            "username": username,
            "name": name,
            "email": email,
            "password": Hasher.hash(password),
            "created_at": datetime.utcnow(),
        }
    )
    st.success("User registered successfully. Go to the Login tab to sign in.")


def render_login() -> None:
    """Show a login form and store successful auth in Streamlit session state."""
    st.title("Login")
    st.caption("Enter your credentials to access the AI code analysis tool.")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)

    if not submitted:
        return

    username = username.strip().lower()
    mongo_user = users_collection.find_one({"username": username})
    local_user = USERS.get(username)

    if mongo_user and Hasher.check_pw(password, mongo_user["password"]):
        st.session_state.authenticated = True
        st.session_state.username = username
        st.session_state.name = mongo_user.get("name", username)
        st.rerun()

    if local_user and password == local_user["password"]:
        st.session_state.authenticated = True
        st.session_state.username = username
        st.session_state.name = local_user["name"]
        st.rerun()

    st.error("Login failed. Please check your username and password.")

# -------------------------------------------------------------
# 2. UI SETUP: IDE Layout Configuration
# -------------------------------------------------------------
if not st.session_state.get("authenticated"):
    login_tab, register_tab = st.tabs(["Login", "Register"])
    with login_tab:
        render_login()
    with register_tab:
        register_user()
    st.stop()

st.title("AI Code Understanding & Explanation Tool for Debugging Assistance.")
st.caption(f"Logged in as: {st.session_state.name} ({st.session_state.username})")
st.markdown("---")

# Secure Token Management via Sidebar
with st.sidebar:
    if st.button("Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.pop("username", None)
        st.session_state.pop("name", None)
        st.rerun()
    st.markdown("---")
    st.subheader("Choose Your Model & API Key")
    model_choice = st.selectbox("LLM Engine", ["gemini-2.5-pro", "gemini-2.5-flash"])
    if model_choice == "gemini-2.5-pro":
        api_key = st.text_input("Enter API Key For Gemini Pro", type="password")
        st.caption("Note: Gemini Pro requires a valid API key with billing enabled, while Gemini Flash is free-tier and doesn't require authentication.")
    else:
        api_key = "AIzaSyDO3EDH-Ch1LW1lkdtVhQVCOmH2Yeb3QBg"  # Hardcoded for flash model as it's free-tier and doesn't require user input
    # st.subheader("🔑 Authentication")
    # api_key = 'AIzaSyDO3EDH-Ch1LW1lkdtVhQVCOmH2Yeb3QBg'
    
    # st.subheader("⚙️ Model Configuration")
    # # Using the premium reasoning model for deep debugging tasks
    # model_choice = st.selectbox("LLM Engine", ["gemini-2.5-pro", "gemini-2.5-flash"])
    st.caption("Pro Tip: Use 'pro' for deep logical debugging; use 'flash' for instant responses.")
    

# Dashboard Split Workspace
col_editor, col_analytics = st.columns([1.1, 1], gap="large")

with col_editor:
    st.subheader("💻 Source Code Editor")
    lang = st.selectbox("Language Mapping", ["python", "javascript", "cpp", "java"])
    
    # Text input area for production code
    raw_code = st.text_area("Paste code repository snippet here:", height=450, placeholder="# Write or paste code...")
    analyze_action = st.button("Run Static AI Analysis 🚀", use_container_width=True)

# -------------------------------------------------------------
# 3. CORE LOGIC: API Orchestration
# -------------------------------------------------------------
with col_analytics:
    st.subheader("📊 Engine Diagnostics")
    
    if analyze_action:
        if not api_key:
            st.error("Access Denied: Missing valid API credential strings in configurations.")
        elif not raw_code.strip():
            st.warning("Workspace Empty: Provide a valid code matrix to run evaluations.")
        else:
            try:
                # Initialize Google GenAI client instance
                client = genai.Client(api_key=api_key)
                
                with st.spinner("Compiling insights and mapping structure..."):
                    
                    # Requesting structured JSON via GenerateContentConfig
                    raw_response = client.models.generate_content(
                        model=model_choice,
                        contents=f"Analyze this {lang} codebase snippet:\n\n{raw_code}",
                        config=types.GenerateContentConfig(
                            system_instruction=(
                                "You are a principal software engineer. Analyze the code provided by the user. "
                                "Be critical about performance, architectural flaws, and formatting problems."
                            ),
                            # This converts the raw model output into a valid Python/JSON Object seamlessly
                            response_mime_type="application/json",
                            response_schema=CodeAnalysisSchema,
                            temperature=0.1 # Low temperature ensures strict logical correctness
                        ),
                    )
                    
                    # Parse out the structured result 
                    # (The client automatically validates it against our Pydantic Schema)
                    data: CodeAnalysisSchema = raw_response.parsed
                
                # Create Clean UI Tab wrappers for an Enterprise Look
                tab_summary, tab_debug, tab_fix = st.tabs(["📋 Logic Breakdowns", "🐛 Bug Diagnostics", "🛠️ Refactored Variant"])
                
                with tab_summary:
                    st.markdown("### Executive Summary")
                    st.info(data.summary)
                    st.markdown(f"**Algorithmic Efficiency:** `{data.complexity}`")
                    
                    st.markdown("### Process Walkthrough")
                    for iteration, step in enumerate(data.explanation_steps, 1):
                        st.write(f"**{iteration}.** {step}")
                        
                with tab_debug:
                    st.markdown("### Detected Structural Vulnerabilities")
                    if data.bugs_found:
                        for issue in data.bugs_found:
                            st.markdown(f"🔴 {issue}")
                    else:
                        st.success("Analysis complete: Zero immediate critical defects found.")
                        
                with tab_fix:
                    st.markdown("### Optimized Baseline Production Patch")
                    st.code(data.fixed_code, language=lang)
                    st.caption("Review internal variables prior to applying to staging/production clusters.")
                    
            except Exception as system_fault:
                st.error(f"Runtime Exception Intercepted: {system_fault}")
