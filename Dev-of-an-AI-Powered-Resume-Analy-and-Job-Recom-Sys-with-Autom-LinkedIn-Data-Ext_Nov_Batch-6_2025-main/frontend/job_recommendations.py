import streamlit as st
import pandas as pd
from backend.auth import get_logged_in_user_id
from backend.scraper import LinkedInJobScraper
from utils.database import (
    get_job_recommendations, save_user_search_preferences,
    get_user_search_preferences, add_search_history_entry,
    get_search_history, update_job_match_scores, update_job_status,
    get_user_analysis
)
from backend.recommendations import JobRecommender
import time
import textwrap
import math
import json
from datetime import datetime

def recommendations_page():
    user_id = get_logged_in_user_id()
    if not user_id:
        st.warning("Please log in to view recommendations.")
        return

    # Initialize Recommender
    try:
        recommender = JobRecommender()
    except ImportError:
        st.error("Backend module error.")
        return

    # --- Load Saved Preferences ---
    saved_prefs = get_user_search_preferences(user_id) or {}

    st.title("🚀 Smart Job Search")
    
    # Layout: Sidebar for quick history, Main for Form & Results
    
    # --- SEARCH PREFERENCES FORM ---
    # Default to open, but can be closed by session state
    if "search_expander_open" not in st.session_state:
        st.session_state["search_expander_open"] = True
        
    # Reset Counter for forcing form clears
    if "reset_counter" not in st.session_state:
        st.session_state["reset_counter"] = 0
    
    suffix = f"_{st.session_state['reset_counter']}"

    with st.expander("🔍 **Search Preferences & Configuration**", expanded=st.session_state["search_expander_open"]):
        with st.form("job_search_form"):
            c1, c2 = st.columns([1, 1])
            with c1:
                job_title = st.text_input("Job Title", value=saved_prefs.get('job_title', 'Software Engineer'), placeholder="e.g. Data Scientist", key=f"search_job_title{suffix}")
                location = st.text_input("Location", value=saved_prefs.get('location', 'India'), placeholder="e.g. New York, Remote", key=f"search_location{suffix}")
            
            with c2:
               # Remote Preference (Single select simulating Radio for compactness)
               remote_map = {"Any": [], "Remote": ["remote"], "Hybrid": ["hybrid"], "On-site": ["on_site"]}
               # Reverse map for default
               saved_remote_code = saved_prefs.get('remote_type', 'Any')
               # Ensure robustness if saved value is invalid
               default_idx = 0
               try:
                   default_idx = ["Any", "Remote", "Hybrid", "On-site"].index(saved_remote_code)
               except ValueError:
                   default_idx = 0
                   
               remote_pref = st.selectbox("Workplace Type", ["Any", "Remote", "Hybrid", "On-site"], index=default_idx, key=f"search_remote{suffix}")

               exp_levels = ["Internship", "Entry Level", "Mid Level", "Senior Level", "Director"]
               saved_exp = saved_prefs.get('experience_level', 'Mid Level')
               # Robust index finding
               exp_idx = 2
               if saved_exp in exp_levels:
                   exp_idx = exp_levels.index(saved_exp)
               experience = st.selectbox("Experience Level", exp_levels, index=exp_idx, key=f"search_experience{suffix}")

            # Job Types
            st.markdown("**Job Type**")
            cols_jt = st.columns(4)
            jt_types = ["Full-time", "Part-time", "Contract", "Internship"]
            selected_jts = []
            
            # Helper to handle saved_jts list safety
            saved_jts = saved_prefs.get('job_type', ["Full-time"])
            if not isinstance(saved_jts, list): saved_jts = ["Full-time"]

            for i, jt in enumerate(jt_types):
                with cols_jt[i]:
                    if st.checkbox(jt, value=(jt in saved_jts)):
                        selected_jts.append(jt)

            # Advanced Section
            with st.expander("⚙️ Advanced Filters (Salary, Keywords, Company)"):
                ac1, ac2 = st.columns(2)
                with ac1:
                    min_salary = st.number_input("Min Annual Salary ($)", value=int(saved_prefs.get('min_salary', 0)), step=5000, key=f"search_min_salary{suffix}")
                    keywords_inc = st.text_input("Must-have Keywords", value=saved_prefs.get('keywords_include', ''), placeholder="python, machine learning", key=f"search_keywords_inc{suffix}")
                    visa_support = st.checkbox("Visa Sponsorship Required", value=saved_prefs.get('visa_sponsorship', False), key=f"search_visa{suffix}")

                with ac2:
                    default_inds = saved_prefs.get('industries', [])
                    if not isinstance(default_inds, list): default_inds = []
                    industries = st.multiselect("Industries", ["Tech", "Finance", "Healthcare", "Education", "Retail", "Manufacturing"], default=default_inds, key=f"search_industries{suffix}")
                    keywords_exc = st.text_input("Exclude Keywords", value=saved_prefs.get('keywords_exclude', ''), placeholder="sales, cold calling", key=f"search_keywords_exc{suffix}")
                    commute_max = st.slider("Max Commute (mins)", 0, 120, int(saved_prefs.get('max_commute', 45)), key=f"search_commute{suffix}")
                
                
                preferred_companies = st.text_area("Preferred Companies", value=saved_prefs.get('preferred_companies', ''), placeholder="Google, Microsoft (comma separated)", key=f"search_companies{suffix}")
                
                # New Slider for Limit
                jobs_limit = st.slider("Max Jobs to Search", 5, 50, int(saved_prefs.get('search_limit', 5)), step=5, key=f"search_limit{suffix}")

                st.markdown("---")
                st.markdown("⏰ **Auto-Scheduling (Beta)**")
                schedule_freq = st.selectbox("Run this search automatically:", ["Off", "Daily", "Weekly"], index=["Off", "Daily", "Weekly"].index(saved_prefs.get('schedule_frequency', 'Off')), key=f"search_schedule{suffix}")
                if schedule_freq != "Off":
                    st.caption("You will receive email notifications when new jobs are found.")

            # Actions (Main Form Level)
            col_act1, col_act2, col_act3 = st.columns([2, 1, 1])
            with col_act1:
                search_submitted = st.form_submit_button("🔎 Find Jobs Now", type="primary")
            with col_act2:
                # We can't have multiple submit buttons easily in Streamlit form in standard way, 
                # but checkboxes work fine to modify the submit action.
                save_prefs = st.checkbox("Save as Default", value=False)
            with col_act3:
                # Reset needs to be outside form or handled differently, but Streamlit forms are strict.
                # Actually, making reset a checkbox often works better inside logic, OR separate button OUTSIDE form.
                # Putting it here as submit button creates conflict if pressed. 
                # Common pattern: Just one submit button. 
                pass

        if st.button("Reset Defaults"):
            if save_user_search_preferences(user_id, {}):
                # Increment reset counter to force all widgets to be recreated fresh
                st.session_state["reset_counter"] += 1
                        
                st.toast("Preferences reset!")
                time.sleep(0.5)
                st.rerun()

    # --- HANDLING FORM SUBMISSION ---
    # --- HANDLING FORM SUBMISSION (Part 1: Capture) ---
    if search_submitted:
        # 1. Build Prefs Object
        current_prefs = {
            "job_title": job_title,
            "location": location,
            "remote_type": remote_pref,
            "experience_level": experience,
            "job_type": selected_jts,
            "min_salary": min_salary,
            "keywords_include": keywords_inc,
            "keywords_exclude": keywords_exc,
            "industries": industries,
            "max_commute": commute_max,
            "visa_sponsorship": visa_support,
            "preferred_companies": preferred_companies,
            "search_limit": jobs_limit,
            "schedule_frequency": schedule_freq
        }
        
        # Save if requested
        if save_prefs:
            save_user_search_preferences(user_id, current_prefs)
            st.toast("Preferences Saved.")

        # Store for execution and collapse UI
        st.session_state['pending_search_params'] = current_prefs
        st.session_state["search_expander_open"] = False
        st.rerun()

    # --- HANDLING EXECUTION (Part 2: Run) ---
    if 'pending_search_params' in st.session_state:
        # Unpack params
        prefs = st.session_state['pending_search_params']
        job_title = prefs['job_title']
        location = prefs['location']
        remote_pref = prefs['remote_type']
        experience = prefs['experience_level']
        selected_jts = prefs['job_type']
        keywords_inc = prefs['keywords_include']
        keywords_exc = prefs['keywords_exclude']
        jobs_limit = prefs['search_limit']
        
        # Maps needed for logic
        remote_map = {"Any": [], "Remote": ["remote"], "Hybrid": ["hybrid"], "On-site": ["on_site"]}
        
        # Merge includes and job title
        full_query = job_title
        if keywords_inc:
            full_query += " " + keywords_inc
        if keywords_exc:
             excludes = [f'NOT "{k.strip()}"' for k in keywords_exc.split(',') if k.strip()]
             full_query += " " + " ".join(excludes)
             
        # Map Experience
        exp_map_scraper = {
            "Internship": "internship", "Entry Level": "entry", 
            "Mid Level": "associate", "Senior Level": "mid_senior", "Director": "director" 
        }
        
        # Map Job Type
        jt_map_scraper = {
            "Full-time": "full_time", "Part-time": "part_time", 
            "Contract": "contract", "Internship": "internship"
        }
        
        scraper_filters = {
            "remote": remote_map.get(remote_pref, []),
            "experience": [exp_map_scraper.get(experience, "mid_senior")],
            "job_type": [jt_map_scraper.get(t) for t in selected_jts if t in jt_map_scraper],
            "date_posted": "week" 
        }

        # Progress UI
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(current, total, eta):
            prog = min(current / total, 1.0)
            progress_bar.progress(prog)
            status_text.markdown(f"**Searching LinkedIn...**Found {current}/{total} jobs. <br>⏱️ Estimated time: {eta}", unsafe_allow_html=True)

        try:
            status_text.info("Initializing Intelligence Agent...")
            scraper = LinkedInJobScraper(user_id=user_id)
            
            # Login
            import os
            email = os.getenv("LINKEDIN_EMAIL")
            password = os.getenv("LINKEDIN_PASSWORD")
            
            if scraper.login(email, password):
                status_text.info(f"Logged In. Searching for '{full_query}' in {location}...")
                
                jobs = scraper.search_jobs(
                    keywords=full_query,
                    location=location,
                    limit=jobs_limit,
                    filters=scraper_filters,
                    progress_callback=update_progress
                )
                
                # Log History
                new_count = len(jobs)
                add_search_history_entry(user_id, f"{job_title} - {location}", prefs, len(jobs), new_count)
                
                # --- CALCULATE & UPDATE MATCH SCORES ---
                try:
                    status_text.info("Calculating match scores for new jobs...")
                    user_analysis = get_user_analysis(user_id)
                    if user_analysis:
                        all_jobs = get_job_recommendations(user_id)
                        updates = []
                        for job in all_jobs:
                            if job.get('match_percentage', 0) == 0:
                                analysis = job.get('job_analysis') or {}
                                if isinstance(analysis, str):
                                    try: analysis = json.loads(analysis)
                                    except: analysis = {}
                                score_data = recommender.calculate_match_score(user_analysis, analysis)
                                updates.append((job['id'], score_data['overall']))
                        
                        if updates:
                            update_job_match_scores(user_id, updates)
                            status_text.info(f"Updated scores for {len(updates)} jobs.")
                    else:
                        status_text.warning("Profile analysis not found. Skipping scoring.")
                except Exception as e:
                    st.warning(f"Note: Could not calculate scores: {str(e)}")
                # ---------------------------------------
                
                progress_bar.progress(1.0)
                status_text.success(f"Search Complete! Found {len(jobs)} new jobs.")
                time.sleep(1)
                
                # Clear pending state on success before rerun
                del st.session_state['pending_search_params']
                st.rerun()
            else:
                st.error("Login failed. Check credentials.")
                # Don't rerun automatically on failure so user sees error, 
                # but we should clear pending params so it doesn't loop? 
                # Or let them retry? If we keep params, it will retry on every reload. 
                # Better to clear.
                del st.session_state['pending_search_params']
                
        except Exception as e:
            st.error(f"Search failed: {e}")
            import traceback
            st.code(traceback.format_exc())
            if 'pending_search_params' in st.session_state:
                del st.session_state['pending_search_params']
        finally:
            if 'scraper' in locals():
                scraper.close()

    # --- MAIN DASHBOARD AREA ---
    
    col_dash, col_hist = st.columns([3, 1])
    
    # HISTORY SIDEBAR
    with col_hist:
        st.subheader("🕑 Recent Searches")
        history = get_search_history(user_id, limit=5)
        if not history:
            st.markdown("*No recent searches.*")
        else:
            for item in history:
                with st.container():
                     st.markdown(f"""
                     <div class="history-item">
                        <div>
                            <strong>{item['query_summary']}</strong><br>
                            <span style="color:#888; font-size:0.8em">{item['timestamp'][:10]}</span>
                        </div>
                        <div style="text-align:right">
                            <span style="color:#ffd700; font-weight:bold">+{item['new']}</span><br>
                            <span style="color:#666; font-size:0.8em">new</span>
                        </div>
                     </div>
                     """, unsafe_allow_html=True)
                     if st.button("Rerun", key=f"hist_{item['id']}"):
                         # Load params and rerun
                         prefs = item['params']
                         save_user_search_preferences(user_id, prefs) # Set as current
                         
                         # Force form refresh to show new values
                         if "reset_counter" in st.session_state:
                             st.session_state["reset_counter"] += 1
                         
                         # Open the expander to show loaded settings
                         st.session_state["search_expander_open"] = True
                         
                         st.toast("Configuration loaded! Click 'Find Jobs Now'.")
                         time.sleep(0.5)
                         st.rerun()

    # RESULTS AREA
    with col_dash:
        raw_jobs = get_job_recommendations(user_id)
        
        # Stats Bar
        k1, k2, k3 = st.columns(3)
        with k1: 
             st.markdown(f"<div class='metric-card'><h3>{len(raw_jobs)}</h3><p>Total Opportunities</p></div>", unsafe_allow_html=True)
        with k2:
             avg_match = int(sum(j.get('match_percentage', 0) for j in raw_jobs)/len(raw_jobs)) if raw_jobs else 0
             st.markdown(f"<div class='metric-card'><h3>{avg_match}%</h3><p>Avg Match Score</p></div>", unsafe_allow_html=True)
        with k3:
             new_jobs = len([j for j in raw_jobs if j.get('status') == 'new'])
             st.markdown(f"<div class='metric-card'><h3>{new_jobs}</h3><p>New / Unread</p></div>", unsafe_allow_html=True)

        st.markdown("---")
        
        # TABS
        tab_rec, tab_saved, tab_compare = st.tabs(["🎯 Recommended", "📌 Saved Jobs", "⚖️ Compare"])
        
        with tab_rec:
            # Sort controls
            s1, s2 = st.columns([2,1])
            with s1:
                 st.caption(f"Showing top results based on AI matching.")
            with s2:
                 sort_opt = st.selectbox("Sort by", ["Match %", "Newest", "Applicants"], label_visibility="collapsed")
            
            # Filter Logic (Client Side for Display)
            display_jobs = [j for j in raw_jobs if j.get('status') not in ['rejected']]
            
            if sort_opt == "Match %":
                display_jobs.sort(key=lambda x: x.get('match_percentage', 0), reverse=True)
            elif sort_opt == "Newest":
                display_jobs.sort(key=lambda x: x.get('posted_date', ''), reverse=True)
            elif sort_opt == "Applicants":
                display_jobs.sort(key=lambda x: x.get('applicant_count', 999))

            # Pagination
            page_size = 20
            if "job_page" not in st.session_state: st.session_state.job_page = 0
            
            total_pages = math.ceil(len(display_jobs) / page_size)
            curr_page = st.session_state.job_page
            
            # Bounds check
            if curr_page >= total_pages: curr_page = 0
            
            start = curr_page * page_size
            end = start + page_size
            page_items = display_jobs[start:end]
            
            if not page_items:
                st.info("No jobs found matching your criteria. Try adjusting filters or running a new search.")
            
            for job in page_items:
                _render_job_card(job, recommender, user_id, context="search")
            
            # Pagination Controls
            if total_pages > 1:
                pc1, pc2, pc3 = st.columns([1, 2, 1])
                with pc1:
                     if st.button("Previous", disabled=curr_page==0):
                         st.session_state.job_page -= 1
                         st.rerun()
                with pc2:
                     st.caption(f"Page {curr_page+1} of {total_pages}")
                with pc3:
                     if st.button("Next", disabled=curr_page>=total_pages-1):
                         st.session_state.job_page += 1
                         st.rerun()

        with tab_saved:
             saved_list = [j for j in raw_jobs if j.get('status') in ['saved', 'applied', 'interviewing']]
             if saved_list:
                 for job in saved_list:
                      _render_job_card(job, recommender, user_id, context="saved")
             else:
                 st.info("No saved jobs yet.")

        with tab_compare:
            st.write("Select jobs to compare side-by-side.")
            # Reuse existing comparison logic or simplified
            opts = {f"{j['job_title']} @ {j['company_name']}": j for j in raw_jobs}
            sel = st.multiselect("Select 2-3 jobs", list(opts.keys()))
            if sel:
                sel_jobs = [opts[k] for k in sel]
                cols = st.columns(len(sel_jobs))
                for idx, j in enumerate(sel_jobs):
                    with cols[idx]:
                         st.markdown(f"#### {j['company_name']}")
                         st.markdown(f"**{j['job_title']}**")
                         st.success(f"{int(j.get('match_percentage', 0))}% Match")
                         st.write(f"📍 {j['location']}")
                         st.write(f"👥 {j.get('applicant_count', 0)} applicants")
                         st.caption(j['job_description'][:150] + "...")

