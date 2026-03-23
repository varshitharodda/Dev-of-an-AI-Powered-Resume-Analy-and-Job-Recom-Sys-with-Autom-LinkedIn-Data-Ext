import sqlite3
import bcrypt
import os
import json
import logging
from datetime import datetime
from typing import Optional

# Configure logging
logger = logging.getLogger(__name__)

# Relative path to the database file
DB_PATH = 'data/database.db'


def get_db_connection():
    # Ensure the parent directories exist before connecting
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
        # Ensure resumes folder exists as well
        os.makedirs(os.path.join(db_dir, 'resumes'), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():

    # Ensure data directories exist
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
        os.makedirs(os.path.join(db_dir, 'resumes'), exist_ok=True)

    conn = get_db_connection()
    cursor = conn.cursor()


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resume_file_path TEXT
    )
    """)


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resume_analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        extracted_text TEXT,
        analysis_scores TEXT,
        strengths TEXT,
        weaknesses TEXT,
        identified_skills TEXT,
        recommended_skills TEXT,
        analysis_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)
    # Ensure one analysis row per user
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_resume_analysis_user_unique ON resume_analysis (user_id)")
    
    # Skills gap analysis table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS skills_gap_analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        target_role TEXT NOT NULL,
        experience_level TEXT DEFAULT 'mid',
        extracted_skills TEXT,
        industry_skills TEXT,
        missing_critical_skills TEXT,
        missing_nice_to_have TEXT,
        skill_recommendations TEXT,
        readiness_score INTEGER,
        summary_json TEXT,
        analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)
    # Backfill for existing DBs: add summary_json if missing
    try:
        cursor.execute("ALTER TABLE skills_gap_analysis ADD COLUMN summary_json TEXT")
    except Exception:
        pass
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_skills_gap_user ON skills_gap_analysis (user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_skills_gap_date ON skills_gap_analysis (analysis_date)")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS job_recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        job_title TEXT,
        company_name TEXT,
        location TEXT,
        job_description TEXT,
        job_url TEXT,
        match_percentage REAL,
        job_analysis TEXT,
        applicant_count INTEGER,
        status TEXT DEFAULT 'new',
        posted_date TEXT,
        scraping_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)
    
    # Migrations
    try:
        cursor.execute("ALTER TABLE job_recommendations ADD COLUMN job_analysis TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE job_recommendations ADD COLUMN applicant_count INTEGER")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE job_recommendations ADD COLUMN status TEXT DEFAULT 'new'")
    except Exception:
        pass

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON resume_analysis (user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id_jobs ON job_recommendations (user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_email ON users (email)")

    # Resume Scoring History table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resume_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        overall_score INTEGER NOT NULL,
        classification TEXT NOT NULL,
        completeness_score INTEGER,
        content_quality_score INTEGER,
        formatting_score INTEGER,
        keyword_relevance_score INTEGER,
        experience_score INTEGER,
        component_scores TEXT,
        improvement_suggestions TEXT,
        scoring_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_resume_scores_user ON resume_scores (user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_resume_scores_timestamp ON resume_scores (scoring_timestamp)")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_search_preferences (
        user_id INTEGER PRIMARY KEY,
        preferences_json TEXT,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS search_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        query_summary TEXT,  -- Short text like "Python Developer in Remote"
        search_params_json TEXT, -- Full parameters used
        jobs_found_count INTEGER DEFAULT 0,
        new_jobs_count INTEGER DEFAULT 0,
        search_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_history_user ON search_history (user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_history_time ON search_history (search_timestamp)")

    conn.commit()
    conn.close()

def create_user(name, email, password, resume_file_path=None):

    conn = get_db_connection()
    cursor = conn.cursor()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    try:
        cursor.execute(
            "INSERT INTO users (name, email, password, resume_file_path) VALUES (?, ?, ?, ?)",
            (name, email, hashed_password, resume_file_path)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()
    return cursor.lastrowid

def get_user_by_email(email):

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def update_user_password(user_id, hashed_password):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_password, user_id))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating password: {e}")
        return False
    finally:
        conn.close()

def update_user_name(user_id, new_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET name = ? WHERE id = ?", (new_name, user_id))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating user name: {e}")
        return False
    finally:
        conn.close()

def save_resume_analysis(user_id, extracted_text, strengths, weaknesses, skills, suggestions, analysis_scores=None):
    """Save comprehensive resume analysis to database with proper JSON formatting.
    analysis_scores should be a JSON-serializable dict with summary metrics.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Ensure all data is properly JSON stringified
        strengths_json = json.dumps(strengths) if isinstance(strengths, (dict, list)) else (strengths if strengths else "{}")
        weaknesses_json = json.dumps(weaknesses) if isinstance(weaknesses, (dict, list)) else (weaknesses if weaknesses else "{}")
        skills_json = json.dumps(skills) if isinstance(skills, (dict, list)) else (skills if skills else "{}")
        suggestions_json = json.dumps(suggestions) if isinstance(suggestions, (dict, list)) else (suggestions if suggestions else "{}")
        
        # Prepare analysis scores JSON (single value or object)
        scores_json = json.dumps(analysis_scores if analysis_scores is not None else {})

        # Validate JSON strings
        try:
            json.loads(strengths_json)
            json.loads(weaknesses_json)
            json.loads(skills_json)
            json.loads(suggestions_json)
            json.loads(scores_json)
        except json.JSONDecodeError as je:
            logger.error(f"JSON validation error: {je}")
            return None
        
        # Upsert to guarantee a single row per user_id
        cursor.execute("""
            INSERT INTO resume_analysis 
            (user_id, extracted_text, strengths, weaknesses, identified_skills, recommended_skills, analysis_scores, analysis_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                extracted_text=excluded.extracted_text,
                strengths=excluded.strengths,
                weaknesses=excluded.weaknesses,
                identified_skills=excluded.identified_skills,
                recommended_skills=excluded.recommended_skills,
                analysis_scores=excluded.analysis_scores,
                analysis_timestamp=CURRENT_TIMESTAMP
        """, (
            user_id,
            extracted_text,
            strengths_json,
            weaknesses_json,
            skills_json,
            suggestions_json,
            scores_json
        ))
        conn.commit()
        analysis_id = cursor.lastrowid
        logger.info(f"Analysis saved successfully for user {user_id}, ID: {analysis_id}")
        return analysis_id
    except Exception as e:
        logger.error(f"Error saving resume analysis: {e}")
        return None
    finally:
        conn.close()

