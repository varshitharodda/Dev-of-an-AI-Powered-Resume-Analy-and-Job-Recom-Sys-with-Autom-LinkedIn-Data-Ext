import streamlit as st
import json
import sys
import os
from datetime import datetime
import html
import pandas as pd
from io import BytesIO

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.auth import is_user_logged_in, get_logged_in_user_id, get_current_user_name
from utils.database import get_user_analysis, get_latest_resume_score
import plotly.graph_objects as go
import plotly.express as px

# Import LLMAnalyzer for improvement suggestions tab
from backend.llm_analyzer import LLMAnalyzer

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


def create_overall_score_gauge(score: int, classification: str) -> go.Figure:
    """Create a circular gauge chart for overall score."""
    color = "#00CC88" if score >= 90 else "#3366FF" if score >= 75 else "#FFAA00" if score >= 60 else "#EE4444"
    
    fig = go.Figure(data=[go.Indicator(
        mode="gauge+number",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"Overall Score - {classification}", 'font': {'size': 24}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 2},
            'bar': {'color': color, 'thickness': 0.7},
            'steps': [
                {'range': [0, 60], 'color': "#FFE6E6"},
                {'range': [60, 75], 'color': "#FFF4E6"},
                {'range': [75, 90], 'color': "#E6F3FF"},
                {'range': [90, 100], 'color': "#E6FFE6"}
            ],
            'threshold': {
                'line': {'color': "black", 'width': 3},
                'thickness': 0.75,
                'value': 90
            }
        }
    )])
    
    fig.update_layout(height=400, margin=dict(l=20, r=20, t=70, b=20))
    return fig


def create_component_bars(component_scores: dict) -> go.Figure:
    """Create horizontal bar chart for component scores."""
    components = []
    scores = []
    
    component_names = {
        "completeness": "Completeness",
        "strengths": "Strengths",
        "weaknesses": "Weaknesses",
        "skills": "Skills",
        "content_quality": "Content Quality"
    }
    
    for comp_key, comp_data in component_scores.items():
        if isinstance(comp_data, dict) and "score" in comp_data:
            components.append(component_names.get(comp_key, comp_key.title()))
            scores.append(comp_data["score"])
        elif isinstance(comp_data, (int, float)):
            components.append(component_names.get(comp_key, comp_key.title()))
            scores.append(comp_data)
    
    colors_list = ["#00CC88" if s >= 75 else "#FFAA00" if s >= 60 else "#EE4444" for s in scores]
    
    fig = go.Figure(data=[
        go.Bar(
            y=components,
            x=scores,
            orientation='h',
            marker_color=colors_list,
            text=[f"{s}%" for s in scores],
            textposition='auto',
            hovertemplate="<b>%{y}</b><br>Score: %{x}/100<extra></extra>"
        )
    ])
    
    fig.update_layout(
        title="Component Score Breakdown",
        xaxis_title="Score (0-100)",
        yaxis_title="Components",
        height=300,
        showlegend=False,
        margin=dict(l=150, r=20, t=50, b=20)
    )
    
    return fig


def create_strengths_cards(strengths: list) -> None:
    """Display strengths in attractive card format."""
    st.subheader("✅ Key Strengths")
    
    strengths = _extract_strength_list(strengths)
    if not strengths:
        st.info("No strengths data available")
        return
    
    cols = st.columns(1)
    
    for strength_item in strengths[:8]:  # Display up to 8 strengths
        with st.container():
            if isinstance(strength_item, dict):
                title = strength_item.get("strength", "Strength")
                category = strength_item.get("category", "")
                importance = strength_item.get("importance", "").upper()
                examples = strength_item.get("examples", [])
                
                col1, col2 = st.columns([0.8, 0.2])
                with col1:
                    st.markdown(f"### 🌟 {title}")
                    if category:
                        st.caption(f"**Category:** {category}")
                with col2:
                    if importance == "CRITICAL":
                        st.success(f"⭐⭐⭐ {importance}")
                    elif importance == "HIGH":
                        st.info(f"⭐⭐ {importance}")
                    else:
                        st.warning(f"⭐ {importance}")
                
                if examples:
                    st.write("**Examples:**")
                    for ex in examples[:3]:
                        st.write(f"• {ex}")
            else:
                st.markdown(f"### 🌟 {strength_item}")
            
            st.divider()


