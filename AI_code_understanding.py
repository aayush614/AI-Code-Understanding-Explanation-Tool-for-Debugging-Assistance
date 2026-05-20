import streamlit as st
import google.genai as genai
from google.genai import types
from pydantic import BaseModel, Field
import pymongo
from streamlit_authenticator import Hasher
from datetime import datetime
import os

# 1. GLOBAL SYSTEM CONFIGURATION
st.set_page_config(page_title="AI Code Understanding & Explanation Tool for Debugging Assistance", layout="wide", initial_sidebar_state="expanded")

# Environment variables for sensitive configurations
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
INITIAL_ADMIN_USERNAME = os.getenv("INITIAL_ADMIN_USERNAME", "admin")
INITIAL_ADMIN_PASSWORD = os.getenv("INITIAL_ADMIN_PASSWORD", "admin123")
INITIAL_ADMIN_NAME = os.getenv("INITIAL_ADMIN_NAME", "Project Supervisor")

@st.cache_resource
def init_enterprise_database():
    try:
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        db = client["ai_debugger_db"]
        
        users_col = db["users"]
        chats_col = db["chat_history"]
        diagnostics_col = db["diagnostic_history"]
        
        users_col.create_index("username", unique=True)
        users_col.create_index("email", unique=True)
        chats_col.create_index([("username", 1), ("timestamp", 1)])
        diagnostics_col.create_index([("username", 1), ("timestamp", -1)])

        # Initialize default admin user if collection is empty
        if users_col.count_documents({}) == 0:
            hashed_password = Hasher.hash(INITIAL_ADMIN_PASSWORD)
            users_col.insert_one({
                "username": INITIAL_ADMIN_USERNAME,
                "name": INITIAL_ADMIN_NAME,
                "email": f"{INITIAL_ADMIN_USERNAME}@example.com",
                "password": hashed_password,
                "created_at": datetime.utcnow(),
            })
            st.success(f"Initial admin user '{INITIAL_ADMIN_USERNAME}' created.")

        return users_col, chats_col, diagnostics_col
    except pymongo.errors.ConnectionFailure as e:
        st.error(f"🔒 Database Connection Error: {e}. Please ensure MongoDB is running and accessible.")
        return None, None, None
    except Exception as e:
        st.error(f"🔒 An unexpected error occurred during database initialization: {e}")
        return None, None, None

users_collection, chats_collection, diagnostics_collection = init_enterprise_database()

# 2. DATA SCHEMAS
class CodeAnalysisSchema(BaseModel):
    summary: str = Field(description="A brief high-level overview of what the code does.")
    complexity: str = Field(description="Time and Space complexity in Big O notation (e.g., O(N) time, O(1) space).")
    explanation_steps: list[str] = Field(description="Step-by-step breakdown of the logic.")
    bugs_found: list[str] = Field(description="List of bugs, logical flaws, or edge-case handling issues.")
    fixed_code: str = Field(description="The complete, fully optimized and corrected version of the code.")

# -------------------------------------------------------------
# 3. IDENTITY ACCESS MANAGEMENT (IAM) FUNCS
# -------------------------------------------------------------
def register_user() -> None:
    st.header("New User Registration")
    st.caption("Establish authorized credentials to access analytics layers.")

    if users_collection is None:
        st.error("🔒 Database Service Unreachable. Registration is currently unavailable.")
        return

    with st.form("register_form", clear_on_submit=True):
        name = st.text_input("Full Name", key="reg_name")
        username = st.text_input("Username", key="reg_username")
        email = st.text_input("Email", key="reg_email")
        password = st.text_input("Password", type="password", key="reg_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm_password")
        submitted = st.form_submit_button("Register", use_container_width=True)

    if not submitted:
        return

    username = username.strip().lower()
    email = email.strip().lower()
    name = name.strip()

    if not username or not name or not email or not password:
        st.error("Operational Error: All entry forms require input arguments.")
        return
    if password != confirm_password:
        st.error("Operational Error: Password validation parameters mismatch.")
        return
    if len(password) < 6:
        st.error("Operational Error: Password must be >= 6 characters.")
        return
        
    try:
        if users_collection.find_one({"username": username}):
            st.error("Operational Error: Username variant matching existing profiles.")
            return
        if users_collection.find_one({"email": email}):
            st.error("Operational Error: Email profile mapped to alternative cluster node.")
            return

        users_collection.insert_one({
            "username": username,
            "name": name,
            "email": email,
            "password": Hasher.hash(password),
            "created_at": datetime.utcnow(),
        })
        st.success("Registration Complete! Switch to Login window tab.")
    except pymongo.errors.PyMongoError as e:
        st.error(f"Database Conflict Encountered: {e}")
    except Exception as e:
        st.error(f"An unexpected error occurred during registration: {e}")