def get_user_analysis(user_id):
    """Retrieve the most recent comprehensive analysis for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, extracted_text, strengths, weaknesses, identified_skills, 
                   recommended_skills, analysis_scores, analysis_timestamp
            FROM resume_analysis
            WHERE user_id = ?
            ORDER BY analysis_timestamp DESC
            LIMIT 1
        """, (user_id,))
        row = cursor.fetchone()
        if row:
            return {
                "id": row["id"],
                "extracted_text": row["extracted_text"],
                "strengths": json.loads(row["strengths"]) if row["strengths"] else {},
                "weaknesses": json.loads(row["weaknesses"]) if row["weaknesses"] else {},
                "skills": json.loads(row["identified_skills"]) if row["identified_skills"] else {},
                "suggestions": json.loads(row["recommended_skills"]) if row["recommended_skills"] else {},
                "scores": json.loads(row["analysis_scores"]) if row["analysis_scores"] else {},
                "timestamp": row["analysis_timestamp"]
            }
        return None
    except Exception as e:
        logger.error(f"Error retrieving analysis: {e}")
        return None
    finally:
        conn.close()

def save_skills_gap_analysis(user_id, target_role, experience_level, gap_analysis_data):
    """Save skills gap analysis to database, caching the latest per user/role/level.
    Ensures a single record per (user_id, target_role, experience_level) by delete+insert.
    Also persists summary JSON to preserve metrics like matching_must_have.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        role_norm = (target_role or "Unknown").strip()
        level_norm = (experience_level or "mid").strip()

        extracted_skills_json = json.dumps(gap_analysis_data.get("extracted_skills", {}))
        industry_skills_json = json.dumps(gap_analysis_data.get("industry_skills", {}))
        missing_critical_json = json.dumps(gap_analysis_data.get("missing_critical_skills", []))
        missing_nice_json = json.dumps(gap_analysis_data.get("missing_nice_to_have", []))
        recommendations_json = json.dumps(gap_analysis_data.get("skill_recommendations", []))
        # Prefer direct readiness_score if provided; else fall back to summary
        readiness_score = gap_analysis_data.get("readiness_score")
        if readiness_score is None:
            readiness_score = gap_analysis_data.get("summary", {}).get("readiness_score", 0)

        # Ensure summary_json column exists (for older DBs)
        try:
            cursor.execute("ALTER TABLE skills_gap_analysis ADD COLUMN summary_json TEXT")
        except Exception:
            pass

        # Delete existing cached record for this user/role/level
        cursor.execute(
            "DELETE FROM skills_gap_analysis WHERE user_id = ? AND LOWER(target_role) = LOWER(?) AND LOWER(experience_level) = LOWER(?)",
            (user_id, role_norm, level_norm)
        )

        # Insert fresh record
        cursor.execute("""
            INSERT INTO skills_gap_analysis 
            (user_id, target_role, experience_level, extracted_skills, industry_skills,
             missing_critical_skills, missing_nice_to_have, skill_recommendations, readiness_score, summary_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            role_norm,
            level_norm,
            extracted_skills_json,
            industry_skills_json,
            missing_critical_json,
            missing_nice_json,
            recommendations_json,
            readiness_score,
            json.dumps(gap_analysis_data.get("summary", {}))
        ))
        conn.commit()
        analysis_id = cursor.lastrowid
        logger.info(f"Skills gap analysis saved (cached latest) for user {user_id}, role '{role_norm}', level '{level_norm}', ID: {analysis_id}")
        return analysis_id
    except Exception as e:
        logger.error(f"Error saving skills gap analysis: {e}")
        return None
    finally:
        conn.close()