def create_weaknesses_cards(weaknesses: list) -> None:
    """Display weaknesses with severity indicators."""
    st.subheader("⚠️ Areas for Improvement")
    
    weakness_list = _extract_weakness_list(weaknesses)
    if not weakness_list:
        st.info("No weaknesses data available")
        return
    
    for weakness_item in weakness_list[:8]:  # Display up to 8 weaknesses
        with st.container():
            if isinstance(weakness_item, dict):
                title = weakness_item.get("weakness", "Issue")
                category = weakness_item.get("category", "")
                severity = weakness_item.get("severity", "minor").lower()
                location = weakness_item.get("location", "")
                fix = weakness_item.get("fix", "")
                
                col1, col2 = st.columns([0.8, 0.2])
                with col1:
                    st.markdown(f"### 📍 {title}")
                    if category:
                        st.caption(f"**Category:** {category}")
                    if location:
                        st.caption(f"**Location:** {location}")
                
                with col2:
                    if severity == "critical":
                        st.error(f"🔴 {severity.upper()}")
                    elif severity == "moderate":
                        st.warning(f"🟠 {severity.upper()}")
                    else:
                        st.info(f"🟡 {severity.upper()}")
                
                if fix:
                    st.write(f"**Fix:** {fix}")
            else:
                st.markdown(f"### 📍 {weakness_item}")
            
            st.divider()


def create_skills_tags(skills_data: dict) -> None:
    """Display skills using compact, card-style components."""
    st.subheader("🛠️ Skills Analysis")

    if not skills_data:
        st.info("No skills data available")
        return

    col1, col2 = st.columns(2)

    color_map = {"advanced": "#a855f7", "intermediate": "#60a5fa", "beginner": "#94a3b8", "expert": "#f472b6"}

    def _skill_card_html(name: str, prof: str = "") -> str:
        prof_text = str(prof).title() if prof else ""
        color = color_map.get(str(prof).lower(), "#94a3b8") if prof else "#94a3b8"
        prof_html = f"<div class='skill-badge' style='color:{color};'>{prof_text}</div>" if prof_text else ""
        return f"<div class='skill-card'><div class='skill-title'>{html.escape(name)}</div>{prof_html}</div>"

    def _priority_badge_html(priority: str) -> str:
        p = str(priority).lower()
        cls = "priority-low"
        if p == "high" or p == "critical":
            cls = "priority-high"
        elif p == "medium":
            cls = "priority-medium"
        return f"<div class='{cls}'>{str(priority).title()}</div>"

    # Identified Skills (left column)
    with col1:
        st.write("### ✅ Identified Skills")
        identified = skills_data.get("identified_skills", []) if isinstance(skills_data, dict) else []

        # Handle summaries separately
        summary_text = identified.get("summary") if isinstance(identified, dict) else None
        if summary_text:
            st.caption(summary_text)

        if identified:
            html_chunks = []
            if isinstance(identified, dict):
                for category, skills_list in identified.items():
                    if category == "summary":
                        continue
                    if not isinstance(skills_list, list):
                        continue
                    cards = []
                    pretty_cat = str(category).replace('_', ' ').title()
                    for s in skills_list:
                        if isinstance(s, dict):
                            name = s.get("skill") or s.get("name") or ""
                            prof = s.get("proficiency", "")
                        else:
                            name = str(s)
                            prof = ""
                        if not name:
                            continue
                        cards.append(_skill_card_html(name, prof))
                    if cards:
                        html_chunks.append(f"<div class='skill-section'><strong>{pretty_cat}</strong><div class='skill-grid'>{''.join(cards[:24])}</div></div>")
            elif isinstance(identified, list):
                cards = []
                for s in identified:
                    if isinstance(s, dict):
                        name = s.get("skill") or s.get("name") or ""
                        prof = s.get("proficiency", "")
                    else:
                        name = str(s)
                        prof = ""
                    if not name:
                        continue
                    cards.append(_skill_card_html(name, prof))
                if cards:
                    html_chunks.append(f"<div class='skill-grid'>{''.join(cards[:40])}</div>")

            if html_chunks:
                st.markdown(''.join(html_chunks), unsafe_allow_html=True)
            else:
                st.info("No identified skills found")
        else:
            st.info("No identified skills found")

    # Recommended Skills (right column)
    with col2:
        st.write("### 💡 Skills to Learn")
        recommended = skills_data.get("recommended_skills", []) if isinstance(skills_data, dict) else skills_data.get("suggestions", []) if isinstance(skills_data, dict) else []

        # Handle summary text
        if isinstance(recommended, dict):
            rec_summary = recommended.get("summary")
            if rec_summary:
                st.caption(rec_summary)

        if recommended:
            rec_chunks = []
            if isinstance(recommended, dict):
                for category, skills_list in recommended.items():
                    if category == "summary":
                        continue
                    if not isinstance(skills_list, list):
                        continue
                    cards = []
                    pretty_cat = str(category).replace('_', ' ').title()
                    for s in skills_list:
                        # If dict improvement format
                        if isinstance(s, dict) and (s.get("improvement") or s.get("skill") or s.get("name")):
                            name = s.get("improvement") or s.get("skill") or s.get("name") or ""
                            pr = s.get("priority", "")
                            badge = _priority_badge_html(pr) if pr else ""
                            cards.append(f"<div class='skill-card'>{html.escape(name)}{badge}</div>")
                        else:
                            if isinstance(s, dict):
                                name = s.get("skill") or s.get("name") or ""
                            else:
                                name = str(s)
                            cards.append(_skill_card_html(name, ""))
                    if cards:
                        rec_chunks.append(f"<div class='skill-section'><strong>{pretty_cat}</strong><div class='skill-grid'>{''.join(cards[:24])}</div></div>")
            elif isinstance(recommended, list):
                cards = []
                for s in recommended:
                    if isinstance(s, dict):
                        name = s.get("improvement") or s.get("skill") or s.get("name") or ""
                        pr = s.get("priority", "")
                        badge = _priority_badge_html(pr) if pr else ""
                        cards.append(f"<div class='skill-card'>{html.escape(name)}{badge}</div>")
                    else:
                        cards.append(_skill_card_html(str(s), ""))
                if cards:
                    rec_chunks.append(f"<div class='skill-grid'>{''.join(cards[:40])}</div>")

            if rec_chunks:
                st.markdown(''.join(rec_chunks), unsafe_allow_html=True)
            else:
                st.info("No additional skills recommended")
        else:
            st.info("No additional skills recommended")