def render_login() -> None:
    st.header("User Login")
    st.caption("Verify token credentials to initialize workspace pipelines.")

    with st.form("login_form"):
        username = st.text_input("Username ", key="login_username")
        password = st.text_input("Password ", type="password", key="login_password")
        submitted = st.form_submit_button("Login", use_container_width=True)

    if not submitted:
        return

    username = username.strip().lower()
    
    if users_collection is None:
        st.error("🔒 Database Service Unreachable. Login is currently unavailable.")
        return

    mongo_user = users_collection.find_one({"username": username})

    if mongo_user and Hasher.check_pw(password, mongo_user["password"]):
        st.session_state.authenticated = True
        st.session_state.username = username
        st.session_state.name = mongo_user.get("name", username)
        st.session_state.chat_memory = load_chat_history(username)
        st.session_state.diagnostic_history = load_diagnostic_history(username)
        st.rerun()
    else:
        st.error("Access Denied: Security validation verification checks failed.")

# -------------------------------------------------------------
# 4. CHAT PERSISTENCE SUBSYSTEM LAYER
# -------------------------------------------------------------
def save_chat_msg(username, role, content):
    if chats_collection is not None:
        try:
            chats_collection.insert_one({
                "username": username,
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow()
            })
        except pymongo.errors.PyMongoError as e:
            st.error(f"Failed to save chat message: {e}")

def load_chat_history(username):
    if chats_collection is not None:
        try:
            cursor = chats_collection.find({"username": username}).sort("timestamp", 1)
            return [{"role": doc["role"], "content": doc["content"]} for doc in cursor]
        except pymongo.errors.PyMongoError as e:
            st.error(f"Failed to load chat history: {e}")
            return []
    return []

def save_diagnostic_run(username, lang, raw_code, model_choice, analysis):
    if diagnostics_collection is not None:
        try:
            diagnostics_collection.insert_one({
                "username": username,
                "language": lang,
                "raw_code": raw_code,
                "model": model_choice,
                "analysis": analysis.model_dump(),
                "timestamp": datetime.utcnow(),
            })
        except pymongo.errors.PyMongoError as e:
            st.error(f"Failed to save IDE diagnostic backup: {e}")

def load_diagnostic_history(username, limit=25):
    if diagnostics_collection is not None:
        try:
            cursor = (
                diagnostics_collection
                .find({"username": username})
                .sort("timestamp", -1)
                .limit(limit)
            )
            history = []
            for doc in cursor:
                doc["id"] = str(doc.pop("_id"))
                history.append(doc)
            return history
        except pymongo.errors.PyMongoError as e:
            st.error(f"Failed to load IDE diagnostic backups: {e}")
            return []
    return []

def diagnostic_label(item):
    timestamp = item.get("timestamp")
    if isinstance(timestamp, datetime):
        timestamp_text = timestamp.strftime("%Y-%m-%d %H:%M")
    else:
        timestamp_text = "saved run"
    language = item.get("language", "code")
    summary = item.get("analysis", {}).get("summary", "IDE diagnostic backup")
    return f"{timestamp_text} | {language} | {summary[:60]}"

def render_analysis_result(data, lang):
    tab_summary, tab_debug, tab_fix = st.tabs([
        "💻 Logic Breakdowns",
        "🪲 Defect Trace Logs",
        "✅ Patched Production Variant",
    ])

    with tab_summary:
        st.markdown("### Executive Summary")
        st.info(data.summary)
        st.markdown(f"**Algorithmic Profiler Index:** `{data.complexity}`")
        st.markdown("### Code Walkthrough Logic")
        for iteration, step in enumerate(data.explanation_steps, 1):
            st.write(f"**Step {iteration}:** {step}")

    with tab_debug:
        st.markdown("### Discovered Critical Vulnerabilities")
        if data.bugs_found:
            for issue in data.bugs_found:
                st.markdown(f"ðŸ”´ {issue}")
        else:
            st.success("Zero immediate flaws located inside target logic structure.")

    with tab_fix:
        st.markdown("### Compiled Refactored Baseline Patch")
        st.code(data.fixed_code, language=lang)

# -------------------------------------------------------------
# 5. CORE ROUTING EXECUTION CONTROL GATEWAY
# -------------------------------------------------------------
if not st.session_state.get("authenticated"):
    st.header("⚡AI Code Understanding & Explanation Tool for Debugging Assistance")
    login_tab, register_tab = st.tabs(["🔒 Login", "📝 New User Registration"])
    with login_tab:
        render_login()
    with register_tab:
        register_user()
    st.stop()