def get_skills_gap_analysis(user_id, limit=1, target_role: Optional[str] = None, experience_level: Optional[str] = None):
    """Retrieve skills gap analysis for a user with optional role/level filters."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        conditions = ["user_id = ?"]
        params = [user_id]

        if target_role:
            conditions.append("LOWER(target_role) = LOWER(?)")
            params.append(target_role)
        if experience_level:
            conditions.append("LOWER(experience_level) = LOWER(?)")
            params.append(experience_level)

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT id, target_role, experience_level, extracted_skills, industry_skills,
                   missing_critical_skills, missing_nice_to_have, skill_recommendations,
                   readiness_score, summary_json, analysis_date
            FROM skills_gap_analysis
            WHERE {where_clause}
            ORDER BY id DESC
            LIMIT ?
        """

        params.append(limit)
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        if not rows:
            return [] if limit > 1 else None
        
        results = []
        for row in rows:
            # Support both old and new schemas (without/with summary_json)
            try:
                summary_json = json.loads(row[9]) if row[9] else {}
                analysis_date = row[10]
            except IndexError:
                summary_json = {}
                analysis_date = row[9]

            results.append({
                "id": row[0],
                "target_role": row[1],
                "experience_level": row[2],
                "extracted_skills": json.loads(row[3]) if row[3] else {},
                "industry_skills": json.loads(row[4]) if row[4] else {},
                "missing_critical_skills": json.loads(row[5]) if row[5] else [],
                "missing_nice_to_have": json.loads(row[6]) if row[6] else [],
                "skill_recommendations": json.loads(row[7]) if row[7] else [],
                "readiness_score": row[8],
                "summary": summary_json,
                "analysis_date": analysis_date
            })
        
        return results if limit > 1 else results[0]
    except Exception as e:
        logger.error(f"Error retrieving skills gap analysis: {e}")
        return [] if limit > 1 else None
    finally:
        conn.close()


# ==================== Resume Scoring Functions ====================

