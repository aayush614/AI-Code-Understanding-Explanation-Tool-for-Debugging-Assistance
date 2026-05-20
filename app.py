import streamlit as st
import google.genai as genai
from google.genai import types
from pydantic import BaseModel, Field

class CodeAnalysisSchema(BaseModel):
    summary: str = Field(description="A brief high-level overview of what the code does.")
    complexity: str = Field(description="Time and Space complexity in Big O notation (e.g., O(N) time, O(1) space).")
    explanation_steps: list[str] = Field(description="Step-by-step breakdown of the logic.")
    bugs_found: list[str] = Field(description="List of bugs, logical flaws, or edge-case handling issues.")
    fixed_code: str = Field(description="The complete, fully optimized and corrected version of the code.")

# -------------------------------------------------------------
# 2. UI SETUP: IDE Layout Configuration
# -------------------------------------------------------------
st.set_page_config(page_title="AI code understanding", layout="wide", initial_sidebar_state="expanded")
st.title("AI Code Understanding & Explanation Tool for Debugging Assistance.")
st.markdown("---")

# Secure Token Management via Sidebar
with st.sidebar:
    st.subheader("🔑 Authentication")
    api_key = st.text_input("Gemini Corporate API Key", type="password")
    
    st.subheader("⚙️ Model Configuration")
    # Using the premium reasoning model for deep debugging tasks
    model_choice = st.selectbox("LLM Engine", ["gemini-2.5-pro", "gemini-2.5-flash"])
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