# Initialize chat_memory only if not already set by login
if "chat_memory" not in st.session_state:
    st.session_state.chat_memory = load_chat_history(st.session_state.username)
if "diagnostic_history" not in st.session_state:
    st.session_state.diagnostic_history = load_diagnostic_history(st.session_state.username)

# -------------------------------------------------------------
# 6. ENTERPRISE STUDIO LAYOUT (MAIN WORKSPACE LAYER)
# -------------------------------------------------------------
st.title("⚡ AI Code Understanding & Explanation Tool for Debugging Assistance")
st.caption(f"Master: {st.session_state.name} | Model: {st.session_state.get('llm_model_choice', 'N/A')}")
st.markdown("---")

# SIDEBAR MONITOR WORKSPACE
with st.sidebar:
    st.subheader("System Access Profile")
    st.write(f"Logged as: **{st.session_state.username}**")
    if st.button("Logout 🔓", use_container_width=True):
        st.session_state.clear() # Clear all session state for a clean logout
        st.rerun()
    
    st.markdown("---")
    st.subheader("Compute Pipeline Settings")
    model_choice = st.selectbox("LLM Compute Engine", ["gemini-2.5-flash", "gemini-2.5-pro"], key="llm_model_choice")
    api_key = st.text_input("Enter Gemini Access Key Token", type="password", value=os.getenv("GEMINI_API_KEY", ""), key="gemini_api_key")
    
    st.markdown("---")
    st.subheader("Memory Maintenance")
    diagnostic_history = st.session_state.get("diagnostic_history", [])
    selected_backup = None
    st.subheader("Source Input Sandbox")
    if diagnostic_history:
        selected_backup_index = st.selectbox(
            "IDE Diagnostic Backups",
            range(len(diagnostic_history)),
            format_func=lambda index: diagnostic_label(diagnostic_history[index]),
            key="diagnostic_backup_select",
        )
        selected_backup = diagnostic_history[selected_backup_index]
        if st.button("Restore Selected Backup", use_container_width=True):
            st.session_state["raw_code_input"] = selected_backup.get("raw_code", "")
            st.session_state["code_lang_select"] = selected_backup.get("language", "python")
            st.rerun()
    else:
        st.caption("No IDE diagnostic backups saved yet.")
    if st.button("Delete Saved Conversation", use_container_width=True):
        if chats_collection is not None:
            try:
                chats_collection.delete_many({"username": st.session_state.username})
                st.session_state.chat_memory = []
                st.success("Session register buffers reset.")
                st.rerun()
            except pymongo.errors.PyMongoError as e:
                st.error(f"Failed to purge chat history: {e}")
        else:
            st.warning("Database not connected. Cannot purge history.")

    if st.button("Delete IDE Diagnostic Backups", use_container_width=True):
        if diagnostics_collection is not None:
            try:
                diagnostics_collection.delete_many({"username": st.session_state.username})
                st.session_state.diagnostic_history = []
                st.success("IDE diagnostic backups deleted.")
                st.rerun()
            except pymongo.errors.PyMongoError as e:
                st.error(f"Failed to delete IDE diagnostic backups: {e}")
        else:
            st.warning("Database not connected. Cannot purge IDE diagnostic backups.")

# STUDIO DASHBOARD TAB ENGINE
workspace_tab, chat_assistant_tab = st.tabs(["💻 IDE Diagnostic Workspace", "💬 Continuous AI Chat Assistant"])

