
import streamlit as st
from contextlib import contextmanager

def card_container(content, title=None, delay=0):
    """
    Renders a clean minimalist card.
    """
    with st.container():
        st.markdown(f"""
        <div class="modern-card">
            {(f'<h3 style="margin-top:0">{title}</h3>' if title else '')}
            {content}
        </div>
        """, unsafe_allow_html=True)

@contextmanager
def saas_card_context(delay=0):
    """
    Context manager for minimalist cards.
    """
    st.markdown('<div class="modern-card">', unsafe_allow_html=True)
    yield
    st.markdown('</div>', unsafe_allow_html=True)

def stat_card(label, value, icon=None, color="", delay=0):
    """
    Renders a minimalist stat block.
    """
    icon_html = f'<div style="font-size: 20px; opacity: 0.5; margin-bottom: 8px;">{icon}</div>' if icon else ''
    st.markdown(f"""
    <div class="modern-card" style="text-align: center;">
        {icon_html}
        <div class="stat-value">{value}</div>
        <div class="stat-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)

def feature_card(icon, title, description="", delay=0):
    """
    Renders a clean feature block.
    """
    st.markdown(f"""
    <div class="modern-card" style="height: 100%; display: flex; flex-direction: column; align-items: start;">
        <div style="font-size: 24px; margin-bottom: 12px;">{icon}</div>
        <div style="font-weight: 600; font-size: 16px; margin-bottom: 4px; color: #fff;">{title}</div>
        <div style="font-size: 14px; color: #a1a1aa; line-height: 1.5;">{description}</div>
    </div>
    """, unsafe_allow_html=True)
