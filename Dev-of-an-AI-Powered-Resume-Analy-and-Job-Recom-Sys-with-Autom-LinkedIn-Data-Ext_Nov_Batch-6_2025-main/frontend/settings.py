import streamlit as st
import os
import shutil
from backend.auth import is_user_logged_in

def settings_page():
    if not is_user_logged_in():
        st.error("You need to be logged in to access this page.")
        st.stop()
    
    st.title("⚙️ Settings")
    
    # Cache Management Section
    st.header("🗂️ Cache Management")
    
    cache_dir = "logs/.cache"
    cache_exists = os.path.exists(cache_dir)
    
    if cache_exists:
        cache_files = os.listdir(cache_dir) if os.path.isdir(cache_dir) else []
        st.write(f"**Current cache status:** {len(cache_files)} cached analysis results")
    else:
        st.write("**Current cache status:** No cache found")
    
    with st.expander("🔧 Advanced Cache Options"):
        st.info("""
        The application caches resume analysis results to improve performance and reduce API calls.
        Cache is stored separately from the database, so clearing the database won't clear cached results.
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ Clear Analysis Cache", type="primary", use_container_width=True):
                if cache_exists:
                    try:
                        shutil.rmtree(cache_dir)
                        os.makedirs(cache_dir, exist_ok=True)
                        st.success("✅ Analysis cache cleared successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error clearing cache: {e}")
                else:
                    st.warning("No cache to clear.")
        
        with col2:
            if st.button("ℹ️ View Cache Info", use_container_width=True):
                if cache_exists and cache_files:
                    st.write("**Cached files:**")
                    for file in cache_files:
                        file_path = os.path.join(cache_dir, file)
                        size = os.path.getsize(file_path)
                        st.write(f"- {file} ({size} bytes)")
                else:
                    st.info("No cached files found.")
    
    st.divider()
    
    # System Information Section
    st.header("🔧 System Information")
    
    from backend.llm_analyzer import LLMAnalyzer
    
    with st.spinner("Testing Ollama connection..."):
        try:
            analyzer = LLMAnalyzer()
            connection_status = analyzer.test_connection()
            
            if connection_status["status"] == "success":
                st.success(f"✅ {connection_status['message']}")
                with st.expander("Available Models",expanded=True):
                    for model in connection_status.get("available_models", []):
                        st.write(f"- {model}")
            elif connection_status["status"] == "warning":
                st.warning(f"⚠️ {connection_status['message']}")
                with st.expander("Available Models"):
                    for model in connection_status.get("available_models", []):
                        st.write(f"- {model}")
            else:
                st.error(f"❌ {connection_status['message']}")
        except Exception as e:
            st.error(f"❌ Error testing connection: {e}")
    
    st.divider()
    
    # About Section
    st.header("ℹ️ About")
    st.write("""
    **Resume Analysis and Job Recommendation System**
    
    This application uses AI-powered analysis to help you improve your resume and find suitable job opportunities.
    
    Features:
    - Resume analysis with strengths and weaknesses identification
    - Job recommendations based on your profile
    - Comprehensive career insights
    - Resume upload and management
    """)
