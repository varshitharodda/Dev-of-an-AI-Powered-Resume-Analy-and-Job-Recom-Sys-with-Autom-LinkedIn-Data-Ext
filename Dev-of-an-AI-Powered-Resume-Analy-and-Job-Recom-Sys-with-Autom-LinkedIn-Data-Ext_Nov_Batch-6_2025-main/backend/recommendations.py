import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import math
import re

from backend.llm_analyzer import LLMAnalyzer
from utils.database import get_user_analysis, get_job_recommendations, save_job_listings

logger = logging.getLogger(__name__)

class JobRecommender:
    def __init__(self):
        self.llm_analyzer = LLMAnalyzer()

    def _normalize_string(self, text: str) -> str:
        return text.lower().strip() if text else ""

    def _map_education_level(self, level: str) -> int:
        l = level.lower() if level else ""
        if "phd" in l or "doctorate" in l: return 4
        if "master" in l or "ms" in l or "m.s." in l or "mba" in l: return 3
        if "bachelor" in l or "bs" in l or "b.s." in l or "degree" in l: return 2
        if "associate" in l: return 1
        return 0

    def _map_seniority_level(self, level: str) -> int:
        l = level.lower() if level else ""
        if "lead" in l or "manager" in l or "principal" in l or "architect" in l: return 4
        if "senior" in l or "sr." in l: return 3
        if "mid" in l or "intermediate" in l: return 2
        if "junior" in l or "entry" in l or "associate" in l: return 1
        return 1 # Default to Junior/Entry

    def calculate_match_score(self, user_profile: Dict[str, Any], job_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate detailed match score based on weights:
        - Skills match: 50%
        - Experience match: 25%
        - Education match: 15%
        - Responsibilities match: 10%
        """
        score_breakdown = {
            "overall": 0,
            "skills_score": 0,
            "experience_score": 0,
            "education_score": 0,
            "responsibilities_score": 0,
            "matching_skills": [],
            "missing_skills": [],
            "match_analysis": ""
        }

        # --- 1. Skills Match (50%) ---
        user_skills = set()
        skills_source = user_profile.get("skills", {})
        if isinstance(skills_source, dict):
            for cat, items in skills_source.items():
                if isinstance(items, list):
                    for s in items:
                        if isinstance(s, str): user_skills.add(self._normalize_string(s))
                        elif isinstance(s, dict): user_skills.add(self._normalize_string(s.get("skill", "")))
        elif isinstance(skills_source, list):
            for s in skills_source:
                if isinstance(s, str): user_skills.add(self._normalize_string(s))

        req_skills = set([self._normalize_string(s) for s in job_analysis.get("required_skills", [])])
        nice_skills = set([self._normalize_string(s) for s in job_analysis.get("nice_to_have_skills", [])])
        
        # Calculate Intersection
        matching_set = req_skills.intersection(user_skills)
        score_breakdown["matching_skills"] = [s.title() for s in matching_set]
        score_breakdown["missing_skills"] = [s.title() for s in req_skills if s not in matching_set]
        
        if req_skills:
            # Must-have weight: 80% of skills score, Nice-to-have: 20%
            base_match = len(matching_set) / len(req_skills)
            
            bonus_match = 0
            if nice_skills:
                matching_nice = nice_skills.intersection(user_skills)
                bonus_match = len(matching_nice) / len(nice_skills)
            
            score_breakdown["skills_score"] = min(100, (base_match * 0.9 + bonus_match * 0.1) * 100)
        else:
            score_breakdown["skills_score"] = 80 # Fallback

        # --- 2. Experience Match (25%) ---
        req_years = job_analysis.get("required_experience_years", 0)
        try:
            req_years = float(req_years)
        except (ValueError, TypeError):
            # Try to extract the first number found
            try:
                import re
                match = re.search(r'(\d+(\.\d+)?)', str(req_years))
                req_years = float(match.group(1)) if match else 0.0
            except:
                req_years = 0.0

        user_years = 0
        try:
             # Try extracting from string "X years" in experience section or user profile
             # Simplified: defaulting to 2 if not found in structured data
             user_years = float(user_profile.get("years_of_experience", 2))
        except:
            user_years = 2.0

        if user_years >= req_years:
            score_breakdown["experience_score"] = 100
        else:
            diff = req_years - user_years
            penalty = diff * 20 
            score_breakdown["experience_score"] = max(0, 100 - penalty)
        
        # --- 3. Education Match (15%) ---
        req_edu_level = self._map_education_level(job_analysis.get("education_level", ""))
        user_edu_level = 2 # Default Bachelor
        
        if user_edu_level >= req_edu_level:
            score_breakdown["education_score"] = 100
        else:
            score_breakdown["education_score"] = 50 # Partial credit

        # --- 4. Responsibilities/Context Match (10%) ---
        # Lightweight keyword check from responsibilities
        resp_keywords = set()
        for r in job_analysis.get("responsibilities", []):
            resp_keywords.update(r.lower().split())
        
        # Check if these keywords appear in user's extracted text
        user_text = user_profile.get("extracted_text", "").lower()
        if resp_keywords and user_text:
            hits = sum(1 for k in resp_keywords if k in user_text)
            coverage = hits / len(resp_keywords)
            score_breakdown["responsibilities_score"] = min(100, coverage * 100 + 40) # Base 40
        else:
            score_breakdown["responsibilities_score"] = 85

        # Weighted Sum
        overall = (
            score_breakdown["skills_score"] * 0.50 +
            score_breakdown["experience_score"] * 0.25 +
            score_breakdown["education_score"] * 0.15 +
            score_breakdown["responsibilities_score"] * 0.10
        )
        score_breakdown["overall"] = round(overall, 1)

        # Match Analysis Strings
        reasons = []
        if score_breakdown["skills_score"] > 80: reasons.append("Strong skills match.")
        elif score_breakdown["skills_score"] < 50: reasons.append("Missing key skills.")
        if score_breakdown["experience_score"] == 100: reasons.append("Experience requirement met.")
        else: reasons.append(f"Gap in experience ({req_years} years req).")
        
        score_breakdown["match_analysis"] = " ".join(reasons)
        
        return score_breakdown

    def check_location(self, job_location: str, user_preferences: Dict[str, Any]) -> bool:
        """
        Check if job location matches user preferences.
        """
        preferred_locations = [self._normalize_string(l) for l in user_preferences.get("locations", [])]
        # Filter out empty strings
        preferred_locations = [p for p in preferred_locations if p]
        
        allow_remote = user_preferences.get("remote", True)
        
        normalized_job_loc = self._normalize_string(job_location)

        # 1. Remote Check
        if "remote" in normalized_job_loc:
            return allow_remote

        # 2. Location Match
        if not preferred_locations:
            return True # No preference implies anywhere is fine
        
        for pref in preferred_locations:
            if pref in normalized_job_loc or normalized_job_loc in pref:
                return True
                
        return False

    def filter_and_score_jobs(self, user_id: int, jobs: List[Dict[str, Any]], filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Process a list of jobs: score them, apply filters, and return ranked results.
        """
        if not filters: filters = {}
        
        user_analysis = get_user_analysis(user_id)
        if not user_analysis:
            logger.warning(f"No analysis found for user {user_id}")
            return []

        processed_jobs = []
        min_score = float(filters.get("min_match_score", 60.0))
        user_location_prefs = {
            "locations": filters.get("locations", []),
            "remote": filters.get("remote", True) # Corrected key from 'include_remote' to likely 'remote' based on frontend
        }
        
        # User constraints
        user_years = 2 
        user_seniority = 1 
        if user_years > 5: user_seniority = 3
        elif user_years > 2: user_seniority = 2

        seen_urls = set()

        # Date Calculator
        date_limit = None
        if filters.get("date_posted_days"):
             date_limit = datetime.now() - timedelta(days=int(filters["date_posted_days"]))

        for job in jobs:
            # 1. Deduplication
            url = job.get("job_url", "")
            if url in seen_urls: continue
            seen_urls.add(url)

            # 2. Location Filter
            if not self.check_location(job.get("location", ""), user_location_prefs):
                continue
            
            # --- NEW FILTERS ---
            # Date Filter
            if date_limit:
                 # TODO: robust parsing. For now, we trust the scraper or just skip if parsing fails
                 pass

            # 3. Validation / Parsing
            job_analysis = job.get("job_analysis", {})
            if not job_analysis:
                pass

            # Job Type Filter
            if filters.get("job_type"):
                j_type = getattr(job_analysis, 'get', lambda x,y: '')("employment_type", "").lower() 
                # Scraper might need to be updated to capture this property cleanly in 'job_analysis'
                # For now, if not present, we might be filtering strictly or loosely. 
                # Let's check 'job' metadata too
                # Assuming job_analysis has it or job root has it.
                pass 

            # 4. Seniority Filter (Enhanced)
            if filters.get("experience_level"):
                 req_level_str = job_analysis.get("seniority_level", "")
                 req_level = self._map_seniority_level(req_level_str)
                 filter_level = self._map_seniority_level(filters["experience_level"])
                 # Strict Match
                 if req_level != filter_level:
                     continue
            
            # Salary Filter
            if filters.get("salary_range"): 
                # Logic to parse "$100k - $120k" string
                pass

            # 5. Scoring
            scores = self.calculate_match_score(user_analysis, job_analysis)
            
            # 6. Threshold Filter
            if scores["overall"] < min_score:
                continue
                
            # Attach Scores
            job["match_scores"] = scores
            job["match_percentage"] = scores["overall"]
            
            processed_jobs.append(job)

        return processed_jobs

    def rank_jobs(self, jobs: List[Dict[str, Any]], sort_by: str = "match_percentage") -> List[Dict[str, Any]]:
        """
        Rank jobs with weighted scoring:
        - Match Percentage (Base)
        - Recency (Newer = better)
        - Competition (Fewer applicants = better)
        """
        now = datetime.now()

        def calculate_ranking_score(job):
            # 1. Base Match (0-100)
            base_score = float(job.get("match_percentage", 0))
            
            # 2. Recency Bonus (0-10)
            # < 24h: +10, < 3d: +5, < 7d: +2
            recency_bonus = 0
            try:
                posted = datetime.strptime(str(job.get("posted_date")), '%Y-%m-%d %H:%M:%S')
                age_hours = (now - posted).total_seconds() / 3600
                if age_hours < 24: recency_bonus = 10
                elif age_hours < 72: recency_bonus = 5
                elif age_hours < 168: recency_bonus = 2
            except: pass

            # 3. Low Competition Bonus (0-5)
            # < 10 applicants: +5, < 50: +2
            comp_bonus = 0
            try:
                applicants = int(job.get("applicant_count", 999))
                if applicants < 10: comp_bonus = 5
                elif applicants < 50: comp_bonus = 2
            except: pass

            return base_score + recency_bonus + comp_bonus

        # Sort based on criteria
        if sort_by == "match_percentage":
            return sorted(jobs, key=calculate_ranking_score, reverse=True)
            
        elif sort_by == "posted_date":
            # Date Descending
            def get_date(j):
                try: return datetime.strptime(str(j.get("posted_date")), '%Y-%m-%d %H:%M:%S').timestamp()
                except: return 0
            return sorted(jobs, key=get_date, reverse=True)
            
        elif sort_by == "applicants":
            # Applicants Ascending
            return sorted(jobs, key=lambda x: int(x.get("applicant_count", 9999)))
            
        else:
            return sorted(jobs, key=calculate_ranking_score, reverse=True)

    def group_jobs(self, jobs: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group jobs into categories based on match score."""
        groups = {
            "Featured": [],
            "Excellent": [],
            "Good": [],
            "Fair": []
        }
        
        now = datetime.now()
        
        for job in jobs:
            score = job.get("match_percentage", 0)
            
            # Featured Logic: Score > 90 OR (Score > 80 AND Posted < 24h)
            is_featured = False
            try:
                posted = datetime.strptime(str(job.get("posted_date")), '%Y-%m-%d %H:%M:%S')
                age_hours = (now - posted).total_seconds() / 3600
                if score >= 90 or (score >= 80 and age_hours < 24):
                    is_featured = True
            except:
                if score >= 90: is_featured = True
            
            if is_featured:
                groups["Featured"].append(job)
                
            # Standard Groups
            if score >= 85:
                groups["Excellent"].append(job)
            elif score >= 70:
                groups["Good"].append(job)
            elif score >= 60:
                groups["Fair"].append(job)
                
        return groups

    def generate_detailed_application_guide(self, user_id: int, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate detailed personalized application advice using LLM.
        """
        user_analysis = get_user_analysis(user_id)
        if not user_analysis:
            return {"error": "User profile not found"}
        
        resume_text = user_analysis.get("extracted_text", "")
        if not resume_text:
             resume_text = json.dumps(user_analysis.get("skills", {}))

        job_desc_str = f"Title: {job.get('job_title')}\nCompany: {job.get('company_name')}\n\nDescription:\n{job.get('raw_description', job.get('job_description', ''))}"
        
        prompt = f"""
        You are an expert career coach. Generate a highly personalized application guide for this user applying to this specific job.

        User's Resume Content:
        {resume_text[:2000]}... (truncated)

        Job Description:
        {job_desc_str[:3000]}... (truncated)

        Provide a JSON response with these keys:
        - cover_letter_points: List of 3-4 specific points to mention in the cover letter mapping user experience to job requirements.
        - resume_tweaks: List of 3 actionable resume edits (e.g. "Rename 'Project A' to 'Scalable Backend System'").
        - interview_prep: List of 3 potential interview questions and suggested angle for answering based on user's background.
        - missing_skills_strategy: Advice on how to address 1-2 missing skills found in the job description.
        - company_research: 2 specific things to research about this company/role type.

        JSON FORMAT ONLY.
        """
        
        # We reuse the LLM analyzer's raw call method or add a wrapper. 
        # Since LLMAnalyzer has specific methods, let's call analyze_resume with a custom prompt lambda.
        return self.llm_analyzer.analyze_resume(
            job_desc_str, # Input text (context)
            lambda _: prompt, # Prompt generator
            "application_guide", # Task type
            use_cache=True
        )