def save_resume_score(user_id: int, scoring_result: dict) -> Optional[int]:
    """Save resume scoring result to database.
    
    Args:
        user_id: User ID
        scoring_result: Dictionary with scoring results from ResumeScorer
        
    Returns:
        Score ID or None if error
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Extract component scores
        component_scores = scoring_result.get("component_scores", {})
        
        # Build component scores JSON
        component_scores_json = json.dumps(component_scores)
        improvement_suggestions = json.dumps(scoring_result.get("improvement_suggestions", []))
        
        cursor.execute("""
            INSERT INTO resume_scores 
            (user_id, overall_score, classification, completeness_score, content_quality_score, 
             formatting_score, keyword_relevance_score, experience_score, component_scores, improvement_suggestions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            scoring_result.get("overall_score", 0),
            scoring_result.get("classification", "Unknown"),
            component_scores.get("completeness", {}).get("score", 0),
            component_scores.get("content_quality", {}).get("score", 0),
            component_scores.get("formatting", {}).get("score", 0),
            component_scores.get("keyword_relevance", {}).get("score", 0),
            component_scores.get("experience", {}).get("score", 0),
            component_scores_json,
            improvement_suggestions
        ))
        
        conn.commit()
        score_id = cursor.lastrowid
        logger.info(f"Resume score saved successfully for user {user_id}, ID: {score_id}")
        return score_id
    except Exception as e:
        logger.error(f"Error saving resume score: {e}")
        return None
    finally:
        conn.close()


def get_resume_scores(user_id: int, limit: int = 10) -> list:
    """Retrieve resume scoring history for a user.
    
    Args:
        user_id: User ID
        limit: Number of recent scores to retrieve
        
    Returns:
        List of scoring results, most recent first
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT id, overall_score, classification, completeness_score, content_quality_score,
                   formatting_score, keyword_relevance_score, experience_score, component_scores,
                   improvement_suggestions, scoring_timestamp
            FROM resume_scores
            WHERE user_id = ?
            ORDER BY scoring_timestamp DESC
            LIMIT ?
        """, (user_id, limit))
        
        rows = cursor.fetchall()
        results = []
        
        for row in rows:
            try:
                component_scores = json.loads(row[8]) if row[8] else {}
                improvement_suggestions = json.loads(row[9]) if row[9] else []
            except json.JSONDecodeError:
                component_scores = {}
                improvement_suggestions = []
            
            results.append({
                "id": row[0],
                "overall_score": row[1],
                "classification": row[2],
                "completeness_score": row[3],
                "content_quality_score": row[4],
                "formatting_score": row[5],
                "keyword_relevance_score": row[6],
                "experience_score": row[7],
                "component_scores": component_scores,
                "improvement_suggestions": improvement_suggestions,
                "scoring_timestamp": row[10]
            })
        
        return results
    except Exception as e:
        logger.error(f"Error retrieving resume scores: {e}")
        return []
    finally:
        conn.close()


def get_latest_resume_score(user_id: int) -> Optional[dict]:
    """Get the most recent resume score for a user.
    
    Args:
        user_id: User ID
        
    Returns:
        Latest scoring result or None
    """
    scores = get_resume_scores(user_id, limit=1)
    return scores[0] if scores else None


def get_score_statistics(user_id: int) -> Optional[dict]:
    """Get scoring statistics for a user to show improvement over time.
    
    Args:
        user_id: User ID
        
    Returns:
        Dictionary with statistics
    """
    scores = get_resume_scores(user_id, limit=100)
    
    if not scores:
        return None
    
    overall_scores = [s["overall_score"] for s in scores]
    
    return {
        "total_evaluations": len(scores),
        "current_score": scores[0]["overall_score"],
        "average_score": sum(overall_scores) / len(overall_scores) if overall_scores else 0,
        "best_score": max(overall_scores) if overall_scores else 0,
        "worst_score": min(overall_scores) if overall_scores else 0,
        "score_trend": overall_scores[:10],  # Last 10 scores for trend
        "improvement": overall_scores[0] - overall_scores[-1] if len(overall_scores) > 1 else 0
    }



