import streamlit as st
import json
from backend.auth import is_user_logged_in, get_logged_in_user_id
from backend.llm_analyzer import LLMAnalyzer
from utils.database import get_user_by_email, save_skills_gap_analysis, get_skills_gap_analysis, get_db_connection
import plotly.graph_objects as go
import plotly.express as px


def _normalize_gap_analysis(analysis: dict) -> dict:
    """Normalize LLM or DB record into a consistent shape for rendering.
    Expected output keys: summary, present_skills, missing_critical_skills, skill_recommendations,
    learning_roadmap, visualization_data, target_role, experience_level.
    """
    if not isinstance(analysis, dict):
        return {}

    # Pass-through: if already normalized, return as-is
    if analysis.get("summary") and analysis.get("present_skills"):
        return analysis

    target_role = analysis.get("target_role") or analysis.get(
        "summary", {}).get("target_role") or "Unknown"
    experience_level = analysis.get("experience_level") or analysis.get(
        "summary", {}).get("experience_level") or "mid"

    extracted_skills = analysis.get("extracted_skills") or {}
    industry_skills = analysis.get("industry_skills") or {}

    def _infer_category_for_skill(name: str) -> str:
        n = name.lower()
        if any(k in n for k in ["python", "java", "c++", "c ", "typescript", "javascript", "nasm", "assembly"]):
            return "Programming"
        if any(k in n for k in ["sql", "mysql", "postgres", "sqlite", "mongo"]):
            return "Database Management"
        if any(k in n for k in ["html", "css", "react", "express", "spring", "rest api", "api", "frontend", "backend"]):
            return "Web Development"
        if any(k in n for k in ["docker", "kubernetes", "cloud", "aws", "azure", "gcp"]):
            return "Cloud/DevOps"
        if any(k in n for k in ["git", "github"]):
            return "Version Control"
        if any(k in n for k in ["linux", "cli", "shell"]):
            return "System Administration"
        if any(k in n for k in ["streamlit", "pandas", "numpy", "ml", "machine learning", "data science"]):
            return "Data Science"
        if any(k in n for k in ["nasm", "assembly"]):
            return "Low-Level Programming"
        return "Other"

    # Build present skills from extracted_skills categories
    present_skills = []
    for category, items in extracted_skills.items():
        if category == "summary":
            continue
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict):
                    skill_name = it.get("skill") or str(it)
                    proficiency = str(it.get("proficiency", "unknown")).lower()
                else:
                    skill_name = str(it)
                    proficiency = "unknown"

                # Determine a more specific category if the bucket is generic
                inferred_cat = _infer_category_for_skill(skill_name)
                cat_final = inferred_cat if category in (
                    "technical", "soft_skills") else category

                # Determine if matches a requirement based on industry skills lists
                matches_requirement = False
                try:
                    if isinstance(industry_skills, dict):
                        for v in industry_skills.values():
                            if isinstance(v, list) and skill_name in v:
                                matches_requirement = True
                                break
                except Exception:
                    matches_requirement = False

                present_skills.append({
                    "skill": skill_name,
                    "category": cat_final,
                    "proficiency": proficiency,
                    "matches_requirement": matches_requirement
                })

    missing_critical = analysis.get("missing_critical_skills") or []
    missing_nice = analysis.get("missing_nice_to_have") or []
    recommendations = analysis.get("skill_recommendations") or []

    # Summary: use provided or compute basic one
    summary = analysis.get("summary") or {}
    if not summary:
        # Compute counts
        total_skills_found = len(present_skills)
        missing_critical_count = len(missing_critical)

        # Top categories for strengths
        category_counts = {}
        for s in present_skills:
            category_counts[s["category"]] = category_counts.get(
                s["category"], 0) + 1
        strength_areas = [k for k, _ in sorted(
            category_counts.items(), key=lambda x: x[1], reverse=True)[:3]]

        # Gap areas from missing critical
        gap_counts = {}
        for m in missing_critical:
            cat = m.get("category", "general")
            gap_counts[cat] = gap_counts.get(cat, 0) + 1
        gap_areas = [k for k, _ in sorted(
            gap_counts.items(), key=lambda x: x[1], reverse=True)[:3]]

        # Fallback: if gap_areas empty, infer from industry skills vs present skills
        if not gap_areas:
            present_names_by_cat = {}
            for s in present_skills:
                present_names_by_cat.setdefault(
                    s["category"], set()).add(s["skill"])
            inferred_gaps = []
            if isinstance(industry_skills, dict):
                for cat, req_list in industry_skills.items():
                    if not isinstance(req_list, list):
                        continue
                    present_set = present_names_by_cat.get(cat, set())
                    missing_in_cat = [
                        r for r in req_list if r not in present_set]
                    if missing_in_cat:
                        inferred_gaps.append(cat)
            # Include categories from missing nice-to-have as soft gaps
            for m in missing_nice:
                c = m.get("category")
                if c and c not in inferred_gaps:
                    inferred_gaps.append(c)
            gap_areas = inferred_gaps[:3]

        # Compute must-have matches from industry skills lists
        present_names = {str(s["skill"]).lower() for s in present_skills}
        required_set = set()
        if isinstance(industry_skills, dict):
            candidate_keys = [
                "must_have", "must-have", "required", "essential", "core_skills", "critical_skills"
            ]
            for k in candidate_keys:
                v = industry_skills.get(k)
                if isinstance(v, list):
                    for item in v:
                        required_set.add(str(item).lower())
            # Nested structures like requirements: { must_have: [] }
            nested = industry_skills.get("requirements")
            if isinstance(nested, dict):
                for k in candidate_keys:
                    v = nested.get(k)
                    if isinstance(v, list):
                        for item in v:
                            required_set.add(str(item).lower())
        matching_must_have = len(present_names.intersection(
            required_set)) if required_set else 0

        summary = {
            "total_skills_found": total_skills_found,
            "matching_must_have": matching_must_have,
            "missing_critical": missing_critical_count,
            "strength_areas": strength_areas,
            "gap_areas": gap_areas,
            "readiness_score": analysis.get("readiness_score", 0)
        }

    # Visualization data
    viz = analysis.get("visualization_data") or {}
    if not viz:
        skills_by_category = {}
        proficiency_distribution = {}
        for s in present_skills:
            skills_by_category[s["category"]] = skills_by_category.get(
                s["category"], 0) + 1
            prof = s.get("proficiency", "unknown").lower()
            proficiency_distribution[prof] = proficiency_distribution.get(
                prof, 0) + 1

        # Map priority to severity
        severity_map = {"high": "critical",
                        "medium": "moderate", "low": "minor"}
        gap_severity = {"critical": 0, "moderate": 0, "minor": 0}
        for m in missing_critical:
            sev = severity_map.get(
                str(m.get("priority", "low")).lower(), "minor")
            gap_severity[sev] = gap_severity.get(sev, 0) + 1

        viz = {
            "skills_by_category": skills_by_category,
            "proficiency_distribution": proficiency_distribution,
            "gap_severity": gap_severity
        }

    # Learning roadmap
    roadmap = analysis.get("learning_roadmap") or {}
    if not roadmap:
        roadmap = {
            "immediate_focus": [m.get("skill") for m in missing_critical if str(m.get("priority", "")).lower() == "high"][:5],
            "short_term": [m.get("skill") for m in missing_critical if str(m.get("priority", "")).lower() == "medium"][:5],
            "long_term": [m.get("skill") for m in missing_nice if str(m.get("priority", "")).lower() == "low"][:5]
        }

    normalized = {
        "target_role": target_role,
        "experience_level": experience_level,
        "db_id": analysis.get("id"),
        "analysis_date": analysis.get("analysis_date"),
        "summary": summary,
        "present_skills": present_skills,
        "missing_critical_skills": missing_critical,
        "skill_recommendations": recommendations,
        "learning_roadmap": roadmap,
        "visualization_data": viz,
    }

    return normalized