def _figure_to_image(fig: go.Figure, width: int = 800, height: int = 500):
    """Convert a Plotly figure to PNG bytes if kaleido is available; otherwise return None."""
    try:
        return fig.to_image(format="png", width=width, height=height, scale=2)
    except Exception:
        return None


def create_pdf_report(analysis_data: dict, user_name: str) -> BytesIO:
    """Generate PDF report with analysis results."""
    if not HAS_REPORTLAB:
        st.error("PDF generation requires reportlab. Install with: pip install reportlab")
        return None
    
    try:
        # Create PDF
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, leftMargin=0.75*inch, rightMargin=0.75*inch)
        story = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=20,
            alignment=TA_CENTER
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2ca02c'),
            spaceAfter=10,
            spaceBefore=12
        )

        bullet_style = ParagraphStyle(
            'Bullet',
            parent=styles['Normal'],
            leftIndent=12,
            bulletIndent=6,
            spaceAfter=4
        )

        # Title
        story.append(Paragraph("Resume Analysis Report", title_style))
        story.append(Paragraph(f"Candidate: {user_name}", styles['Normal']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 0.25*inch))

        # Overall Score
        story.append(Paragraph("Overall Assessment", heading_style))
        overall_score = analysis_data.get("overall_score", "N/A")
        classification = analysis_data.get("classification", "N/A")
        story.append(Paragraph(f"<b>Overall Score:</b> {overall_score}/100", styles['Normal']))
        story.append(Paragraph(f"<b>Classification:</b> {classification}", styles['Normal']))
        story.append(Spacer(1, 0.15*inch))

        # Score gauge graphic (best-effort if kaleido is available)
        gauge_fig = create_overall_score_gauge(overall_score if isinstance(overall_score, (int, float)) else 0, classification)
        gauge_img = _figure_to_image(gauge_fig, width=800, height=500)
        if gauge_img:
            story.append(Image(BytesIO(gauge_img), width=6.5*inch, height=3.8*inch))
            story.append(Spacer(1, 0.2*inch))

        # Component Scores Table
        components = analysis_data.get("component_scores", {}) or {}
        if components:
            story.append(Paragraph("Component Scores", heading_style))
            data = [["Component", "Score", "Weight", "Weighted"]]
            for comp_name, comp_data in components.items():
                score = comp_data.get("score", "N/A") if isinstance(comp_data, dict) else comp_data
                weight = comp_data.get("weight", "-") if isinstance(comp_data, dict) else "-"
                weighted = comp_data.get("weighted_score", "-") if isinstance(comp_data, dict) else "-"
                data.append([comp_name.replace("_", " ").title(), f"{score}", weight, weighted])
            table = Table(data, colWidths=[2.5*inch, 1*inch, 1*inch, 1*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
            ]))
            story.append(table)
            story.append(Spacer(1, 0.25*inch))

            # Component scores bar chart (best-effort)
            comp_fig = create_component_bars(components)
            comp_img = _figure_to_image(comp_fig, width=900, height=500)
            if comp_img:
                story.append(Image(BytesIO(comp_img), width=6.5*inch, height=3.8*inch))
                story.append(Spacer(1, 0.25*inch))

        # Strengths
        strengths_list = _extract_strength_list(analysis_data.get("strengths", {}))
        if strengths_list:
            story.append(Paragraph("Key Strengths", heading_style))
            for i, item in enumerate(strengths_list[:8], 1):
                if isinstance(item, dict):
                    parts = [f"{i}. {item.get('strength', 'Strength')}"]
                    cat = item.get('category')
                    imp = item.get('importance')
                    if cat:
                        parts.append(f"(Category: {cat}")
                    if imp:
                        parts.append(f"Importance: {imp})" if cat else f"(Importance: {imp})")
                    story.append(Paragraph(" ".join(parts), bullet_style))
                    examples = item.get('examples')
                    if examples:
                        for ex in examples[:2]:
                            story.append(Paragraph(f"• {ex}", bullet_style))
                else:
                    story.append(Paragraph(f"{i}. {item}", bullet_style))
            story.append(Spacer(1, 0.2*inch))

        # Weaknesses
        weaknesses_list = _extract_weakness_list(analysis_data.get("weaknesses", {}))
        if weaknesses_list:
            story.append(Paragraph("Areas for Improvement", heading_style))
            for i, item in enumerate(weaknesses_list[:8], 1):
                if isinstance(item, dict):
                    text = f"{i}. {item.get('weakness', 'Issue')}"
                    sev = item.get('severity')
                    loc = item.get('location')
                    if sev:
                        text += f" (Severity: {sev})"
                    if loc:
                        text += f" [Location: {loc}]"
                    story.append(Paragraph(text, bullet_style))
                    fix = item.get('fix')
                    if fix:
                        story.append(Paragraph(f"• Fix: {fix}", bullet_style))
                else:
                    story.append(Paragraph(f"{i}. {item}", bullet_style))
            story.append(Spacer(1, 0.2*inch))

        # Skills
        skills = analysis_data.get("skills", {})
        recs = analysis_data.get("suggestions", {})
        if skills or recs:
            story.append(Paragraph("Skills Analysis", heading_style))
            # Identified skills table (wrapped to avoid overflow)
            if skills:
                rows = [["Category", "Skills"]]
                for cat, items in skills.items():
                    if isinstance(items, list):
                        rendered = ", ".join([
                            item.get('skill', str(item)) if isinstance(item, dict) else str(item)
                            for item in items
                        ])
                        rows.append([cat, Paragraph(rendered, styles['Normal'])])
                if len(rows) > 1:
                    table = Table(rows, colWidths=[2.0*inch, 4.25*inch])
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP')
                    ]))
                    story.append(table)
                    story.append(Spacer(1, 0.15*inch))
            # Recommendations
            if recs:
                story.append(Paragraph("Recommended Skills / Improvements", styles['Heading3']))
                if isinstance(recs, dict):
                    for cat, items in recs.items():
                        if cat == "summary":
                            story.append(Paragraph(f"{items}", styles['Normal']))
                            continue
                        if not isinstance(items, list):
                            continue
                        for item in items:
                            if isinstance(item, dict) and item.get('improvement'):
                                text = f"{item['improvement']}"
                                pr = item.get('priority')
                                if pr:
                                    text += f" (Priority: {pr})"
                                story.append(Paragraph(f"• {text}", bullet_style))
                            else:
                                story.append(Paragraph(f"• {item}", bullet_style))
                elif isinstance(recs, list):
                    for item in recs:
                        story.append(Paragraph(f"• {item}", bullet_style))

        # Build PDF
        doc.build(story)
        pdf_buffer.seek(0)
        return pdf_buffer
    
    except Exception as e:
        st.error(f"Error generating PDF: {str(e)}")
        return None