# --- WORKSPACE TAB (THE ORIGINAL TWO-PANEL INTERFACE) ---
with workspace_tab:
    # diagnostic_history = st.session_state.get("diagnostic_history", [])
    # selected_backup = None
    col_editor, col_analytics = st.columns([1.1, 1], gap="large")

    with col_editor:
        # st.subheader("Source Input Sandbox")
        # if diagnostic_history:
        #     selected_backup_index = st.selectbox(
        #         "IDE Diagnostic Backups",
        #         range(len(diagnostic_history)),
        #         format_func=lambda index: diagnostic_label(diagnostic_history[index]),
        #         key="diagnostic_backup_select",
        #     )
        #     selected_backup = diagnostic_history[selected_backup_index]
        #     if st.button("Restore Selected Backup", use_container_width=True):
        #         st.session_state["raw_code_input"] = selected_backup.get("raw_code", "")
        #         st.session_state["code_lang_select"] = selected_backup.get("language", "python")
        #         st.rerun()
        # else:
        #     st.caption("No IDE diagnostic backups saved yet.")

        lang = st.selectbox("Target Compiler Mapping", ["python", "javascript", "cpp", "java"], key="code_lang_select")
        # Persist raw_code using session state
        raw_code = st.text_area("Inject raw evaluation source scripts here:", height=450, placeholder="# Insert package blocks...", key="raw_code_input")
        analyze_action = st.button("Run Static AI Analysis 🚀", use_container_width=True)

    with col_analytics:
        st.subheader("Static Diagnostics Stream")
        if analyze_action:
            if not api_key:
                st.error("Pipeline Disrupted: Unauthenticated connection strings located.")
            elif not raw_code.strip():
                st.warning("Telemetry Cancelled: Analysis target buffer text reports size null.")
            else:
                try:
                    client = genai.Client(api_key=api_key)
                    with st.spinner("Compiling structural properties parameters..."):
                        raw_response = client.models.generate_content(
                            model=model_choice,
                            contents=f"Analyze this {lang} codebase snippet:\n\n{raw_code}",
                            config=types.GenerateContentConfig(
                                system_instruction="You are a principal engineer. Be critical about performance and flaws.",
                                response_mime_type="application/json",
                                response_schema=CodeAnalysisSchema,
                                temperature=0.1
                            ),
                        )
                        data: CodeAnalysisSchema = raw_response.parsed
                        save_diagnostic_run(st.session_state.username, lang, raw_code, model_choice, data)
                        st.session_state.diagnostic_history = load_diagnostic_history(st.session_state.username)
                    
                    tab_summary, tab_debug, tab_fix = st.tabs(["📋 Logic Breakdowns", "🐛 Defect Trace Logs", "🛠️ Patched Production Variant"])
                    
                    with tab_summary:
                        st.markdown("### Executive Summary")
                        st.info(data.summary)
                        st.markdown(f"**Algorithmic Profiler Index:** `{data.complexity}`")
                        st.markdown("### Code Walkthrough Logic")
                        for iteration, step in enumerate(data.explanation_steps, 1):
                            st.write(f"**Step {iteration}:** {step}")
                            
                    with tab_debug:
                        st.markdown("### Discovered Critical Vulnerabilities")
                        if data.bugs_found:
                            for issue in data.bugs_found:
                                st.markdown(f"🔴 {issue}")
                        else:
                            st.success("Zero immediate flaws located inside target logic structure.")
                            
                    with tab_fix:
                        st.markdown("### Compiled Refactored Baseline Patch")
                        st.code(data.fixed_code, language=lang)
                        
                except Exception as e:
                    st.error(f"Runtime Exception Intercepted: {e}")
        elif selected_backup:
            st.caption("Showing selected IDE diagnostic backup.")
            saved_data = CodeAnalysisSchema(**selected_backup.get("analysis", {}))
            render_analysis_result(saved_data, selected_backup.get("language", "python"))

# --- CHAT ASSISTANT TAB (THE NATIVE CHAT LOG INTERFACE) ---
with chat_assistant_tab:
    st.subheader("Conversational Debugging Workspace")
    st.caption("Ask contextual follow-up questions regarding architectural patterns.")
    
    # RENDER HISTORICAL ELEMENTS
    for msg in st.session_state.chat_memory:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    # CAPTURE NEW ENTRIES
    if chat_prompt := st.chat_input("Ask a question about code or structural patterns...", key="chat_input_widget"):
        with st.chat_message("user"):
            st.markdown(chat_prompt)
            
        st.session_state.chat_memory.append({"role": "user", "content": chat_prompt})
        save_chat_msg(st.session_state.username, "user", chat_prompt)
        
        if not api_key:
            st.error("Authentication Failures: Missing active security key configurations.")
        else:
            try:
                chat_history_for_llm = st.session_state.chat_memory[-20:] 
                chat_context = "\n\n".join(
                    f"{msg['role'].title()}: {msg['content']}"
                    for msg in chat_history_for_llm
                )
                chat_prompt_for_llm = (
                    "You are a helpful code debugging assistant. Continue the conversation below. "
                    "Use the previous messages as context, and answer the latest user message.\n\n"
                    f"{chat_context}"
                )

                client = genai.Client(api_key=api_key)
                with st.chat_message("assistant"):
                    with st.spinner("Evaluating dialogue arrays context loops..."):
                        response = client.models.generate_content(
                            model=model_choice,
                            contents=chat_prompt_for_llm,
                            config=types.GenerateContentConfig(
                                temperature=0.7
                            )
                        )
                        ai_reply = response.text
                        st.markdown(ai_reply)
                        
                st.session_state.chat_memory.append({"role": "assistant", "content": ai_reply})
                save_chat_msg(st.session_state.username, "assistant", ai_reply)
                st.rerun()
            except Exception as chat_err:
                st.error(f"Chat Pipeline Fault: {chat_err}")
