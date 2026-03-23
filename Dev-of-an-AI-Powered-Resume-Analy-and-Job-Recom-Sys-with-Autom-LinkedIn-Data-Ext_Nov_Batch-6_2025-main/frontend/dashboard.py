import streamlit as st
import os
import PyPDF2
import docx
import time
from datetime import datetime
from backend.auth import is_user_logged_in, get_current_user_name
from utils.database import get_db_connection
from backend.resume_parser import parse_resume
from frontend.modern_components import ModernUI


def format_date(date_str):
    """Normalize timestamp strings to a readable date."""
    if not date_str:
        return "N/A"
    try:
        # Accept ISO-like strings and strip timezone Z if present
        dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        return dt.strftime("%B %d, %Y")
    except Exception:
        return str(date_str).split(" ")[0]


MAX_FILE_SIZE = 5 * 1024 * 1024

def is_file_valid(file):

    if file.size > MAX_FILE_SIZE:
        return False, "File size exceeds the 5MB limit."

    file_extension = os.path.splitext(file.name)[1].lower()
    if file_extension not in ['.pdf', '.docx']:
        return False, "Invalid file format. Please upload a PDF or DOCX file."

    try:
        if file_extension == '.pdf':
            PyPDF2.PdfReader(file)
        elif file_extension == '.docx':
            docx.Document(file)
    except Exception:
        return False, "The file appears to be corrupted."

    return True, ""