def save_job_listings(user_id, jobs_data):
    """
    Save multiple job listings to the database.
    jobs_data: list of dicts with keys: job_title, company_name, location, job_description, job_url, match_percentage
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    saved_count = 0
    
    try:
        for job in jobs_data:
            # Check for duplicates based on URL and User ID
            cursor.execute(
                "SELECT id FROM job_recommendations WHERE user_id = ? AND job_url = ?", 
                (user_id, job.get('job_url'))
            )
            if cursor.fetchone():
                continue

            analysis_json = json.dumps(job.get('job_analysis', {})) if job.get('job_analysis') else None

            cursor.execute("""
                INSERT INTO job_recommendations 
                (user_id, job_title, company_name, location, job_description, job_url, match_percentage, job_analysis, applicant_count, posted_date, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')
            """, (
                user_id,
                job.get('job_title'),
                job.get('company_name'),
                job.get('location'),
                job.get('job_description'),
                job.get('job_url'),
                job.get('match_percentage', 0.0),
                analysis_json,
                job.get('applicant_count', 0),
                job.get('posted_date')
            ))
            saved_count += 1
            
        conn.commit()
        logger.info(f"Saved {saved_count} new job listings for user {user_id}")
        return saved_count
    except Exception as e:
        logger.error(f"Error saving job listings: {e}")
        return 0
    finally:
        conn.close()

def get_job_recommendations(user_id, limit=None):
    """Retrieve job recommendations for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = """
            SELECT id, job_title, company_name, location, job_url, job_description, match_percentage, job_analysis, applicant_count, status, scraping_date, posted_date
            FROM job_recommendations 
            WHERE user_id = ? 
            ORDER BY scraping_date DESC 
        """
        params = [user_id]
        
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
            
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            if d.get('job_analysis'):
                try:
                    d['job_analysis'] = json.loads(d['job_analysis'])
                except:
                    d['job_analysis'] = {}
            else:
                 d['job_analysis'] = {}
            result.append(d)
        return result
    except Exception as e:
        logger.error(f"Error retrieving job recommendations: {e}")
        return []
    finally:
        conn.close()

def update_job_status(user_id, job_id, new_status):
    """Update status of a job (e.g., 'saved', 'applied', 'rejected')."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE job_recommendations SET status = ? WHERE id = ? AND user_id = ?",
            (new_status, job_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error updating job status: {e}")
        return False
    finally:
        conn.close()

def check_job_exists(user_id, job_url):
    """Check if a job already exists for the user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM job_recommendations WHERE user_id = ? AND job_url = ?", (user_id, job_url))
        return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking job existence: {e}")
        return False
    finally:
        conn.close()

def update_job_match_scores(user_id, updates):
    """
    Bulk update match scores for jobs.
    updates: list of tuples (job_id, match_percentage)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    updated_count = 0
    try:
        cursor.executemany(
            "UPDATE job_recommendations SET match_percentage = ? WHERE id = ? AND user_id = ?",
            [(score, job_id, user_id) for job_id, score in updates]
        )
        conn.commit()
        updated_count = cursor.rowcount
        return updated_count
    except Exception as e:
        logger.error(f"Error updating match scores: {e}")
        return 0
    finally:
        conn.close()

def save_user_search_preferences(user_id: int, preferences: dict) -> bool:
    """Save or update user search preferences."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        pref_json = json.dumps(preferences)
        cursor.execute("""
            INSERT INTO user_search_preferences (user_id, preferences_json, last_updated)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                preferences_json = excluded.preferences_json,
                last_updated = CURRENT_TIMESTAMP
        """, (user_id, pref_json))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error saving preferences: {e}")
        return False
    finally:
        conn.close()

def get_user_search_preferences(user_id: int) -> dict:
    """Retrieve user search preferences."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT preferences_json FROM user_search_preferences WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row and row[0]:
            return json.loads(row[0])
        return {}
    except Exception as e:
        logger.error(f"Error retrieving preferences: {e}")
        return {}
    finally:
        conn.close()

def add_search_history_entry(user_id: int, query_summary: str, params: dict, found_count: int, new_count: int):
    """Log a search event."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO search_history (user_id, query_summary, search_params_json, jobs_found_count, new_jobs_count)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, query_summary, json.dumps(params), found_count, new_count))
        conn.commit()
    except Exception as e:
        logger.error(f"Error logging search history: {e}")
    finally:
        conn.close()

def get_search_history(user_id: int, limit: int = 5) -> list:
    """Get recent search history."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, query_summary, search_params_json, jobs_found_count, new_jobs_count, search_timestamp
            FROM search_history
            WHERE user_id = ?
            ORDER BY search_timestamp DESC
            LIMIT ?
        """, (user_id, limit))
        rows = cursor.fetchall()
        
        history = []
        for row in rows:
            history.append({
                "id": row[0],
                "query_summary": row[1],
                "params": json.loads(row[2]) if row[2] else {},
                "found": row[3],
                "new": row[4],
                "timestamp": row[5]
            })
        return history
    except Exception as e:
        logger.error(f"Error getting search history: {e}")
        return []
    finally:
        conn.close()
