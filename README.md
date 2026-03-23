# Dev-of-an-AI-Powered-Resume-Analy-and-Job-Recom-Sys-with-Autom-LinkedIn-Data-Ext
Developed an AI-powered resume analyzer using NLP and Streamlit to extract skills, score resumes, and perform skill gap analysis. Integrated an LLM via Ollama for intelligent insights and built a job recommendation system that suggests suitable roles based on user profiles.
# Table of Contents
Features
Project Structure
Setup & Installation
Running the Application
Resume Analysis
Resume Scoring System
Skills Gap Analysis
Job Recommendations
LLM Setup
Database Schema
Contributing
Features
✅ User Authentication: Secure registration and login with bcrypt password hashing ✅ Resume Upload: Support for PDF and DOCX file formats with validation ✅ Text Extraction: Automatic text extraction from resume files ✅ Resume Analysis: AI-powered analysis using Ollama LLM with strengths/weaknesses detection ✅ Resume Scoring System: Comprehensive multi-factor scoring with detailed breakdown (NEW) ✅ Skills Gap Analysis: Comprehensive skills extraction, industry comparison, and personalized learning roadmap ✅ Intelligent Caching: Two-level cache (memory + disk) to avoid re-analyzing identical resumes ✅ Confidence Scoring: 0-100% confidence scores on all analyses ✅ Database Storage: Persistent storage of analysis results linked to user profiles ✅ Interactive Visualizations: Plotly charts for skills distribution and gap analysis ✅ Learning Recommendations: Prioritized skill recommendations with resources and learning paths ✅ User Dashboard: Central hub for navigation, quick stats, and application tracking ✅ Job Recommendations: Personalized job recommendations based on resume analysis with specific 'Match %' ✅ Application Tracker: Track status of jobs (Saved, Applied, Rejected)

Project Structure
ResumeAnalysisAndJobRecommendationSystem/
├── app.py                          # Main Streamlit entry point
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── .env                           # Environment variables (not in git)
├── .gitignore                     # Git ignore rules
├── backend/
│   ├── __init__.py
│   ├── auth.py                    # Authentication & session management
│   ├── resume_parser.py           # PDF/DOCX text extraction
│   ├── llm_analyzer.py            # LLM-based analysis
│   ├── resume_scorer.py           # Resume scoring system
│   ├── recommendations.py         # Job matching logic
│   └── scraper.py                 # LinkedIn job scraper
├── frontend/
│   ├── __init__.py
│   ├── pages.py                   # Page routing configuration
│   ├── login.py                   # Login page
│   ├── registration.py            # Registration page
│   ├── dashboard.py               # Main dashboard
│   ├── profile.py                 # User profile page
│   ├── resume_analysis.py         # Resume analysis page
│   ├── analysis.py                # Analysis results display
│   ├── resume_scoring.py          # Resume scoring page
│   ├── skills_gap.py              # Skills gap analysis page
│   ├── job_recommendations.py     # Job recommendations page
│   └── settings.py                # User settings page
├── utils/
│   ├── __init__.py
│   └── database.py                # Database connection & CRUD operations
└── data/
    ├── database.db                # SQLite database
    └── resumes/                   # Uploaded resume files
Setup & Installation
Prerequisites
Python 3.9 or higher
pip (Python package manager)
Step 1: Clone the Repository
git clone <repository-url>
cd ResumeAnalysisAndJobRecommendationSystem
Step 2: Create a Virtual Environment
# On Windows
python -m venv .venv
.venv\Scripts\activate

# On macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
Step 3: Install Dependencies
pip install -r requirements.txt
Step 4: Set Up Environment Variables
Create a .env file in the project root directory (or copy .env.example and fill values):

# Database configuration
DB_PATH=data/database.db

# Chrome / WebDriver settings (for the LinkedIn scraper)
# Use a local Chromedriver binary path via CHROMEDRIVER_PATH (recommended for controlled deployments)
# If running Chrome/Chromium from a custom location (e.g., container), set CHROME_BINARY_PATH
# Run Chrome in headless mode for server deployments
CHROMEDRIVER_PATH=
CHROME_BINARY_PATH=
CHROME_HEADLESS=true

# Optional: LinkedIn Credentials for Scraping
LINKEDIN_EMAIL=your_email
LINKEDIN_PASSWORD=your_password

# API Keys (add as needed for future integrations)
# OPENAI_API_KEY=your_key_here
Step 5: Initialize the Database
The database is automatically initialized when the application starts.

Running the Application
Prerequisites: Start Ollama First
Ollama must be running before starting the Streamlit app. Open a terminal and run:

ollama serve
Start the Streamlit Server
streamlit run app.py
The application will be available at http://localhost:8501.

Running on Linux / Docker 🐧🐳
Linux (Ubuntu/Debian) Quick Setup
Install Chrome/Chromium and download a matching chromedriver:
sudo apt-get update
sudo apt-get install -y wget gnupg unzip ca-certificates
# Install Google Chrome
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt-get update && sudo apt-get install -y google-chrome-stable

# Download matching chromedriver for your Chrome major version
CHROME_VERSION=$(google-chrome --version | awk '{print $3}')
CHROME_MAJOR=$(echo $CHROME_VERSION | cut -d. -f1)
CHROMEDRIVER_VERSION=$(curl -sS "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_MAJOR}")
wget -q "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" -O /tmp/chromedriver.zip
unzip /tmp/chromedriver.zip -d /tmp && sudo mv /tmp/chromedriver /usr/local/bin/chromedriver && sudo chmod +x /usr/local/bin/chromedriver
rm /tmp/chromedriver.zip
Then set the env variable (in .env or shell):

