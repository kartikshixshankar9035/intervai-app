import os
import streamlit as st
from google import genai
from google.genai import types

st.set_page_config(page_title="IntervAI", layout="wide")
st.title("🤝 IntervAI: AI Mock Interviewer & Feedback System")
st.caption("Simulate professional interviews and get instant, detailed feedback reports.")

# -------------------------------------------------------------
# 1. HARD FORCED API KEY INPUT
# -------------------------------------------------------------
st.sidebar.header("🔑 Authentication")
# Look for environment variable first, otherwise force a textbox in the sidebar
api_key = os.environ.get("GEMINI_API_KEY") or st.sidebar.text_input("Paste Gemini API Key Here:", type="password", help="Get a free key from Google AI Studio")

if not api_key:
    st.warning("⚠️ Access Blocked: You must paste your Gemini API Key into the sidebar field to unlock the application.")
    st.info("💡 Don't have a key? Go to https://aistudio.google.com/ to generate a free developer key instantly.")
    st.stop()

# Initialize the Gemini Client safely after key verification
client = genai.Client(api_key=api_key)

# Initialize Session State Variables to preserve data across interactions
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "interview_started" not in st.session_state:
    st.session_state.interview_started = False
if "interview_complete" not in st.session_state:
    st.session_state.interview_complete = False

# -------------------------------------------------------------
# 2. INTERVIEW SETUP FORM
# -------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.header("📋 Interview Setup")
job_title = st.sidebar.text_input("Target Job Title", value="Software Engineer")
job_desc = st.sidebar.text_area("Job Description / Key Skills", value="Proficiency in Python, system design, and algorithmic problem-solving.")
resume_text = st.sidebar.text_area("Your Resume / Background Summarized", value="ECE Student skilled in Python programming and Embedded Systems.")

# Defining the Interviewer's strict systemic persona
INTERVIEWER_PROMPT = f"""
You are an expert technical interviewer for the role of {job_title}. 
Your target job description is: {job_desc}. 
The candidate's profile is: {resume_text}.

Conduct a realistic job interview. Follow these rules strictly:
1. Ask exactly ONE question at a time. Never dump multiple questions.
2. Wait for the candidate's response before asking the next question.
3. Stay strictly in character as a professional interviewer.
4. Do NOT give feedback, grades, or corrections during the interview conversation. 
5. Start immediately by welcoming the candidate and asking the first question.
"""

if st.sidebar.button("🚀 Start Interview", disabled=st.session_state.interview_started):
    st.session_state.interview_started = True
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",  # Modern v2 core string
            contents=[types.Content(role="user", parts=[types.Part.from_text(text="Start the interview.")])],
            config=types.GenerateContentConfig(system_instruction=INTERVIEWER_PROMPT)
        )
        st.session_state.chat_history.append({"role": "interviewer", "text": response.text})
    except Exception as e:
        st.session_state.interview_started = False
        st.sidebar.error(f"❌ Server Error: {e}")

if st.sidebar.button("🛑 End Interview & Generate Report", disabled=not st.session_state.interview_started or st.session_state.interview_complete):
    st.session_state.interview_complete = True

# -------------------------------------------------------------
# 3. CONVERSATIONAL LOOP & UI RENDERING
# -------------------------------------------------------------
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("💬 Live Interview Chat")
    
    # Render active conversational logs
    for message in st.session_state.chat_history:
        if message["role"] == "interviewer":
            with st.chat_message("assistant", avatar="🤖"):
                st.write(message["text"])
        else:
            with st.chat_message("user", avatar="👨‍💻"):
                st.write(message["text"])

    if st.session_state.interview_started and not st.session_state.interview_complete:
        if user_answer := st.chat_input("Type your response here..."):
            st.session_state.chat_history.append({"role": "candidate", "text": user_answer})
            
            # Format conversational arrays for multi-turn execution
            formatted_contents = []
            for msg in st.session_state.chat_history:
                role_type = "model" if msg["role"] == "interviewer" else "user"
                formatted_contents.append(
                    types.Content(role=role_type, parts=[types.Part.from_text(text=msg["text"])])
                )
            
            with st.spinner("Interviewer is thinking..."):
                try:
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",  # Modern v2 core string
                        contents=formatted_contents,
                        config=types.GenerateContentConfig(system_instruction=INTERVIEWER_PROMPT)
                    )
                    st.session_state.chat_history.append({"role": "interviewer", "text": response.text})
                    st.rerun()
                except Exception as e:
                    st.session_state.chat_history.pop()
                    st.error(f"⚠️ Transmission failed. Please try submitting again. Error detail: {e}")

# -------------------------------------------------------------
# 4. ANALYTICS & FEEDBACK MODULE
# -------------------------------------------------------------
with col2:
    st.subheader("📊 Performance Analytics")
    
    if st.session_state.interview_complete:
        with st.spinner("Analyzing transcript and compiling metrics..."):
            transcript = ""
            for msg in st.session_state.chat_history:
                label = "Interviewer" if msg["role"] == "interviewer" else "Candidate"
                transcript += f"{label}: {msg['text']}\n"
            
            EVALUATOR_PROMPT = """
            You are a senior talent acquisition specialist. Analyze the interview transcript.
            Generate a detailed performance review containing:
            1. Overall Score out of 10.
            2. Technical Accuracy Evaluation.
            3. Communication Style (STAR method critique).
            4. Detailed list of highlights and areas for improvement.
            Format completely using clean Markdown headings, tables, and bullet points.
            """
            try:
                report = client.models.generate_content(
                    model="gemini-2.5-pro",  # FIXED: Updated to modern v2 analytics engine string
                    contents=[types.Content(role="user", parts=[types.Part.from_text(text=f"Transcript:\n{transcript}")])],
                    config=types.GenerateContentConfig(system_instruction=EVALUATOR_PROMPT)
                )
                st.success("Analysis Complete!")
                st.markdown(report.text)
            except Exception as e:
                st.error(f"Error compiling metrics: {e}")
    else:
        st.info("The evaluation report will generate in this dashboard panel as soon as you choose to conclude the session.")

# -------------------------------------------------------------
# 5. RESET UTILITY
# -------------------------------------------------------------
if st.session_state.interview_complete:
    if st.sidebar.button("🔄 Start New Session"):
        st.session_state.clear()
        st.rerun()