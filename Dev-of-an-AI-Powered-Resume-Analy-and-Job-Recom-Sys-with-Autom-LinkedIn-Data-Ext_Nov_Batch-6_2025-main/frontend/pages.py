from frontend import dashboard, profile, resume_analysis, analysis, job_recommendations, settings, skills_gap, resume_scoring


LOGGED_IN_PAGES = {
    "Dashboard": dashboard.dashboard_page,
    "My Profile": profile.profile_page,
    "Resume Analysis": resume_analysis.analysis_page,
    "Analysis Results": analysis.analysis_page,
    "Resume Scoring": resume_scoring.scoring_page,
    "Skills Gap Analysis": skills_gap.skills_gap_page,
    "Job Recommendations": job_recommendations.recommendations_page,
    "Settings": settings.settings_page,
}

# Pages accessible when the user is not logged in
LOGGED_OUT_PAGES = {
    "Login": "frontend.login.login_page",
    "Registration": "frontend.registration.registration_page",
}
