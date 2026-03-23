import streamlit as st
import json
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.auth import is_user_logged_in, get_logged_in_user_id, get_current_user_name
from backend.resume_parser import extract_text_from_pdf, extract_text_from_docx, clean_text
from backend.resume_scorer import ResumeScorer
from backend.llm_analyzer import LLMAnalyzer
from utils.database import (
    get_db_connection, save_resume_score, get_resume_scores, 
    get_latest_resume_score, get_score_statistics, get_user_analysis
)

import plotly.graph_objects as go
import plotly.express as px


def create_score_gauge_chart(score: int, classification: str) -> go.Figure:
    """Create a gauge chart for the overall resume score."""
    color = "green" if score >= 75 else "orange" if score >= 60 else "red"
    
    fig = go.Figure(data=[go.Indicator(
        mode="gauge+number+delta",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"Resume Score - {classification}"},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, 60], 'color': "#FFE6E6"},
                {'range': [60, 75], 'color': "#FFF4E6"},
                {'range': [75, 90], 'color': "#E6F3FF"},
                {'range': [90, 100], 'color': "#E6FFE6"}
            ],
            'threshold': {
                'line': {'color': "black", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    )])
    
    fig.update_layout(height=400)
    return fig


def create_component_scores_chart(component_scores: dict) -> go.Figure:
    """Create a bar chart showing all component scores."""
    components = []
    scores = []
    weights = []
    colors = []
    
    for component, data in component_scores.items():
        components.append(component.replace("_", " ").title())
        scores.append(data.get("score", 0))
        weights.append(f"{int(data.get('weight', 0) * 100)}%")
        
        score = data.get("score", 0)
        colors.append("green" if score >= 75 else "orange" if score >= 60 else "red")
    
    fig = go.Figure(data=[
        go.Bar(
            x=components,
            y=scores,
            marker_color=colors,
            text=[f"{s}<br>({w})" for s, w in zip(scores, weights)],
            textposition='outside',
            hovertemplate="<b>%{x}</b><br>Score: %{y}/100<extra></extra>"
        )
    ])
    
    fig.update_layout(
        title="Component Scores Breakdown",
        yaxis_title="Score (0-100)",
        xaxis_title="Components",
        height=400,
        showlegend=False
    )
    
    return fig


def create_score_trend_chart(scores: list) -> go.Figure:
    """Create a line chart showing score improvement over time."""
    if not scores:
        return None
    
    # Reverse to show oldest first
    scores_reversed = scores[::-1]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        y=[s["overall_score"] for s in scores_reversed],
        mode='lines+markers',
        name='Overall Score',
        line=dict(color='#636EFA', width=3),
        marker=dict(size=8),
        fill='tozeroy',
        fillcolor='rgba(99, 110, 250, 0.2)'
    ))
    
    # Add trend zones
    fig.add_hline(y=90, line_dash="dash", line_color="green", annotation_text="Excellent (90+)")
    fig.add_hline(y=75, line_dash="dash", line_color="blue", annotation_text="Good (75-89)")
    fig.add_hline(y=60, line_dash="dash", line_color="orange", annotation_text="Average (60-74)")
    
    fig.update_layout(
        title="Resume Score Improvement Over Time",
        yaxis_title="Score (0-100)",
        xaxis_title="Evaluation Number",
        height=400,
        hovermode='x unified'
    )
    
    return fig


def create_radar_chart(component_scores: dict) -> go.Figure:
    """Create a radar chart showing all components."""
    components = []
    scores = []
    
    for component, data in component_scores.items():
        components.append(component.replace("_", " ").title())
        scores.append(data.get("score", 0))
    
    fig = go.Figure(data=[
        go.Scatterpolar(
            r=scores,
            theta=components,
            fill='toself',
            name='Resume Scores'
        )
    ])
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )
        ),
        title="Resume Components - Radar View",
        height=500
    )
    
    return fig