def _classify_score(score: int) -> str:
    """Map numeric score to classification label."""
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 60:
        return "Average"
    return "Needs Improvement"


def _extract_strength_list(strengths_data):
    """Normalize strengths payload to a list."""
    if isinstance(strengths_data, list):
        return strengths_data
    if isinstance(strengths_data, dict):
        if "strengths" in strengths_data and isinstance(strengths_data["strengths"], list):
            return strengths_data["strengths"]
        if "strength" in strengths_data and isinstance(strengths_data["strength"], list):
            return strengths_data["strength"]
        # Some models return under "items" or "data"
        for key in ("items", "data"):
            if key in strengths_data and isinstance(strengths_data[key], list):
                return strengths_data[key]
    return []


def _extract_weakness_list(weaknesses_data):
    """Normalize weaknesses payload to a list."""
    if isinstance(weaknesses_data, list):
        return weaknesses_data
    if isinstance(weaknesses_data, dict):
        if "weaknesses" in weaknesses_data and isinstance(weaknesses_data["weaknesses"], list):
            return weaknesses_data["weaknesses"]
        if "weakness" in weaknesses_data and isinstance(weaknesses_data["weakness"], list):
            return weaknesses_data["weakness"]
        for key in ("items", "data"):
            if key in weaknesses_data and isinstance(weaknesses_data[key], list):
                return weaknesses_data[key]
    return []


