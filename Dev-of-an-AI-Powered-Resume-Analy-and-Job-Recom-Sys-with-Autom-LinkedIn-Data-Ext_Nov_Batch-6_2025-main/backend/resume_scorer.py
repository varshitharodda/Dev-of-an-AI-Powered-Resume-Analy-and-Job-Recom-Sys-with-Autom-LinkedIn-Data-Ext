import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.llm_analyzer import LLMAnalyzer

# Configure logging
logger = logging.getLogger(__name__)


class ResumeScorer:
    """
    Comprehensive resume scoring system with multi-factor evaluation.
    
    Scoring Components:
    - Completeness Score (25%): Essential sections presence
    - Content Quality Score (30%): Action verbs, achievements, relevance
    - Formatting Score (15%): Consistency, readability, structure
    - Keyword Relevance Score (20%): Industry-relevant keywords
    - Experience Score (10%): Years, progression, role relevance
    """
    
    # Scoring weights
    WEIGHTS = {
        "completeness": 0.25,
        "content_quality": 0.30,
        "formatting": 0.15,
        "keyword_relevance": 0.20,
        "experience": 0.10
    }
    
    # Essential resume sections
    ESSENTIAL_SECTIONS = [
        "contact", "summary", "experience", "education", "skills"
    ]
    
    # Common action verbs for achievement-focused resumes
    ACTION_VERBS = {
        "leadership": ["led", "managed", "directed", "supervised", "coordinated", "spearheaded"],
        "achievement": ["achieved", "accomplished", "delivered", "completed", "executed"],
        "improvement": ["improved", "enhanced", "optimized", "streamlined", "accelerated"],
        "innovation": ["created", "designed", "developed", "invented", "pioneered"],
        "analysis": ["analyzed", "evaluated", "assessed", "identified", "determined"],
        "collaboration": ["collaborated", "partnered", "cooperated", "contributed", "supported"]
    }
    
    def __init__(self, llm_analyzer: Optional[LLMAnalyzer] = None):
        """Initialize the resume scorer with LLM analyzer."""
        self.llm = llm_analyzer or LLMAnalyzer()
        logger.info("Resume Scorer initialized")
    
    # ==================== Score Calculation Methods ====================
    
    def calculate_completeness_score(self, resume_text: str) -> Tuple[int, Dict[str, Any]]:
        """
        Calculate completeness score based on presence of essential sections.
        
        Returns:
            Tuple of (score 0-100, details dict)
        """
        details = {
            "found_sections": [],
            "missing_sections": [],
            "section_details": {}
        }
        
        resume_lower = resume_text.lower()
        found_count = 0
        
        # Check for section presence with variations
        section_patterns = {
            "contact": r"(contact|phone|email|linkedin|address)",
            "summary": r"(professional summary|summary|objective|profile)",
            "experience": r"(work experience|experience|professional experience|employment)",
            "education": r"(education|degree|university|college|school)",
            "skills": r"(skills|technical skills|competencies|expertise|proficiencies)"
        }
        
        for section, pattern in section_patterns.items():
            if re.search(pattern, resume_lower):
                details["found_sections"].append(section)
                found_count += 1
                details["section_details"][section] = "Present"
            else:
                details["missing_sections"].append(section)
                details["section_details"][section] = "Missing"
        
        # Calculate score
        score = int((found_count / len(self.ESSENTIAL_SECTIONS)) * 100)
        details["completeness_percentage"] = found_count / len(self.ESSENTIAL_SECTIONS)
        
        logger.info(f"Completeness Score: {score}/100 - Found {found_count}/{len(self.ESSENTIAL_SECTIONS)} sections")
        
        return score, details
    
    def calculate_content_quality_score(self, resume_text: str) -> Tuple[int, Dict[str, Any]]:
        """
        Calculate content quality using LLM analysis.
        Evaluates action verbs, quantifiable achievements, and relevance.
        
        Returns:
            Tuple of (score 0-100, details dict)
        """
        details = {
            "action_verbs_found": [],
            "achievement_count": 0,
            "quantifiable_achievements": 0,
            "llm_assessment": ""
        }
        
        resume_lower = resume_text.lower()
        
        # Count action verbs
        action_verb_count = 0
        found_verbs = []
        for category, verbs in self.ACTION_VERBS.items():
            for verb in verbs:
                # Count occurrences (case-insensitive)
                count = len(re.findall(r'\b' + verb + r'\b', resume_lower))
                if count > 0:
                    action_verb_count += count
                    found_verbs.append(f"{verb} ({count}x)")
        
        details["action_verbs_found"] = found_verbs
        details["action_verb_count"] = action_verb_count
        
        # Count quantifiable metrics (numbers, percentages, etc.)
        quantifiable_pattern = r'\b(?:\d+%|\$\d+[KM]?|\d+\+?(?:\s*(?:years?|months?|weeks?|days?|hours?))?)\b'
        quantifiable_count = len(re.findall(quantifiable_pattern, resume_text))
        details["quantifiable_achievements"] = quantifiable_count
        
        # Use LLM for detailed content quality assessment
        prompt = f"""
Analyze the following resume section for content quality. Evaluate on a scale of 0-100 based on:
1. Presence of action verbs (strongly preferred)
2. Quantifiable achievements and metrics
3. Relevance and impact of accomplishments
4. Clarity and specificity of achievements
5. Professional tone and language

Resume text:
{resume_text[:2000]}

Provide:
1. A score from 0-100
2. Brief explanation (2-3 sentences)
3. Top 3 strengths observed
4. Top 3 areas for improvement

Format as JSON:
{{"score": <number>, "explanation": "<text>", "strengths": ["<str1>", "<str2>", "<str3>"], "improvements": ["<imp1>", "<imp2>", "<imp3>"]}}
"""
        
        try:
            llm_response = self.llm.query(prompt)
            
            # Parse LLM response
            try:
                # Extract JSON from response
                json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                if json_match:
                    response_data = json.loads(json_match.group())
                    llm_score = response_data.get("score", 50)
                    details["llm_assessment"] = response_data.get("explanation", "")
                    details["strengths"] = response_data.get("strengths", [])
                    details["improvements"] = response_data.get("improvements", [])
                else:
                    llm_score = 50
                    details["llm_assessment"] = "Could not parse LLM response"
            except json.JSONDecodeError:
                llm_score = 50
                details["llm_assessment"] = "LLM response parsing error"
        except Exception as e:
            logger.warning(f"LLM content quality assessment failed: {e}")
            llm_score = 50
            details["llm_assessment"] = f"Assessment error: {str(e)}"
        
        # Combine metrics: 60% LLM assessment, 40% manual metrics
        action_verb_score = min(100, action_verb_count * 15)  # Scale by 15 per verb
        achievement_score = min(100, quantifiable_count * 10)  # Scale by 10 per metric
        manual_score = (action_verb_score + achievement_score) / 2
        
        score = int(llm_score * 0.6 + manual_score * 0.4)
        details["final_score"] = score
        
        logger.info(f"Content Quality Score: {score}/100 - LLM: {llm_score}, Manual: {int(manual_score)}")
        
        return score, details
    
    def calculate_formatting_score(self, resume_text: str) -> Tuple[int, Dict[str, Any]]:
        """
        Calculate formatting score based on:
        - Consistency of spacing and formatting
        - Appropriate length (1-2 pages)
        - Section structure
        - Readability metrics
        
        Returns:
            Tuple of (score 0-100, details dict)
        """
        details = {
            "text_length": len(resume_text),
            "word_count": len(resume_text.split()),
            "line_count": len(resume_text.split('\n')),
            "formatting_checks": {}
        }
        
        score_components = []
        
        # 1. Length appropriateness (400-1000 words for 1 page, 1000-2000 for 2 pages)
        word_count = details["word_count"]
        if 400 <= word_count <= 2000:
            length_score = 100
            details["formatting_checks"]["length"] = "✓ Appropriate (1-2 pages)"
        elif 200 <= word_count < 400:
            length_score = 70
            details["formatting_checks"]["length"] = "⚠ Too brief"
        elif 2000 < word_count <= 3000:
            length_score = 60
            details["formatting_checks"]["length"] = "⚠ Too lengthy"
        else:
            length_score = 40
            details["formatting_checks"]["length"] = "✗ Far from ideal length"
        
        score_components.append(length_score)
        
        # 2. Consistency of formatting (check for bullet points, dashes, etc.)
        bullet_count = len(re.findall(r'[-•*]', resume_text))
        newline_count = resume_text.count('\n')
        
        if bullet_count > 0 and newline_count > 20:
            consistency_score = 90
            details["formatting_checks"]["consistency"] = "✓ Well-structured with bullets"
        elif bullet_count > 0 or newline_count > 15:
            consistency_score = 75
            details["formatting_checks"]["consistency"] = "✓ Generally consistent"
        else:
            consistency_score = 50
            details["formatting_checks"]["consistency"] = "⚠ Could improve structure"
        
        score_components.append(consistency_score)
        
        # 3. Section clarity (proper spacing between sections)
        # Count significant line breaks (indicating section breaks)
        double_newlines = len(re.findall(r'\n\n+', resume_text))
        
        if double_newlines >= 4:
            section_clarity_score = 95
            details["formatting_checks"]["clarity"] = "✓ Clear section separation"
        elif double_newlines >= 2:
            section_clarity_score = 80
            details["formatting_checks"]["clarity"] = "✓ Good section organization"
        else:
            section_clarity_score = 50
            details["formatting_checks"]["clarity"] = "⚠ Improve section spacing"
        
        score_components.append(section_clarity_score)
        
        # 4. Avoid excessive special characters or formatting issues
        special_char_ratio = len(re.findall(r'[^a-zA-Z0-9\s\n\-•*.()\[\]]', resume_text)) / max(len(resume_text), 1)
        
        if special_char_ratio < 0.05:
            special_char_score = 95
            details["formatting_checks"]["special_chars"] = "✓ Clean formatting"
        elif special_char_ratio < 0.15:
            special_char_score = 80
            details["formatting_checks"]["special_chars"] = "✓ Acceptable"
        else:
            special_char_score = 50
            details["formatting_checks"]["special_chars"] = "⚠ Too many special characters"
        
        score_components.append(special_char_score)
        
        # Calculate average score
        score = int(sum(score_components) / len(score_components))
        
        logger.info(f"Formatting Score: {score}/100 - Length: {word_count} words, Sections: {double_newlines}")
        
        return score, details
    
    def calculate_keyword_relevance_score(self, resume_text: str, target_keywords: Optional[List[str]] = None) -> Tuple[int, Dict[str, Any]]:
        """
        Calculate keyword relevance using LLM to identify industry-relevant keywords.
        
        Args:
            resume_text: Resume content
            target_keywords: Optional list of keywords to look for
            
        Returns:
            Tuple of (score 0-100, details dict)
        """
        details = {
            "found_keywords": [],
            "keyword_count": 0,
            "missing_keywords": [],
            "industry_assessment": ""
        }
        
        # If no target keywords provided, have LLM identify relevant ones
        if not target_keywords:
            prompt = f"""
Analyze this resume and identify the top technical and professional keywords present.
Also suggest what keywords should be present based on the job context evident in the resume.

Resume:
{resume_text[:2000]}

Provide response as JSON:
{{"found_keywords": ["<kw1>", "<kw2>", ...], "missing_keywords": ["<mkw1>", "<mkw2>", ...], "industry_keywords": ["<ikw1>", "<ikw2>", ...]}}
"""
            try:
                llm_response = self.llm.query(prompt)
                json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                if json_match:
                    response_data = json.loads(json_match.group())
                    details["found_keywords"] = response_data.get("found_keywords", [])
                    details["missing_keywords"] = response_data.get("missing_keywords", [])
                    details["industry_keywords"] = response_data.get("industry_keywords", [])
                else:
                    # Fallback: extract common tech keywords
                    details["found_keywords"] = self._extract_tech_keywords(resume_text)
            except Exception as e:
                logger.warning(f"LLM keyword analysis failed: {e}")
                details["found_keywords"] = self._extract_tech_keywords(resume_text)
        else:
            # Check for provided keywords
            resume_lower = resume_text.lower()
            for keyword in target_keywords:
                if keyword.lower() in resume_lower:
                    details["found_keywords"].append(keyword)
                else:
                    details["missing_keywords"].append(keyword)
        
        # Calculate score based on keyword density
        keyword_count = len(details["found_keywords"])
        missing_count = len(details["missing_keywords"])
        
        if keyword_count == 0:
            score = 40  # Some keywords should be present
        else:
            # Score based on ratio of found to total relevant
            total_relevant = keyword_count + missing_count
            if total_relevant > 0:
                score = int((keyword_count / total_relevant) * 100)
            else:
                score = 70  # Default for found keywords without reference
        
        # Boost score if many keywords found
        if keyword_count >= 15:
            score = min(100, score + 15)
        
        details["keyword_count"] = keyword_count
        details["final_score"] = score
        
        logger.info(f"Keyword Relevance Score: {score}/100 - Found {keyword_count} keywords")
        
        return score, details
    
    def calculate_experience_score(self, resume_text: str) -> Tuple[int, Dict[str, Any]]:
        """
        Calculate experience score based on:
        - Years of experience mentioned
        - Career progression/growth
        - Relevance of roles
        
        Returns:
            Tuple of (score 0-100, details dict)
        """
        details = {
            "years_mentioned": [],
            "career_progression": "unknown",
            "role_relevance": "unknown",
            "llm_assessment": ""
        }
        
        # Extract years of experience mentions
        year_pattern = r'(\d{1,2})\s*(?:\+)?\s*(?:years?|yrs?)'
        year_matches = re.findall(year_pattern, resume_text, re.IGNORECASE)
        
        years_of_experience = 0
        if year_matches:
            # Take the highest mentioned years as total experience
            years_of_experience = max([int(y) for y in year_matches])
            details["years_mentioned"] = year_matches
        
        # Use LLM for detailed experience assessment
        prompt = f"""
Analyze the following resume for experience quality and progression.
Evaluate:
1. Total years of experience (if clear)
2. Career progression and growth (entry → mid → senior level?)
3. Relevance of roles to a coherent career path
4. Depth vs breadth of experience

Resume:
{resume_text[:2000]}

Provide response as JSON:
{{"years_detected": <number or null>, "progression": "<entry/mid/senior/unclear>", "coherence": <0-100>, "depth": <0-100>, "explanation": "<brief>"}}
"""
        
        try:
            llm_response = self.llm.query(prompt)
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                response_data = json.loads(json_match.group())
                if response_data.get("years_detected"):
                    years_of_experience = response_data["years_detected"]
                details["career_progression"] = response_data.get("progression", "unknown")
                coherence_score = response_data.get("coherence", 50)
                depth_score = response_data.get("depth", 50)
                details["llm_assessment"] = response_data.get("explanation", "")
            else:
                coherence_score = 50
                depth_score = 50
        except Exception as e:
            logger.warning(f"LLM experience assessment failed: {e}")
            coherence_score = 50
            depth_score = 50
        
        # Calculate score
        # 40% based on years, 30% on progression, 30% on coherence
        years_score = min(100, max(0, years_of_experience * 10))  # 10+ years = 100
        progression_score = {"entry": 60, "mid": 80, "senior": 95, "unclear": 50}.get(details["career_progression"], 50)
        
        score = int(years_score * 0.4 + progression_score * 0.3 + coherence_score * 0.3)
        details["years_of_experience"] = years_of_experience
        details["final_score"] = score
        
        logger.info(f"Experience Score: {score}/100 - {years_of_experience} years, {details['career_progression']} level")
        
        return score, details
    
    def _extract_tech_keywords(self, text: str) -> List[str]:
        """Extract common technical keywords from resume text."""
        # Common tech keywords to look for
        keywords_to_search = [
            "python", "java", "javascript", "c++", "c#", "go", "rust", "php",
            "react", "angular", "vue", "node", "django", "flask", "spring",
            "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
            "aws", "azure", "gcp", "docker", "kubernetes", "jenkins", "git",
            "agile", "scrum", "jira", "linux", "windows", "machine learning",
            "ai", "tensorflow", "pytorch", "pandas", "numpy", "api", "rest",
            "microservices", "cloud", "devops", "ci/cd"
        ]
        
        text_lower = text.lower()
        found = []
        for keyword in keywords_to_search:
            if keyword in text_lower:
                found.append(keyword)
        
        return found
    
    # ==================== Main Scoring Method ====================
    
    def score_resume(self, resume_text: str, target_keywords: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Calculate comprehensive resume score with all components.
        
        Args:
            resume_text: Full resume text
            target_keywords: Optional keywords specific to target role
            
        Returns:
            Dictionary with all scores and details
        """
        logger.info("Starting comprehensive resume scoring...")
        
        # Calculate individual component scores
        completeness_score, completeness_details = self.calculate_completeness_score(resume_text)
        content_quality_score, content_details = self.calculate_content_quality_score(resume_text)
        formatting_score, formatting_details = self.calculate_formatting_score(resume_text)
        keyword_score, keyword_details = self.calculate_keyword_relevance_score(resume_text, target_keywords)
        experience_score, experience_details = self.calculate_experience_score(resume_text)
        
        # Calculate weighted overall score
        overall_score = (
            completeness_score * self.WEIGHTS["completeness"] +
            content_quality_score * self.WEIGHTS["content_quality"] +
            formatting_score * self.WEIGHTS["formatting"] +
            keyword_score * self.WEIGHTS["keyword_relevance"] +
            experience_score * self.WEIGHTS["experience"]
        )
        overall_score = int(overall_score)
        
        # Classify resume
        classification = self._classify_resume(overall_score)
        
        # Compile comprehensive result
        result = {
            "overall_score": overall_score,
            "classification": classification,
            "timestamp": datetime.now().isoformat(),
            "component_scores": {
                "completeness": {
                    "score": completeness_score,
                    "weight": self.WEIGHTS["completeness"],
                    "weighted_score": int(completeness_score * self.WEIGHTS["completeness"]),
                    "details": completeness_details
                },
                "content_quality": {
                    "score": content_quality_score,
                    "weight": self.WEIGHTS["content_quality"],
                    "weighted_score": int(content_quality_score * self.WEIGHTS["content_quality"]),
                    "details": content_details
                },
                "formatting": {
                    "score": formatting_score,
                    "weight": self.WEIGHTS["formatting"],
                    "weighted_score": int(formatting_score * self.WEIGHTS["formatting"]),
                    "details": formatting_details
                },
                "keyword_relevance": {
                    "score": keyword_score,
                    "weight": self.WEIGHTS["keyword_relevance"],
                    "weighted_score": int(keyword_score * self.WEIGHTS["keyword_relevance"]),
                    "details": keyword_details
                },
                "experience": {
                    "score": experience_score,
                    "weight": self.WEIGHTS["experience"],
                    "weighted_score": int(experience_score * self.WEIGHTS["experience"]),
                    "details": experience_details
                }
            },
            "improvement_suggestions": self._generate_improvement_suggestions(
                completeness_score, content_quality_score, formatting_score, keyword_score, experience_score
            )
        }
        
        logger.info(f"Resume scoring complete - Overall Score: {overall_score}/100 ({classification})")
        
        return result
    
    def _classify_resume(self, score: int) -> str:
        """Classify resume based on score."""
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Good"
        elif score >= 60:
            return "Average"
        else:
            return "Needs Improvement"
    
    def _generate_improvement_suggestions(self, completeness: int, content: int, formatting: int, 
                                         keyword: int, experience: int) -> List[str]:
        """Generate specific improvement suggestions based on scores."""
        suggestions = []
        
        if completeness < 80:
            missing = []
            if completeness < 100:
                missing.append("Ensure all essential sections are present (contact, summary, experience, education, skills)")
        
        if content < 75:
            suggestions.append("Improve content quality by using more action verbs and adding quantifiable achievements (e.g., 'increased sales by 25%')")
        
        if formatting < 75:
            suggestions.append("Improve formatting: Use consistent bullet points, maintain proper spacing between sections, and keep to 1-2 pages")
        
        if keyword < 75:
            suggestions.append("Include more industry-relevant keywords and technical skills that match your target role")
        
        if experience < 75:
            suggestions.append("Highlight career progression and demonstrate growth in your roles; clarify years of experience")
        
        if not suggestions:
            suggestions.append("Your resume is performing well! Consider fine-tuning the weaker components for a perfect score.")
        
        return suggestions
