import streamlit as st
import pandas as pd
import json
import time
from datetime import datetime
from backend.auth import is_user_logged_in, get_current_user_name, get_logged_in_user_id, update_profile_name, change_password
from utils.database import (
    get_db_connection, 
    get_latest_resume_score, 
    get_job_recommendations, 
    get_user_analysis, 
    get_search_history,
    update_job_status
)

def format_date(date_str):
    if not date_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        return dt.strftime("%B %d, %Y")
    except:
        return str(date_str).split(" ")[0]

def profile_page():
    if not is_user_logged_in():
        st.error("You need to be logged in to access this page.")
        st.stop()

    user_id = get_logged_in_user_id()
    user_name = get_current_user_name()
    
    # --- Data Fetching ---
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # User Details
    cursor.execute("SELECT email, registration_date, resume_file_path FROM users WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()
    email = user_data['email'] if user_data else "Unknown"
    reg_date = format_date(user_data['registration_date']) if user_data else "Unknown"
    
    # Stats
    jobs = get_job_recommendations(user_id)
    jobs_df = pd.DataFrame(jobs) if jobs else pd.DataFrame(columns=['id', 'status', 'match_percentage'])
    
    total_jobs = len(jobs_df)
    saved_jobs = len(jobs_df[jobs_df['status'] == 'saved'])
    applied_jobs = len(jobs_df[jobs_df['status'] == 'applied'])
    
    # Resume Score
    latest_score_data = get_latest_resume_score(user_id)
    overall_score = latest_score_data.get('overall_score', 0) if latest_score_data else 0
    classification = latest_score_data.get('classification', 'N/A') if latest_score_data else 'N/A'
    
    # Resume Analysis
    analysis_data = get_user_analysis(user_id)
    
    conn.close()

    # --- UI Construction ---
    
    # Custom CSS for Dark Theme (Matching Global Styles)
    st.markdown("""
        <style>
        /* Global Text Colors */
        h1, h2, h3 {
            color: #f8fafc !important;
        }
        
        /* Profile Header */
        .profile-header {
            background-color: #1e293b;
            padding: 2rem;
            border-radius: 12px;
            border: 1px solid #334155;
            margin-bottom: 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .profile-name {
            font-size: 2.2rem;
            font-weight: 700;
            color: #3b82f6; /* Primary Blue */
            margin: 0;
        }
        .profile-meta {
            font-size: 1rem;
            color: #94a3b8;
            margin-top: 0.5rem;
        }
        
        /* Stats Cards */
        .metric-card {
            background-color: #1e293b;
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #3b82f6;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s;
            border: 1px solid #334155;
            border-left: 4px solid #3b82f6;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            background-color: #243147;
        }
        .stat-number {
            font-size: 2.2rem;
            font-weight: bold;
            color: #f8fafc;
            margin-bottom: 5px;
        }
        .stat-label {
            font-size: 0.9rem;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        /* Section Titles */
        .section-header {
            margin-top: 2.5rem;
            margin-bottom: 1.5rem;
            border-bottom: 1px solid #FFFFFF;
            padding-bottom: 10px;
            font-size: 1.4rem;
            color: #FFFFFF;
            font-weight: 600;
        }
        
        /* History Items */
        .history-item {
            background-color: #1e293b;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #334155;
            margin-bottom: 10px;
            transition: border-color 0.2s;
        }
        .history-item:hover {
            border-color: #3b82f6;
        }
        
        /* Sidebar/Panels */
        .side-panel {
            background-color: #1e293b;
            padding: 20px;
            border-radius: 12px;
            border: 1px solid #334155;
        }
        
        /* DataFrame Styling */
        div[data-testid="stDataFrame"] {
            background-color: #1e293b;
            border-radius: 12px;
            border: 1px solid #334155;
        }
        </style>
    """, unsafe_allow_html=True)


    # Header
    st.markdown(f"""
        <div class="profile-header">
            <div>
                <h1 class="profile-name">{user_name}</h1>
                <div class="profile-meta">📧 {email} &nbsp; • &nbsp; 📅 Joined {reg_date}</div>
            </div>
            <div style="text-align: right; color: #666; font-size: 3rem; opacity: 0.2;">
                👤
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Top Stats Row
    st.markdown('<div class="section-header">📊 Activity Overview</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    
    # Determine color for score
    score_color = "#3b82f6" # Default Blue
    if overall_score >= 90: score_color = "#00c853"
    elif overall_score >= 75: score_color = "#3b82f6"
    elif overall_score >= 60: score_color = "#ffd700"
    else: score_color = "#ff5252"
    
    with c1:
        st.markdown(f"""
            <div class="metric-card" style="border-left-color: {score_color}">
                <div class="stat-number" style="color: {score_color}">{overall_score}</div>
                <div class="stat-label">Resume Score</div>
            </div>
        """, unsafe_allow_html=True)
        
    with c2:
        st.markdown(f"""
            <div class="metric-card">
                <div class="stat-number">{applied_jobs}</div>
                <div class="stat-label">Applications</div>
            </div>
        """, unsafe_allow_html=True)
        
    with c3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="stat-number">{saved_jobs}</div>
                <div class="stat-label">Jobs Saved</div>
            </div>
        """, unsafe_allow_html=True)
        
    with c4:
        st.markdown(f"""
            <div class="metric-card">
                <div class="stat-number">{total_jobs}</div>
                <div class="stat-label">Jobs Found</div>
            </div>
        """, unsafe_allow_html=True)

    # Main Content Area
    col_left, col_right = st.columns([2, 1])

    with col_left:
        # Job Applications Tracker
        st.markdown('<div class="section-header">📂 Application Tracker</div>', unsafe_allow_html=True)
        
        # Tab View for cleaner interface
        tab_active, tab_history = st.tabs(["Active Applications", "Search History"])
        
        with tab_active:
            if not jobs_df.empty:
                # Filter for active interactions
                active_jobs = jobs_df[jobs_df['status'].isin(['saved', 'applied', 'interviewing'])].copy()
                if not active_jobs.empty:
                    # Clean up for display
                    display_df = active_jobs[['id', 'job_title', 'company_name', 'match_percentage', 'status', 'posted_date']].copy()
                    display_df.columns = ['ID', 'Role', 'Company', 'Match', 'Status', 'Date']
                    
                    # Convert match to integer
                    display_df['Match'] = display_df['Match'].fillna(0).astype(int)
                    
                    edited_df = st.data_editor(
                        display_df,
                        use_container_width=True,
                        hide_index=True,
                        disabled=["Role", "Company", "Match", "Date"],
                        column_config={
                            "ID": None, # Hide ID
                            "Role": st.column_config.TextColumn("Role", width="large"),
                            "Company": st.column_config.TextColumn("Company", width="medium"),
                            "Status": st.column_config.SelectboxColumn(
                                "Status",
                                help="Update your application progress",
                                width="medium",
                                options=["saved", "applied", "interviewing", "rejected"],
                            ),
                            "Match": st.column_config.ProgressColumn(
                                "Match",
                                format="%d%%",
                                min_value=0,
                                max_value=100,
                            ),
                            "Date": st.column_config.TextColumn("Posted", width="small")
                        },
                        key="active_jobs_editor"
                    )
                    
                    # Handle changes
                    if st.session_state.active_jobs_editor.get('edited_rows'):
                        for row_idx, changes in st.session_state.active_jobs_editor['edited_rows'].items():
                            if 'Status' in changes:
                                job_idx = int(row_idx)
                                job_id = display_df.iloc[job_idx]['ID']
                                new_status = changes['Status']
                                if update_job_status(user_id, job_id, new_status):
                                    st.toast(f"Updated status to {new_status}")
                                    time.sleep(0.5)
                                    st.rerun()
                else:
                    st.info("No active applications. Go to Job Recommendations to find matching roles!")
                    if st.button("Browse Jobs Now"):
                        st.session_state['page'] = 'Job Recommendations'
                        st.rerun()
            else:
                st.info("No job data found yet.")

        with tab_history:
            history = get_search_history(user_id)
            if history:
                for item in history:
                    st.markdown(f"""
                    <div class="history-item">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <div style="color:#3b82f6; font-weight:600;">{item['query_summary']}</div>
                                <div style="color:#94a3b8; font-size:0.85em;">{format_date(item['timestamp'])}</div>
                            </div>
                            <div style="text-align:right;">
                                <div style="font-size:1.1em; font-weight:bold; color: #f8fafc;">{item['found']}</div>
                                <div style="font-size:0.8em; color:#94a3b8;">results</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.caption("No search history available.")

    with col_right:
        # Resume Insights Side Panel
        st.markdown('<div class="section-header">📄 Insights</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="side-panel">', unsafe_allow_html=True)
        
        if classification != 'N/A':
             # Color code specific classifications
            cls_color = "white"
            if classification == "Excellent": cls_color = "#00c853"
            elif classification == "Good": cls_color = "#3b82f6"
            elif classification == "Average": cls_color = "#ffd700"
            else: cls_color = "#ff5252"
            
            st.markdown(f"**Classification:** <span style='color:{cls_color}; font-weight:bold'>{classification}</span>", unsafe_allow_html=True)
        
        if analysis_data:
            st.caption(f"Last Analyzed: {format_date(analysis_data.get('timestamp'))}")
            st.divider()
            
            # Strengths Summary
            if analysis_data.get('strengths'):
                st.markdown("**Top Strengths**")
                # Handle varying strength formats safely
                s_list = analysis_data['strengths']
                if isinstance(s_list, dict): 
                     # Extract list from dict if nested
                     s_list = s_list.get('strengths', []) or s_list.get('items', [])
                
                # Show top 3 normalized strings
                count = 0
                for s in s_list:
                    if count >= 3: break
                    txt = s.get('strength', s) if isinstance(s, dict) else s
                    st.markdown(f"✅ {txt}")
                    count += 1
            
            st.markdown("---")
            if st.button("View Full Analysis", use_container_width=True):
                st.session_state['page'] = 'Analysis Results'
                st.rerun()
        else:
            st.warning("Resume analysis incomplete.")
            if st.button("Analyze Resume", use_container_width=True):
                st.session_state['page'] = 'Analyse Resume'
                st.rerun()
                
        st.markdown('</div>', unsafe_allow_html=True)

    # Account Actions
    st.markdown('<div class="section-header">⚙️ Account Settings</div>', unsafe_allow_html=True)
    with st.expander("Update Profile"):
        # Profile Name Update
        st.subheader("Profile Information")
        with st.form("update_name_form"):
            c_a, c_b = st.columns(2)
            with c_a:
                new_name = st.text_input("Display Name", value=user_name)
            with c_b:
                st.text_input("Email Address", value=email, disabled=True, help="Email cannot be changed.")
            
            if st.form_submit_button("Save Profile Changes"):
                if new_name != user_name:
                    success, msg = update_profile_name(user_id, new_name)
                    if success:
                        st.success(msg)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.info("No changes made.")

        st.divider()
        
        # Password Change
        st.subheader("Security")
        with st.form("change_password_form"):
            st.write("Change Password")
            col_curr, col_new, col_conf = st.columns(3)
            with col_curr:
                start_password = st.text_input("Current Password", type="password")
            with col_new:
                new_password = st.text_input("New Password", type="password")
            with col_conf:
                confirm_password = st.text_input("Confirm New Password", type="password")
                
            if st.form_submit_button("Update Password"):
                if not start_password or not new_password or not confirm_password:
                    st.error("All fields are required.")
                elif new_password != confirm_password:
                    st.error("New passwords do not match.")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters long.")
                else:
                    success, msg = change_password(user_id, start_password, new_password)
                    if success:
                        st.success(msg)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(msg)