def _render_job_card(job, recommender, user_id, context="search"):
    """Render a single job card."""
    match = int(job.get('match_percentage', 0))
    color = "#00c853" if match > 75 else "#ffd700" if match > 50 else "#ff5252"
    status = job.get('status', 'new')
    
    # Badge logic for Saved Tab
    status_badge = ""
    if context == "saved":
        if status == 'applied':
            status_badge = f"<span style='background:#4CAF50; color:white; padding:2px 8px; border-radius:4px; font-size:0.8em; margin-left:10px'>✓ APPLIED</span>"
        elif status == 'saved':
             status_badge = f"<span style='background:#2196F3; color:white; padding:2px 8px; border-radius:4px; font-size:0.8em; margin-left:10px'>📌 SAVED</span>"

    with st.container():
        import html
        desc_text = job.get('job_description', '')
        desc = html.escape(textwrap.shorten(desc_text, width=200, placeholder='...'))
        title = html.escape(job['job_title'])
        company = html.escape(job['company_name'])
        location = html.escape(job['location'])

        # Minified HTML to prevent Markdown block interpretation
        html_content = f"""<div style="border-left: 5px solid {color}; padding: 1.5rem; background-color: #1e293b; border: 1px solid #334155; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);"><div style="display: flex; justify-content: space-between; align-items: flex-start;"><div style="flex: 1;"><a href="{job['job_url']}" target="_blank" style="text-decoration: none; color: #3b82f6; font-size: 1.25rem; font-weight: 700;">{title}</a>{status_badge}<div style="color: #f8fafc; font-size: 1.1rem; font-weight: 500; margin-top: 5px;">{company}</div><div style="color: #94a3b8; font-size: 0.95rem; margin-top: 4px;">📍 {location} &nbsp;•&nbsp; 🗓️ Posted {job.get('posted_date', 'N/A')[:10]}</div></div><div style="text-align: right; min-width: 100px; margin-left: 15px;"><span style="background-color: {color}33; color: {color}; padding: 4px 12px; border-radius: 9999px; font-weight: 600; font-size: 0.875rem;">{match}% Match</span><br><span style="display: inline-block; margin-top: 8px; font-size: 0.875rem; color: #94a3b8;">{job.get('applicant_count', 0)} applicants</span></div></div><div style="margin-top: 1rem; color: #cbd5e1; font-size: 0.95rem; line-height: 1.6;">{desc}</div></div>"""
        
        st.markdown(html_content, unsafe_allow_html=True)
        
        # Action Buttons
        c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
        
        if context == "search":
            with c1:
                # Save Button Logic
                if status != 'saved' and st.button("🔖 Save", key=f"s_{job['id']}"):
                    update_job_status(user_id, job['id'], 'saved')
                    st.rerun()
            with c2: 
                # Ignore Button Logic
                if status != 'rejected' and st.button("🚫 Ignore", key=f"i_{job['id']}"):
                    update_job_status(user_id, job['id'], 'rejected')
                    st.rerun()
            with c3:
                # Tips Logic
                if st.button("💡 Tips", key=f"t_{job['id']}"):
                    with st.spinner("Analyzing..."):
                        tips = recommender.generate_detailed_application_guide(user_id, job)
                        if tips:
                            st.session_state[f"tips_{job['id']}"] = tips
                            
        elif context == "saved":
            with c1:
                # Toggle Applied
                if status == 'saved':
                    if st.button("✅ Applied", key=f"app_{job['id']}"):
                        update_job_status(user_id, job['id'], 'applied')
                        st.rerun()
                elif status == 'applied':
                     if st.button("⏪ Undo", key=f"unapp_{job['id']}", help="Mark as Saved"):
                        update_job_status(user_id, job['id'], 'saved')
                        st.rerun()
            with c2:
                # Remove Logic
                if st.button("🗑️ Remove", key=f"rm_{job['id']}"):
                    update_job_status(user_id, job['id'], 'rejected') 
                    st.rerun()
            with c3:
                # Tips Logic for Saved
                if st.button("💡 Tips", key=f"ts_{job['id']}"):
                     with st.spinner("Analyzing..."):
                        tips = recommender.generate_detailed_application_guide(user_id, job)
                        if tips: st.session_state[f"tips_{job['id']}"] = tips
        
        # Display tips if generated
        if f"tips_{job['id']}" in st.session_state:
            t = st.session_state[f"tips_{job['id']}"]
            with st.expander("✨ AI Application Strategy", expanded=True):
                 st.write("Cover Letter Ideas:")
                 for p in t.get('cover_letter_points', []): st.write(f"- {p}")
