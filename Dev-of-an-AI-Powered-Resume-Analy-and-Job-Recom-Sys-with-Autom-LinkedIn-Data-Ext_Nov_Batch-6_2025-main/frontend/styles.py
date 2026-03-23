"""
Modern React-like Styling for Streamlit
"""

CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    :root {
        --bg-color: #0f172a;
        --sidebar-bg: #1e293b;
        --card-bg: #1e293b;
        --text-color: #f8fafc;
        --text-secondary: #94a3b8;
        --primary-color: #3b82f6;
        --primary-hover: #2563eb;
        --border-color: #334155;
        --success: #22c55e;
        --warning: #eab308;
        --danger: #ef4444;
    }

    /* Global Reset & Typography */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
        background-color: var(--bg-color) !important;
        color: var(--text-color) !important;
    }

    /* Streamlit Main Container */
    .stApp {
        background-color: var(--bg-color) !important;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: var(--sidebar-bg) !important;
        border-right: 1px solid var(--border-color) !important;
    }

    /* Headings */
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-color) !important;
        font-weight: 600 !important;
        letter-spacing: -0.025em !important;
    }
    
    h1 { font-size: 2.25rem !important; }
    h2 { font-size: 1.8rem !important; margin-bottom: 1rem !important; }
    h3 { font-size: 1.5rem !important; }

    /* Buttons (Primary) */
    div.stButton > button {
        background-color: var(--primary-color) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 1.2rem !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
    }

    div.stButton > button:hover {
        background-color: var(--primary-hover) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05) !important;
    }

    div.stButton > button:active {
        transform: translateY(0) !important;
    }

    /* Inputs (Text Input, Number Input, Text Area) */
    div[data-baseweb="input"] > div, 
    div[data-baseweb="textarea"] > div,
    div[data-baseweb="select"] > div {
        background-color: #334155 !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
        color: white !important;
    }

    div[data-baseweb="input"] > div:focus-within,
    div[data-baseweb="textarea"] > div:focus-within {
        border-color: var(--primary-color) !important;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3) !important;
    }
    
    input, textarea {
        color: white !important;
    }

    /* Cards / Containers */
    div[data-testid="stMetric"], div.css-1r6slb0 {
        background-color: var(--card-bg) !important;
        padding: 1rem !important;
        border-radius: 12px !important;
        border: 1px solid var(--border-color) !important;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06) !important;
    }

    /* DataFrames / Tables */
    div[data-testid="stDataFrame"] {
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
        overflow: hidden !important;
    }

    /* Alerts */
    div[data-testid="stNotification"], div[class*="stAlert"] {
        border-radius: 8px !important;
        border: none !important;
    }
    
    div.stAlert > div[role="alert"] {
        padding: 0.75rem 1rem !important;
    }

    /* Navigation / Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem !important;
        border-bottom: 1px solid var(--border-color) !important;
    }

    .stTabs [data-baseweb="tab"] {
        height: 3rem !important;
        white-space: nowrap !important;
        border: none !important;
        color: var(--text-secondary) !important;
        background-color: transparent !important;
    }

    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: var(--primary-color) !important;
        border-bottom: 2px solid var(--primary-color) !important;
    }

    /* File Uploader */
    div[data-testid="stFileUploader"] section {
        background-color: var(--card-bg) !important;
        border: 2px dashed var(--border-color) !important;
        border-radius: 12px !important;
    }
    
    div[data-testid="stFileUploader"] section:hover {
        border-color: var(--primary-color) !important;
    }

    /* Progress Bar */
    .stProgress > div > div > div > div {
        background-color: var(--primary-color) !important;
    }

    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: var(--bg-color); 
    }
    
    ::-webkit-scrollbar-thumb {
        background: #475569; 
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: #64748b; 
    }

    /* Utils */
    .text-sm { font-size: 0.875rem !important; }
    .text-gray { color: var(--text-secondary) !important; }
    .font-bold { font-weight: 700 !important; }

    /* Legacy / Custom Components Support */
    .modern-card {
        background-color: var(--card-bg) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
        margin-bottom: 1rem !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
    }
    
    .stat-value {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: var(--text-color) !important;
    }
    
    .stat-label {
        font-size: 0.875rem !important;
        color: var(--text-secondary) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        margin-top: 0.25rem !important;
    }

    /* Skill Cards */
    .skill-grid {
        display: flex !important;
        flex-wrap: wrap !important;
        gap: 10px !important;
        margin-top: 8px !important;
    }

    .skill-card {
        min-width: 140px !important;
        max-width: 260px !important;
        background: linear-gradient(180deg, rgba(255,255,255,0.01), rgba(0,0,0,0.03)) !important;
        border: 1px solid rgba(255,255,255,0.03) !important;
        padding: 10px 12px !important;
        border-radius: 10px !important;
        box-shadow: 0 6px 14px rgba(2,6,23,0.6) !important;
    }

    .skill-title {
        font-weight: 700 !important;
        color: var(--text-color) !important;
        margin-bottom: 6px !important;
    }

    .skill-badge {
        font-size: 0.85rem !important;
        opacity: 0.95 !important;
        font-weight: 700 !important;
    }

    .priority-high {
        background: linear-gradient(90deg,#dc2626,#ef4444) !important;
        color: white !important;
        padding: 4px 8px !important;
        border-radius: 999px !important;
        font-size: 0.75rem !important;
        display: inline-block !important;
        margin-top: 6px !important;
    }

    .priority-medium {
        background: linear-gradient(90deg,#f59e0b,#f97316) !important;
        color: white !important;
        padding: 4px 8px !important;
        border-radius: 999px !important;
        font-size: 0.75rem !important;
        display: inline-block !important;
        margin-top: 6px !important;
    }

    .priority-low {
        background: linear-gradient(90deg,#10b981,#34d399) !important;
        color: white !important;
        padding: 4px 8px !important;
        border-radius: 999px !important;
        font-size: 0.75rem !important;
        display: inline-block !important;
        margin-top: 6px !important;
    }

    .skill-section strong {
        display: block !important;
        margin-bottom: 6px !important;
        color: var(--text-gray) !important;
    }

</style>
"""

def apply_styles():
    import streamlit as st
    st.markdown(CSS, unsafe_allow_html=True)