def dashboard_page():

    if not is_user_logged_in():
        st.error("You need to be logged in to access this page.")
        st.stop()

    # initialize uploader flag
    if 'show_resume_uploader' not in st.session_state:
        st.session_state['show_resume_uploader'] = False

    st.title(f"Welcome to your Dashboard, {get_current_user_name()}!")

    # Always refresh from database to ensure latest data
    conn = get_db_connection()
    cursor = conn.cursor()
    user_id = st.session_state['user_id']
    cursor.execute("SELECT resume_file_path FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    cursor.execute("SELECT analysis_timestamp FROM resume_analysis WHERE user_id = ? ORDER BY analysis_timestamp DESC LIMIT 1", (user_id,))
    latest_analysis = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) FROM job_recommendations WHERE user_id = ?", (user_id,))
    job_recommendation_count = cursor.fetchone()[0]
    conn.close()
    
    # Store in session to avoid multiple DB queries in same render
    st.session_state['user_resume_path'] = user['resume_file_path'] if user else None

    has_resume = bool(st.session_state.get('user_resume_path'))

    st.header("Quick Stats")
    col1, col2, col3 = st.columns(3)
    with col1:
        if has_resume:
            st.metric("Resume Status", "✅ Uploaded")
        else:
            st.markdown("**Resume Status**")
            st.markdown("<span style='font-size:14px'>❌ Not Uploaded</span>", unsafe_allow_html=True)
    with col2:
        st.metric("Last Analysis", latest_analysis['analysis_timestamp'].split(" ")[0] if latest_analysis else "Never")
    with col3:
        st.metric("Job Recommendations", job_recommendation_count)

    st.header("What would you like to do?")
    col1, col2 = st.columns(2)
    
    with col1:
        if not has_resume:
            if st.button("📤 Upload Your Resume"):
                st.session_state['show_resume_uploader'] = True
                st.rerun()
   
    with col2:
        if has_resume:
            if st.button("🔍 Analyze Your Resume"):
                st.session_state['page'] = 'Resume Analysis'
                st.rerun()

    # Uploader or delete area occupies the same section position
    if not has_resume:
        with st.expander("Upload Your Resume", expanded=st.session_state.get('show_resume_uploader', False)):
            uploaded_file = st.file_uploader(
                "Choose a PDF or DOCX file",
                type=['pdf', 'docx'],
                accept_multiple_files=False
            )

            if uploaded_file is not None:
                is_valid, message = is_file_valid(uploaded_file)
                if not is_valid:
                    st.error(message)
                else:
                    st.write("File Details:")
                    st.write(f"- **Name:** {uploaded_file.name}")
                    st.write(f"- **Size:** {round(uploaded_file.size / 1024, 2)} KB")
                    
                    if st.button("Upload Resume"):
                        with st.spinner("Uploading and parsing your resume..."):
                            file_extension = os.path.splitext(uploaded_file.name)[1]
                            unique_filename = f"{user_id}_{int(time.time())}{file_extension}"
                            file_path = os.path.join("data", "resumes", unique_filename)
                            
                            with open(file_path, "wb") as f:
                                f.write(uploaded_file.getbuffer())
                            
                            # Update the user's resume file path in the database
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute("UPDATE users SET resume_file_path = ? WHERE id = ?", (file_path, user_id))
                            conn.commit()
                            conn.close()

                            # Update session immediately so UI reflects new state before rerun
                            st.session_state['user_resume_path'] = file_path

                            # Parse the resume and store the extracted text
                            parse_resume(file_path, user_id)

                        st.success("Resume uploaded and analyzed successfully!")
                        # collapse the uploader after successful upload
                        st.session_state['show_resume_uploader'] = False
                        st.rerun()
    else:
        # When resume exists, show metadata and delete controls in the same section position
        with st.expander("Manage Current Resume", expanded=False):
            current_path = st.session_state.get('user_resume_path')
            if current_path:
                file_name = os.path.basename(current_path)
                file_size = os.path.getsize(current_path) if os.path.exists(current_path) else 0
                size_kb = round(file_size / 1024, 2)

                # Fetch latest analysis timestamp for display
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT analysis_timestamp FROM resume_analysis WHERE user_id = ? ORDER BY analysis_timestamp DESC LIMIT 1",
                    (user_id,)
                )
                latest = cursor.fetchone()
                conn.close()

                st.markdown("**Current Resume**")
                st.write(f"📄 Name: {file_name}")
                st.write(f"📦 Size: {size_kb} KB")
                st.write(f"📁 Path: {current_path}")
                st.write(f"⏱️ Last parsed: {latest['analysis_timestamp'] if latest else 'Never'}")

            st.markdown("To upload a new resume, delete the current one.")
            if st.button("🗑️ Delete Current Resume", use_container_width=True):
                try:
                    if os.path.exists(current_path or ''):
                        os.remove(current_path)
                except Exception as e:
                    st.warning(f"Could not delete file: {e}")

                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM resume_analysis WHERE user_id = ?", (user_id,))
                cursor.execute("UPDATE users SET resume_file_path = NULL WHERE id = ?", (user_id,))
                conn.commit()
                conn.close()

                st.session_state['user_resume_path'] = None
                st.success("Resume deleted successfully.")
                st.rerun()

        # Secondary delete section removed to avoid duplicate controls

    # Guided steps section
    st.header("How It Works")
    st.caption("Follow these quick steps to use the app.")

    steps = [
        ("Login", "🔐"),
        ("Upload Resume", "📤"),
        ("Analyze", "🔍"),
        ("Review Insights", "🧠"),
        ("Match Jobs", "🎯"),
        ("Apply", "📨"),
    ]

    cols = st.columns(len(steps))
    for i, (label, icon) in enumerate(steps):
        with cols[i]:
            st.markdown(
                f"""
                <div style="
                    background-color: #1e293b;
                    border: 1px solid #334155;
                    border-radius: 8px;
                    padding: 1rem;
                    text-align: center;
                    height: 100%;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                ">
                    <div style="font-size: 2rem; margin-bottom: 0.5rem;">{icon}</div>
                    <div style="font-weight: 600; color: #f8fafc; font-size: 0.9rem;">{label}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.header("Recent Activity")

    # Aggregate recent user activities: searches, resume analyses, and job interactions
    activities = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Recent searches
        cursor.execute("SELECT query_summary, search_timestamp, jobs_found_count, new_jobs_count FROM search_history WHERE user_id = ? ORDER BY search_timestamp DESC LIMIT 5", (user_id,))
        for r in cursor.fetchall():
            activities.append({
                "type": "search",
                "label": r[0],
                "meta": f"{r[2]} results ({r[3]} new)",
                "timestamp": r[1]
            })

        # Recent resume analyses
        cursor.execute("SELECT analysis_timestamp FROM resume_analysis WHERE user_id = ? ORDER BY analysis_timestamp DESC LIMIT 5", (user_id,))
        for r in cursor.fetchall():
            activities.append({
                "type": "analysis",
                "label": "Resume Analysis",
                "meta": "Detailed insights generated",
                "timestamp": r[0]
            })

        # Recent job interactions/additions
        cursor.execute("SELECT job_title, company_name, status, match_percentage, scraping_date FROM job_recommendations WHERE user_id = ? ORDER BY scraping_date DESC LIMIT 6", (user_id,))
        for r in cursor.fetchall():
            title = r[0] or "(untitled)"
            comp = r[1] or ""
            status = r[2] or "new"
            match = int(r[3]) if r[3] is not None else 0
            activities.append({
                "type": "job",
                "label": f"{title} @ {comp}",
                "meta": f"{status.upper()} — {match}% match",
                "timestamp": r[4] or ''
            })
    except Exception as e:
        st.error(f"Could not fetch recent activity: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass

    # Normalize and sort by timestamp (most recent first)
    def _parse_ts(ts):
        if not ts:
            return datetime.min
        try:
            return datetime.fromisoformat(str(ts).replace('Z', '+00:00'))
        except Exception:
            try:
                return datetime.strptime(str(ts).split(" ")[0], "%Y-%m-%d")
            except Exception:
                return datetime.min

    activities.sort(key=lambda x: _parse_ts(x.get('timestamp')), reverse=True)

    if not activities:
        st.info("No recent activity to show yet. Start a search or analyze your resume to populate this list.")
    else:
        for a in activities:
            icon = ""
            if a['type'] == 'search': icon = '🔎'
            elif a['type'] == 'analysis': icon = '🧠'
            elif a['type'] == 'job': icon = '💼'
            ts = a.get('timestamp') or ''
            display_ts = format_date(ts)

            st.markdown(f"""
            <div style='display:flex; justify-content:space-between; align-items:center; padding:0.6rem 0.4rem; border-bottom:1px solid rgba(255,255,255,0.03);'>
                <div style='display:flex; gap:12px; align-items:center;'>
                    <div style='font-size:1.2rem;'>{icon}</div>
                    <div>
                        <div style='font-weight:700; color:#f8fafc;'>{a['label']}</div>
                        <div style='color:#94a3b8; font-size:0.9rem; margin-top:3px;'>{a['meta']}</div>
                    </div>
                </div>
                <div style='color:#94a3b8; font-size:0.85rem;'>{display_ts}</div>
            </div>
            """, unsafe_allow_html=True)