def analysis_page():
    """Main analysis results display page."""
    st.set_page_config(page_title="Analysis Results", layout="wide")
    
    st.title("📊 Resume Analysis Results")
    
    # Check if user is logged in
    if not is_user_logged_in():
        st.error("Please login to view analysis results.")
        return
    
    user_id = get_logged_in_user_id()
    user_name = get_current_user_name()
    
    # Get analysis data and latest score
    analysis_data = get_user_analysis(user_id)
    score_data = get_latest_resume_score(user_id)
    
    if not analysis_data:
        st.warning("📌 No analysis results found. Please analyze your resume first.")
        st.markdown("[Go to Resume Analysis →](/?page=Resume%20Analysis)")
        return
    
    # Derive scores and classification
    if score_data:
        overall_score = score_data.get("overall_score", 0)
        classification = score_data.get("classification") or _classify_score(overall_score)
        component_scores_data = score_data.get("component_scores", {}) or {}
        analysis_timestamp = score_data.get("scoring_timestamp", analysis_data.get("timestamp", "N/A"))
    else:
        # Fallback to any saved single score (legacy)
        raw_score = analysis_data.get("scores")
        overall_score = raw_score if isinstance(raw_score, int) else 0
        classification = analysis_data.get("classification") or _classify_score(overall_score)
        component_scores_data = analysis_data.get("component_scores", {}) or {}
        analysis_timestamp = analysis_data.get("timestamp", "N/A")

    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📈 Overview",
        "✅ Strengths",
        "⚠️ Weaknesses",
        "🛠️ Skills",
        "📄 Report",
        "💡 Improvement Suggestions"
    ])
    
    # ==================== Tab 1: Overview ====================
    with tab1:
        st.header("Analysis Overview")
        
        col1, col2 = st.columns(2)
        
        # Overall Score Gauge
        with col1:
            fig_gauge = create_overall_score_gauge(overall_score, classification)
            st.plotly_chart(fig_gauge, use_container_width=True)
        
        # Key Metrics
        with col2:
            st.subheader("📋 Summary")
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Overall Score", f"{overall_score}/100")
            with col_b:
                st.metric("Classification", classification)
            with col_c:
                st.caption(f"**Analysis Date:** {analysis_timestamp}")
            
            st.divider()
            
            # Quick Stats with normalized lists
            strengths_list = _extract_strength_list(analysis_data.get("strengths", {}))
            weaknesses_list = _extract_weakness_list(analysis_data.get("weaknesses", {}))
            skills_data = analysis_data.get("skills", {})
            
            strength_count = len(strengths_list)
            weakness_count = len(weaknesses_list)
            
            st.write(f"**Strengths Identified:** {strength_count}")
            st.write(f"**Areas for Improvement:** {weakness_count}")
            
            if isinstance(skills_data, dict):
                skill_count = sum(len(v) if isinstance(v, list) else 0 for v in skills_data.values())
            else:
                skill_count = len(skills_data) if isinstance(skills_data, list) else 0
            
            st.write(f"**Skills Identified:** {skill_count}")
        
        st.divider()
        
        # Component Breakdown
        st.subheader("📊 Component Scores")
        
        component_scores = component_scores_data
        if component_scores:
            fig_bars = create_component_bars(component_scores)
            st.plotly_chart(fig_bars, use_container_width=True)
        else:
            st.info("No component scores available")
    
    # ==================== Tab 2: Strengths ====================
    with tab2:
        create_strengths_cards(analysis_data.get("strengths", []))
    
    # ==================== Tab 3: Weaknesses ====================
    with tab3:
        create_weaknesses_cards(analysis_data.get("weaknesses", []))
    
    # ==================== Tab 4: Skills ====================
    with tab4:
        create_skills_tags({
            "identified_skills": analysis_data.get("skills", {}),
            "recommended_skills": analysis_data.get("suggestions", {})
        })
    
    # Prepare merged data for report generation
    report_data = {
        **analysis_data,
        "overall_score": overall_score,
        "classification": classification,
        "component_scores": component_scores_data,
        "analysis_timestamp": analysis_timestamp,
    }

    # ==================== Tab 5: Report ====================
    with tab5:
        st.header("📄 Generate Report")
        st.write("Download a comprehensive PDF report with all your analysis results.")
        if HAS_REPORTLAB:
            if st.button("📥 Download PDF Report", use_container_width=True, type="primary"):
                pdf_file = create_pdf_report(report_data, user_name)
                if pdf_file:
                    st.download_button(
                        label="📄 Click to Download",use_container_width=True,
                        data=pdf_file,
                        file_name=f"resume_analysis_{user_name.replace(' ', '_')}.pdf",
                        mime="application/pdf"
                    )
                    st.success("✅ PDF generated successfully!")
        else:
            st.warning("PDF generation not available. Install reportlab: `pip install reportlab`")

        st.write("**Quick Navigation:**")
        nav1, nav2, nav3, nav4 = st.columns(4)
        with nav1:
            if st.button("🔄 Re-analyze Resume", use_container_width=True):
                st.session_state['page'] = 'Resume Analysis'
                st.rerun()
        with nav2:
            if st.button("💼 Find Jobs", use_container_width=True):
                st.session_state['page'] = 'Job Recommendations'
                st.rerun()
        with nav3:
            if st.button("✅ Score Resume", use_container_width=True):
                st.session_state['page'] = 'Resume Scoring'
                st.rerun()
        with nav4:
            if st.button("📊 Skills Gap Analysis", use_container_width=True):
                st.session_state['page'] = 'Skills Gap Analysis'
                st.rerun()

        st.divider()
        st.subheader("💡 Next Steps")
        st.markdown("""
        1. **Review Your Strengths** - Leverage these in your applications and interviews
        2. **Address Weaknesses** - Focus on improving the areas with highest severity
        3. **Build New Skills** - Learn the recommended skills for your target role
        4. **Score Your Resume** - Get a quantitative measure of your resume quality
        5. **Apply to Jobs** - Use the job recommendations to find matching opportunities
        """)

    # ==================== Tab 6: Improvement Suggestions ====================
    with tab6:
        st.header("💡 Resume Improvement Suggestions")
        analyzer = LLMAnalyzer()
        resume_text = analysis_data.get("extracted_text") or ""
        weaknesses = _extract_weakness_list(analysis_data.get("weaknesses", {}))
        if not resume_text:
            st.info("No resume text found for suggestions.")
        else:
            redo = st.button("🔄 Redo Improvement Suggestions", use_container_width=True)
            
            # Clear previous application state on redo
            if redo:
                if "applied_suggestions" in st.session_state:
                    del st.session_state["applied_suggestions"]
                
                # Also clear the widget states to reset UI
                keys_to_clear = [k for k in st.session_state.keys() if k.startswith("radio_suggestion_")]
                for k in keys_to_clear:
                    del st.session_state[k]

            use_cache = not redo
            with st.spinner("Generating personalized improvement suggestions..." if not redo else "Regenerating improvement suggestions ..."):
                suggestions_result = analyzer.analyze_resume(
                    resume_text,
                    analyzer.get_improvement_suggestions_prompt,
                    analysis_type="improvement_suggestions",
                    use_cache=use_cache
                )
                # After a redo, always cache the new result if not errored
                if redo and "error" not in suggestions_result:
                    analyzer.cache.set(resume_text, "improvement_suggestions", suggestions_result)
            suggestions = suggestions_result.get("suggestions", [])
            if suggestions_result.get("cached") and not redo:
                st.info("Loaded from cache for this resume. Redo to refresh.")
            
            if "error" in suggestions_result:
                st.error(f"Analysis Error: {suggestions_result['error']}")
            elif not suggestions:
                st.info("No improvement suggestions available.")
            else:
                if "applied_suggestions" not in st.session_state:
                    st.session_state["applied_suggestions"] = {}
                st.markdown("**Review and apply the following improvement suggestions. Mark as 'Applied' or 'Not Relevant'.**")
                for idx, suggestion in enumerate(suggestions, 1):
                    key = f"suggestion_{idx}"
                    applied_state = st.session_state["applied_suggestions"].get(key, None)
                    # Handle suggestion as dict or string
                    if isinstance(suggestion, dict):
                        display_text = f"{idx}. {suggestion.get('change', str(suggestion))}"
                        suggestion_text = suggestion.get('change', str(suggestion))
                        before = suggestion.get('before', "(Original resume content here)")
                        after = suggestion.get('after', "(Improved version here)")
                        section_advice = suggestion.get('section_advice', "- Add quantifiable metrics to experience bullets.\n- Use strong action verbs.\n- Organize skills by category.\n- Highlight key achievements in summary.\n- Add relevant coursework or GPA in education if strong.\n- Use clear headings and consistent formatting.")
                        resources = suggestion.get('resources', [
                            "[Coursera Resume Writing Course](https://www.coursera.org/learn/resume-writing)",
                            "[Harvard Resume Guide](https://hwpi.harvard.edu/files/ocs/files/hes-resume-cover-letter-guide.pdf)",
                            "[Canva Resume Templates](https://www.canva.com/resumes/templates/)"
                        ])
                        priority = suggestion.get('priority', "High")
                        score_impact = suggestion.get('score_impact', "+5")
                    else:
                        display_text = f"{idx}. {suggestion}"
                        suggestion_text = str(suggestion)
                        before = "(Original resume content here)"
                        after = "(Improved version here)"
                        section_advice = "- Add quantifiable metrics to experience bullets.\n- Use strong action verbs.\n- Organize skills by category.\n- Highlight key achievements in summary.\n- Add relevant coursework or GPA in education if strong.\n- Use clear headings and consistent formatting."
                        resources = [
                            "[Coursera Resume Writing Course](https://www.coursera.org/learn/resume-writing)",
                            "[Harvard Resume Guide](https://hwpi.harvard.edu/files/ocs/files/hes-resume-cover-letter-guide.pdf)",
                            "[Canva Resume Templates](https://www.canva.com/resumes/templates/)"
                        ]
                        priority = "High"
                        score_impact = "+5"
                    with st.expander(display_text):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown("**Before/After Example:**")
                            st.markdown(f"- **Before:** {before}")
                            st.markdown(f"- **After:** {after}")
                            st.markdown("**Section-Specific Advice:**")
                            st.write(section_advice)
                            st.markdown("**Learning Resources:**")
                            for r in resources:
                                st.write(f"- {r}")
                        with col2:
                            st.markdown(f"**Priority:** {priority}")
                            st.markdown(f"**Estimated Score Impact:** {score_impact}")
                            applied = st.radio(
                                "Status:",
                                ("Not Reviewed", "Applied", "Not Relevant"),
                                index=0 if applied_state is None else (1 if applied_state == "Applied" else 2),
                                key=f"radio_{key}"
                            )
                            st.session_state["applied_suggestions"][key] = applied
                st.success("You can track which suggestions you have applied or skipped. This will help you improve your resume iteratively!")