def skills_gap_page():
    """Skills Gap Analysis Page - Comprehensive skills analysis with recommendations."""

    if not is_user_logged_in():
        st.error("You need to be logged in to access this page.")
        st.stop()

    user_id = get_logged_in_user_id()

    st.title("🎯 Skills Gap Analysis")
    st.markdown("""
    Discover which skills you have, which ones you need, and get a personalized learning roadmap
    to advance your career.
    """)

    # Check if resume has been analyzed (extracted text exists in database)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT extracted_text FROM resume_analysis WHERE user_id = ? LIMIT 1", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row or not row[0]:
        st.warning(
            "⚠️ Please upload and analyze your resume in the Resume Analysis page first.")
        return

    # Configuration section
    st.header("📋 Analysis Configuration")

    col1, col2 = st.columns(2)

    with col1:
        target_role = st.text_input(
            "Target Job Role",
            placeholder="e.g., Backend Developer, Data Scientist",
            help="Leave empty to auto-detect from your resume"
        )

    with col2:
        experience_level = st.selectbox(
            "Experience Level",
            ["Junior", "Mid", "Senior"],
            index=1,
            help="Your current or target experience level"
        )

    # Cache control
    skip_cache = st.checkbox(
        "Force fresh analysis (skip cache)",
        value=False,
        help="Turn this on to always call the LLM and ignore saved results for the same role/level."
    )

    # Analyze button with caching (reuse last analysis for same role/level)
    if st.button("🔍 Analyze Skills Gap", type="primary", use_container_width=True):
        with st.spinner("Analyzing your skills and comparing with industry standards... This may take 2-3 minutes."):
            try:
                # Check cached analysis for same role/level
                if not skip_cache:
                    # Always load the most recent cached analysis regardless of current inputs
                    cached = get_skills_gap_analysis(user_id, limit=1)
                    if cached:
                        norm = _normalize_gap_analysis(cached)
                        st.session_state['skills_gap_analysis'] = norm
                        role_disp = norm.get('target_role', 'Unknown')
                        lvl_disp = norm.get('experience_level', 'mid')
                        st.success(f"✅ Loaded latest cached analysis (Role: {role_disp}, Level: {lvl_disp}).")
                        st.rerun()
                        return

                # Get resume text and identified skills from database
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT extracted_text, identified_skills
                    FROM resume_analysis
                    WHERE user_id = ?
                    ORDER BY analysis_timestamp DESC
                    LIMIT 1
                """, (user_id,))
                row = cursor.fetchone()
                conn.close()

                if not row or not row[0]:
                    st.error("No resume text found. Please upload and analyze your resume first in the Resume Analysis page.")
                    return

                resume_text = row[0]
                identified_skills = json.loads(row[1]) if row[1] else None

                if not identified_skills:
                    st.error("No skills found in database. Please run Resume Analysis first to extract skills.")
                    return

                # Initialize analyzer
                analyzer = LLMAnalyzer()

                # Perform skills gap analysis using pre-extracted skills
                gap_analysis = analyzer.analyze_skills_gap_from_extracted(
                    extracted_skills=identified_skills,
                    target_role=target_role if target_role else None,
                    experience_level=experience_level
                )

                if "error" in gap_analysis:
                    st.error(f"Analysis failed: {gap_analysis['error']}")
                    return

                # Save to database
                save_skills_gap_analysis(
                    user_id,
                    gap_analysis.get("target_role", target_role or "Unknown"),
                    experience_level,
                    gap_analysis
                )

                # Store in session state for display (normalized)
                st.session_state['skills_gap_analysis'] = _normalize_gap_analysis(gap_analysis)
                st.success("✅ Analysis complete!")
                st.rerun()

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                return

    st.divider()

    # Display results
    # Check for analysis in session state or database
    gap_analysis = st.session_state.get('skills_gap_analysis')

    if not gap_analysis:
        # Try to load from database
        db_analysis = get_skills_gap_analysis(user_id)
        if db_analysis:
            gap_analysis = _normalize_gap_analysis(db_analysis)
            st.session_state['skills_gap_analysis'] = gap_analysis

    if not gap_analysis:
        st.info(
            "👆 Click 'Analyze Skills Gap' to get started with your personalized skills analysis.")
        return

    # Debug: Show what data we have

    # Display Analysis Results
    display_skills_gap_results(gap_analysis)


def display_skills_gap_results(analysis):
    """Display comprehensive skills gap analysis results with visualizations."""

    # Check if analysis has error
    if "error" in analysis:
        st.error(f"Analysis Error: {analysis['error']}")
        if "raw_response" in analysis:
            with st.expander("View Raw Response"):
                st.text(analysis["raw_response"])
        return

    summary = analysis.get("summary", {})
    target_role = analysis.get("target_role", "Unknown")
    experience_level = analysis.get("experience_level", "mid")

    # Show warning if summary is empty
    if not summary:
        st.warning(
            "⚠️ Analysis completed but summary data is missing. The LLM may not have returned data in the expected format.")

    # Summary Section
    st.header(f"📊 Analysis for: {target_role} ({experience_level.title()} Level)")

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Readiness Score",
            f"{summary.get('readiness_score', 0)}%",
            delta=None
        )

    with col2:
        st.metric(
            "Total Skills",
            summary.get('total_skills_found', 0)
        )

    with col3:
        st.metric(
            "Must-Have Match",
            f"{summary.get('matching_must_have', 0)}"
        )

    with col4:
        st.metric(
            "Critical Gaps",
            summary.get('missing_critical', 0),
            delta=f"-{summary.get('missing_critical', 0)}",
            delta_color="inverse"
        )

    # Strength and Gap Areas
    col1, col2 = st.columns(2)

    with col1:
        st.success("**💪 Strength Areas:**")
        for area in summary.get('strength_areas', []):
            st.write(f"- {area}")

    with col2:
        st.warning("**🎯 Gap Areas:**")
        for area in summary.get('gap_areas', []):
            st.write(f"- {area}")

    st.divider()

    # Visualizations
    st.header("📈 Skills Visualization")

    viz_data = analysis.get("visualization_data", {})

    # Create tabs for different visualizations
    tab1, tab2, tab3 = st.tabs(
        ["Skills by Category", "Proficiency Distribution", "Gap Severity"])

    with tab1:
        if viz_data.get("skills_by_category"):
            fig = px.bar(
                x=list(viz_data["skills_by_category"].keys()),
                y=list(viz_data["skills_by_category"].values()),
                labels={"x": "Category", "y": "Number of Skills"},
                title="Skills Distribution by Category"
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        if viz_data.get("proficiency_distribution"):
            fig = px.pie(
                names=list(viz_data["proficiency_distribution"].keys()),
                values=list(viz_data["proficiency_distribution"].values()),
                title="Proficiency Level Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        if viz_data.get("gap_severity"):
            fig = px.bar(
                x=list(viz_data["gap_severity"].keys()),
                y=list(viz_data["gap_severity"].values()),
                labels={"x": "Severity", "y": "Number of Gaps"},
                title="Skills Gap Severity",
                color=list(viz_data["gap_severity"].keys()),
                color_discrete_map={"critical": "red",
                                    "moderate": "orange", "minor": "yellow"}
            )
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Present Skills
    st.header("✅ Your Current Skills")
    present_skills = analysis.get("present_skills", [])

    if present_skills:
        # Group by category
        skills_by_category = {}
        for skill in present_skills:
            category = skill.get("category", "other")
            if category not in skills_by_category:
                skills_by_category[category] = []
            skills_by_category[category].append(skill)

        for category, skills in skills_by_category.items():
            with st.expander(f"**{category.replace('_', ' ').title()}** ({len(skills)} skills)", expanded=False):
                for skill in skills:
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        st.write(f"**{skill['skill']}**")
                    with col2:
                        st.write(f"Proficiency: {skill.get('proficiency', 'N/A').title()}")
                    with col3:
                        if skill.get('matches_requirement'):
                            st.success("✓ Required")
                        else:
                            st.info("ℹ️ Bonus")

    st.divider()

    # Missing Critical Skills
    st.header("🚨 Missing Critical Skills")
    missing_critical = analysis.get("missing_critical_skills", [])

    if missing_critical:
        for skill in missing_critical:
            with st.expander(f"**{skill['skill']}** - {skill.get('category', '').replace('_', ' ').title()}", expanded=True):
                st.write(f"**Priority:** {skill.get('priority', 'N/A').upper()}")
                st.write(f"**Why Important:** {skill.get('why_important', 'N/A')}")
                st.write(f"**Learning Time:** {skill.get('typical_learning_time', 'N/A')}")
    else:
        st.success("🎉 You have all critical skills for this role!")

    st.divider()

    # Skill Recommendations
    st.header("🎓 Personalized Skill Recommendations")
    recommendations = analysis.get("skill_recommendations", [])

    if recommendations:
        # Filter by priority
        priority_filter = st.multiselect(
            "Filter by Priority",
            ["high", "medium", "low"],
            default=["high", "medium"]
        )

        filtered_recs = [r for r in recommendations if r.get("priority") in priority_filter]

        for i, rec in enumerate(filtered_recs[:10], 1):
            priority_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}

            with st.expander(
                f"{priority_color.get(rec.get('priority'), '⚪')} **{i}. {rec['skill']}** - {rec.get('category', '').replace('_', ' ').title()}",expanded=(i <= 3)
            ):
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.write(f"**Why Learn:** {rec.get('why_learn', 'N/A')}")
                    st.write(f"**Current Demand:** {rec.get('current_demand', 'N/A').title()}")

                    if rec.get('prerequisites'):
                        st.write(f"**Prerequisites:** {', '.join(rec['prerequisites'])}")

                    if rec.get('use_cases'):
                        st.write("**Use Cases:**")
                        for uc in rec['use_cases'][:3]:
                            st.write(f"  - {uc}")

                with col2:
                    st.info(
                        f"**Difficulty:** {rec.get('difficulty', 'N/A').title()}")
                    st.info(
                        f"**Learning Time:** {rec.get('estimated_learning_time', 'N/A')}")

                # Learning path
                if rec.get('learning_path'):
                    st.write("**📚 Learning Path:**")
                    for j, step in enumerate(rec['learning_path'], 1):
                        st.write(f"{j}. {step}")

                # Resources
                if rec.get('resources'):
                    st.write("**🔗 Learning Resources:**")
                    for resource in rec['resources']:
                        resource_type = resource.get(
                            'type', 'resource').title()
                        resource_name = resource.get('name', 'Resource')
                        resource_cost = resource.get('cost', 'unknown').title()
                        st.write(
                            f"- **{resource_type}:** {resource_name} ({resource_cost})")

    st.divider()

    # Learning Roadmap
    st.header("🗺️ Your Learning Roadmap")
    roadmap = analysis.get("learning_roadmap", {})

    if roadmap:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.info("**🚀 Immediate Focus (1-2 months)**")
            for skill in roadmap.get('immediate_focus', []):
                st.write(f"- {skill}")

        with col2:
            st.success("**📈 Short-term (3-6 months)**")
            for skill in roadmap.get('short_term', []):
                st.write(f"- {skill}")

        with col3:
            st.warning("**🎯 Long-term (6-12 months)**")
            for skill in roadmap.get('long_term', []):
                st.write(f"- {skill}")

    # Download option