def display_component_details(component_name: str, component_data: dict):
    """Display detailed information for a component."""
    with st.expander(f"📊 {component_name.replace('_', ' ').title()} Details (Score: {component_data['score']}/100)"):
        score = component_data.get("score", 0)
        weight = component_data.get("weight", 0)
        weighted_score = component_data.get("weighted_score", 0)
        details = component_data.get("details", {})
        
        # Score bar
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.progress(score / 100, text=f"{score}/100")
        with col2:
            st.metric("Weight", f"{int(weight * 100)}%")
        with col3:
            st.metric("Weighted Score", f"{weighted_score:.0f}")
        
        st.divider()
        
        # Component-specific details
        if component_name == "completeness":
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Found Sections:**")
                for section in details.get("found_sections", []):
                    st.write(f"✅ {section.title()}")
            with col2:
                st.write("**Missing Sections:**")
                missing = details.get("missing_sections", [])
                if missing:
                    for section in missing:
                        st.write(f"❌ {section.title()}")
                else:
                    st.write("✅ All sections present!")
        
        elif component_name == "content_quality":
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Action Verbs Found:**")
                verbs = details.get("action_verbs_found", [])
                if verbs:
                    for verb in verbs[:10]:
                        st.write(f"• {verb}")
                    if len(verbs) > 10:
                        st.write(f"... and {len(verbs) - 10} more")
                else:
                    st.write("⚠️ Few action verbs found")
            
            with col2:
                st.write("**Achievements:**")
                st.metric("Quantifiable Metrics", details.get("quantifiable_achievements", 0))
                st.write(f"*LLM Assessment:* {details.get('llm_assessment', 'N/A')}")
            
            if details.get("strengths"):
                st.write("**Strengths:**")
                for strength in details["strengths"]:
                    st.write(f"✅ {strength}")
            
            if details.get("improvements"):
                st.write("**Areas to Improve:**")
                for improvement in details["improvements"]:
                    st.write(f"🔄 {improvement}")
        
        elif component_name == "formatting":
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Word Count", details.get("word_count", 0))
                st.metric("Line Count", details.get("line_count", 0))
            with col2:
                st.metric("Text Length", f"{details.get('text_length', 0)} chars")
            
            st.write("**Formatting Checks:**")
            for check, result in details.get("formatting_checks", {}).items():
                st.write(f"• {check.title()}: {result}")
        
        elif component_name == "keyword_relevance":
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Found Keywords:**")
                keywords = details.get("found_keywords", [])
                if keywords:
                    for kw in keywords[:15]:
                        st.write(f"✅ {kw}")
                    if len(keywords) > 15:
                        st.write(f"... and {len(keywords) - 15} more")
                st.metric("Total Keywords", len(keywords))
            
            with col2:
                st.write("**Missing Keywords:**")
                missing = details.get("missing_keywords", [])
                if missing:
                    for kw in missing[:10]:
                        st.write(f"📌 {kw}")
                    if len(missing) > 10:
                        st.write(f"... and {len(missing) - 10} more")
                else:
                    st.write("✅ No missing keywords identified")
        
        elif component_name == "experience":
            st.write("**Experience Analysis:**")
            st.metric("Years of Experience", details.get("years_of_experience", 0))
            st.metric("Career Level", details.get("career_progression", "Unknown").title())
            
            if details.get("llm_assessment"):
                st.write(f"**Assessment:** {details['llm_assessment']}")