export CHROMEDRIVER_PATH=/usr/local/bin/chromedriver
export CHROME_HEADLESS=true
Minimal Dockerfile Snippet
Use this snippet as a starting point for containerized deployments (installs Chrome and chromedriver at image build time):

FROM python:3.11-slim

RUN apt-get update && apt-get install -y wget gnupg unzip ca-certificates \
  && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
  && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
  && apt-get update && apt-get install -y google-chrome-stable \
  && CHROME_MAJOR=$(google-chrome --version | awk '{print $3}' | cut -d. -f1) \
  && CHROMEDRIVER_VERSION=$(curl -sS "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_MAJOR}") \
  && wget -q "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" -O /tmp/chromedriver.zip \
  && unzip /tmp/chromedriver.zip -d /usr/local/bin && chmod +x /usr/local/bin/chromedriver \
  && rm /tmp/chromedriver.zip && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver
ENV CHROME_HEADLESS=true

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
This ensures the CHROMEDRIVER_PATH and Chrome binary are available inside the container.

Resume Analysis & Strengths/Weaknesses Analyzer
Overview
AI-powered analyzer using Ollama LLM to identify resume strengths and weaknesses with detailed categorization, severity levels, and actionable recommendations.

Key Features
Strengths Identification: Highlights top 5-7 strengths with importance levels (Critical, High, Medium).
Weakness Detection: Identifies improvement areas with severity (Critical, Moderate, Minor) and location context.
Skills Extraction: Automatically parses Technical and Soft skills.
Visual Reports: Interactive charts and a downloadable PDF Report.
Resume Scoring System
Overview
Comprehensive scoring system that evaluates resumes on multiple criteria using a weighted multi-factor algorithm.

Scoring Components (Weights)
Completeness (25%): Checks for essential sections (Summary, Experience, Education, etc.).
Content Quality (30%): Analyzes action verbs, quantifiable metrics, and impact.
Formatting (15%): Evaluates structure, length, and readability.
Keyword Relevance (20%): Checks validation against industry standards.
Experience (10%): Validates career progression and timeline.
Classification
Excellent (90-100)
Good (75-89)
Average (60-74)
Needs Improvement (<60)
Skills Gap Analysis
Overview
This module bridges the gap between your current profile and your target role (e.g., "Full Stack Developer", "Data Scientist").

Features
Target Role Comparison: Compares your resume skills against the requirements of specific job roles and seniority levels (Entry, Mid, Senior).
Readiness Score: A 0-100 score indicating how qualified you are for the target role.
Missing Skills Detection:
Critical Skills: Must-haves for the role that you are missing.
Nice-to-Haves: Bonus skills to boost your candidacy.
Learning Roadmap:
Provides a structured learning path.
Recommends specific courses, project ideas, and certifications.
Estimates time to close the gap.
Job Recommendations
Overview
An intelligent job search engine that not only finds jobs but "matches" them to your resume using semantic analysis.

Features
Smart Search:

Filters: Location, Remote/Hybrid, Salary, Experience Level.
Scraper: Integrated LinkedIn scraper (Headless or Browser mode) to fetch real-time listings.
Chrome / Chromedriver: The scraper requires Chrome/Chromium and a compatible chromedriver. Configure this via the .env variables shown above:

CHROMEDRIVER_PATH to point to a local chromedriver binary (recommended for controlled deployments)
CHROME_BINARY_PATH to point to a custom Chrome/Chromium binary
For containerized deployments, ensure the container image provides headless Chrome and a compatible chromedriver or install them and set CHROMEDRIVER_PATH to the binary inside the container.

AI Match Scoring:

Instead of just keywords, the AI analyzes the context of the job description vs. your resume.
Assigns a Match % (e.g., "85% Match") to every job.
Application Guide:

Click "💡 Tips" on any job card to generate a tailored strategy.
Includes Cover Letter Points and Interview Prep Questions specific to that job description.
Application Tracker:

Save interesting jobs.
Mark as Applied or Rejected.
View your history and status in the "My Profile" page.
LLM Setup
Environment Configuration (.env)
The application uses the following LLM configuration defaults:

OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=mistral   # or llama3.2, llama2, etc.
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=3000
Supported Models
llama3.2 (Recommended for speed/quality balance)
mistral
gemma
Database Schema
The application uses SQLite with the following core tables:

users: Identity and resume file path.
resume_analysis: Stored JSON results of LLM analysis (Strengths, Weaknesses).
resume_scores: Structured scoring history with component breakdowns.
skills_gap_analysis: Cache for gap analysis sessions.
job_recommendations: Scraped jobs with match scores and user status (saved/applied).
search_history: Log of user search parameters and results counts.
CI & Tests (Recommended)
Currently the repository does not include a full CI pipeline or automated unit tests. Before deploying to production we strongly recommend:

Adding a GitHub Actions workflow to run linting (flake8/ruff), type checks (mypy), security audits (pip-audit), and tests (pytest).
Writing unit tests for core logic (authentication, DB CRUD, LLMAnalyzer with mocked HTTP responses, and recommender score calculations).
Running dependency vulnerability scans on PRs and on a schedule.
Example simple CI steps to add in .github/workflows/python.yml:

Checkout, setup Python, install from requirements.txt.
Run flake8 / ruff, mypy (if used), and pytest.
Run pip-audit and fail the job if critical vulnerabilities are found.
Adding CI will significantly reduce regressions and improve safety for production rollouts.

Contributing
Create a new branch for your feature.
Make your changes and test thoroughly.
Submit a pull request with a clear description.