def scoring_page():
    """Main resume scoring page."""
    st.set_page_config(page_title="Resume Scoring", layout="wide")
    
    st.title("🎯 Resume Scoring System")
    st.markdown("""
    Get a comprehensive evaluation of your resume across multiple dimensions.
    Our AI-powered system analyzes your resume and provides detailed feedback for improvement.
    """)
    
    # Check if user is logged in
    if not is_user_logged_in():
        st.error("Please login first to access the resume scoring system.")
        return
    
    user_id = get_logged_in_user_id()
    user_name = get_current_user_name()
    
    # Initialize LLM analyzer
    try:
        llm_analyzer = LLMAnalyzer()
        scorer = ResumeScorer(llm_analyzer)
    except Exception as e:
        st.error(f"Failed to initialize scoring system: {str(e)}")
        return
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs([
        "📄 Score Your Resume",
        "📊 Score Breakdown",
        "📈 Score History",
        "💡 Improvement Tips"
    ])
    
    # ==================== Tab 1: Score Resume ====================
    with tab1:
        st.header("Score Your Resume")
        
        # Get current resume analysis
        current_analysis = get_user_analysis(user_id)
        
        if current_analysis:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("Resume Extracted")
                resume_text = current_analysis.get("extracted_text", "")
                if resume_text:
                    with st.expander("View Extracted Resume Text", expanded=False):
                        st.text_area("Resume Content", resume_text, height=300, disabled=True)
                else:
                    st.warning("No resume text found. Please upload a resume in 'Resume Analysis'.")
                    return
            
            with col2:
                st.subheader("Scoring Options")
                
                # Target keywords input
                st.write("**Optional: Specify target role keywords**")
                keywords_input = st.text_area(
                    "Enter keywords separated by commas (e.g., 'python, machine learning, aws')",
                    placeholder="Leave empty to auto-detect keywords",
                    height=100
                )
                
                target_keywords = None
                if keywords_input.strip():
                    target_keywords = [kw.strip().lower() for kw in keywords_input.split(",")]
                
                if st.button("🚀 Score Resume Now", use_container_width=True, type="primary"):
                    with st.spinner("Scoring your resume... This may take a moment..."):
                        try:
                            # Score the resume
                            scoring_result = scorer.score_resume(resume_text, target_keywords)
                            
                            # Save to database
                            score_id = save_resume_score(user_id, scoring_result)
                            
                            if score_id:
                                st.success(f"✅ Resume scored successfully! (ID: {score_id})")
                                st.session_state.latest_score = scoring_result
                                st.rerun()
                            else:
                                st.error("Failed to save scoring result.")
                        
                        except Exception as e:
                            st.error(f"Error during scoring: {str(e)}")
                            import traceback
                            st.write(traceback.format_exc())
        else:
            st.info("📌 Please upload and analyze your resume first in the 'Resume Analysis' section.")
            st.markdown("[Go to Resume Analysis →](/?page=Resume%20Analysis)")
    
    # ==================== Tab 2: Score Breakdown ====================
    with tab2:
        st.header("Score Breakdown & Analysis")
        
        # Get latest score
        latest_score = st.session_state.get("latest_score")
        if latest_score is None:
            latest_score = get_latest_resume_score(user_id)
        
        if latest_score:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Overall score gauge
                overall_score = latest_score.get("overall_score", 0)
                classification = latest_score.get("classification", "Unknown")
                
                fig_gauge = create_score_gauge_chart(overall_score, classification)
                st.plotly_chart(fig_gauge, use_container_width=True)
            
            with col2:
                st.subheader("Classification")
                col1_status, col2_status = st.columns(2)
                with col1_status:
                    st.metric("Overall Score", overall_score)
                with col2_status:
                    if classification == "Excellent":
                        st.success(f"🌟 {classification}")
                    elif classification == "Good":
                        st.info(f"👍 {classification}")
                    elif classification == "Average":
                        st.warning(f"⚠️ {classification}")
                    else:
                        st.error(f"📍 {classification}")
                
                st.divider()
                st.write(f"**Evaluation Date:**")
                st.write(latest_score.get("timestamp", "N/A"))
            
            # Component scores chart
            component_scores = latest_score.get("component_scores", {})
            
            st.divider()
            st.subheader("Component Scores")
            
            fig_bar = create_component_scores_chart(component_scores)
            st.plotly_chart(fig_bar, use_container_width=True)
            
            # Radar chart
            fig_radar = create_radar_chart(component_scores)
            st.plotly_chart(fig_radar, use_container_width=True)
            
            # Detailed component breakdown
            st.divider()
            st.subheader("Detailed Component Analysis")
            
            for component_name, component_data in component_scores.items():
                display_component_details(component_name, component_data)
        
        else:
            st.info("📌 Score your resume first to see detailed breakdown. Go to 'Score Your Resume' tab.")
    
    # ==================== Tab 3: Score History ====================
    with tab3:
        st.header("Score History & Trends")
        
        scores = get_resume_scores(user_id, limit=20)
        
        if scores:
            # Score statistics
            stats = get_score_statistics(user_id)
            
            if stats:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Current Score", f"{stats['current_score']}/100")
                with col2:
                    st.metric("Best Score", f"{stats['best_score']}/100")
                with col3:
                    st.metric("Average Score", f"{stats['average_score']:.1f}/100")
                with col4:
                    improvement = stats['improvement']
                    delta_color = "normal" if improvement >= 0 else "inverse"
                    st.metric("Improvement", f"+{improvement}" if improvement >= 0 else f"{improvement}", 
                             delta_color=delta_color)
            
            st.divider()
            
            # Score trend chart
            if len(scores) > 1:
                fig_trend = create_score_trend_chart(scores)
                st.plotly_chart(fig_trend, use_container_width=True)
            
            # Score history table
            st.subheader("Evaluation History")
            
            history_data = []
            for i, score in enumerate(scores, 1):
                history_data.append({
                    "Evaluation #": len(scores) - i + 1,
                    "Score": f"{score['overall_score']}/100",
                    "Classification": score['classification'],
                    "Components": f"C:{score['completeness_score']} | Q:{score['content_quality_score']} | F:{score['formatting_score']} | K:{score['keyword_relevance_score']} | E:{score['experience_score']}",
                    "Date": score['scoring_timestamp']
                })
            
            st.dataframe(history_data, use_container_width=True, hide_index=True)
        
        else:
            st.info("📌 No scoring history yet. Score your resume to start tracking improvements.")
    
    # ==================== Tab 4: Improvement Tips ====================
    with tab4:
        st.header("💡 Improvement Recommendations")
        
        latest_score = get_latest_resume_score(user_id)
        
        if latest_score:
            improvement_suggestions = latest_score.get("improvement_suggestions", [])
            
            st.subheader("Personalized Suggestions")
            
            for i, suggestion in enumerate(improvement_suggestions, 1):
                st.info(f"**{i}.** {suggestion}")
            
            st.divider()
            
            # Component-specific recommendations
            st.subheader("Component-Specific Focus Areas")
            
            component_scores = latest_score.get("component_scores", {})
            
            # Find lowest scoring components
            sorted_components = sorted(
                component_scores.items(),
                key=lambda x: x[1].get("score", 0)
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**🎯 Priority 1 - Lowest Scoring:**")
                if sorted_components:
                    component_name, component_data = sorted_components[0]
                    score = component_data.get("score", 0)
                    st.warning(f"{component_name.replace('_', ' ').title()}: {score}/100")
                    
                    if component_name == "completeness":
                        st.write("""
                        **Action Items:**
                        - Ensure you have all 5 essential sections
                        - Add contact information if missing
                        - Include a professional summary
                        """)
                    elif component_name == "content_quality":
                        st.write("""
                        **Action Items:**
                        - Use more action verbs (led, developed, created, etc.)
                        - Add quantifiable metrics and achievements
                        - Focus on impact and results
                        """)
                    elif component_name == "formatting":
                        st.write("""
                        **Action Items:**
                        - Keep resume to 1-2 pages
                        - Use consistent bullet point formatting
                        - Add clear section breaks
                        - Use professional fonts and spacing
                        """)
                    elif component_name == "keyword_relevance":
                        st.write("""
                        **Action Items:**
                        - Add industry-specific keywords
                        - Include technical skills relevant to target role
                        - Use standard terminology for your field
                        - Match job description keywords
                        """)
                    elif component_name == "experience":
                        st.write("""
                        **Action Items:**
                        - Clearly state years of experience
                        - Show career progression
                        - Highlight relevant roles for target position
                        - Demonstrate continuous growth
                        """)
            
            with col2:
                if len(sorted_components) > 1:
                    st.write("**🎯 Priority 2 - Second Lowest:**")
                    component_name, component_data = sorted_components[1]
                    score = component_data.get("score", 0)
                    st.warning(f"{component_name.replace('_', ' ').title()}: {score}/100")
            
            st.divider()
            
            st.write("**📚 General Best Practices:**")
            st.markdown("""
            1. **Keep it concise** - 1 page for <5 years experience, 2 pages max
            2. **Use keywords** - Include industry-specific terminology
            3. **Show achievements** - Use metrics and quantifiable results
            4. **Action verbs** - Start bullets with strong action words
            5. **Relevant only** - Include only relevant experience for the role
            6. **Professional format** - Consistent fonts, spacing, and structure
            7. **Update regularly** - Keep your resume current with latest skills
            8. **Tailor for roles** - Customize for each application
            """)
        
        else:
            st.info("📌 Score your resume first to get personalized improvement recommendations.")
