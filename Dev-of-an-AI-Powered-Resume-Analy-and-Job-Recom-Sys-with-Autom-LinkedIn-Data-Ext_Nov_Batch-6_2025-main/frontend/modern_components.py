"""
Modern Components for Resume Analysis Application.
Designed to mimic high-quality React UI components.
"""

import streamlit as st
import time

class ModernUI:
    @staticmethod
    def apply_custom_theme():
        from frontend.styles import apply_styles
        apply_styles()

    @staticmethod
    def card(title, content, icon="📄", key=None):
        """
        Renders a card-like container.
        """
        st.markdown(
            f"""
            <div style="
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 1.5rem;
                margin-bottom: 1rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            ">
                <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                    <span style="font-size: 1.5rem; margin-right: 0.75rem;">{icon}</span>
                    <h3 style="margin: 0; font-size: 1.25rem; font-weight: 600; color: #f8fafc;">{title}</h3>
                </div>
                <div style="color: #cbd5e1; font-size: 0.95rem; line-height: 1.6;">
                    {content}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    @staticmethod
    def metric_card(label, value, delta=None, color="primary"):
        """
        Renders a statistic/metric card similar to a dashboard widget.
        """
        delta_html = ""
        if delta:
            delta_color = "#22c55e" if "+" in delta or "up" in delta.lower() else "#ef4444"
            delta_html = f'<span style="color: {delta_color}; font-size: 0.875rem; font-weight: 500; margin-left: 0.5rem;">{delta}</span>'

        st.markdown(
            f"""
            <div style="
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 1.25rem;
                display: flex;
                flex-direction: column;
            ">
                <span style="color: #94a3b8; font-size: 0.875rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em;">{label}</span>
                <div style="display: flex; align-items: baseline; margin-top: 0.5rem;">
                    <span style="color: #f8fafc; font-size: 2rem; font-weight: 700;">{value}</span>
                    {delta_html}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    @staticmethod
    def header(title, subtitle=None):
        """
        Renders a page header.
        """
        st.markdown(f'<h1 style="margin-bottom: 0.5rem;">{title}</h1>', unsafe_allow_html=True)
        if subtitle:
            st.markdown(f'<p style="color: #94a3b8; font-size: 1.1rem; margin-top: 0; margin-bottom: 2rem;">{subtitle}</p>', unsafe_allow_html=True)
        else:
             st.markdown('<div style="margin-bottom: 2rem;"></div>', unsafe_allow_html=True)

    @staticmethod
    def divider():
        st.markdown('<hr style="border-color: #334155; margin: 2rem 0;">', unsafe_allow_html=True)

    @staticmethod
    def skill_chip(label, level=None):
        """
        Renders a skill chip/badge.
        """
        level_indicator = ""
        if level:
            # Simple dot indicator for level
             level_indicator = f'<span style="margin-left: 6px; opacity: 0.7;">• {level}</span>'

        st.markdown(
            f"""
            <span style="
                display: inline-flex;
                align-items: center;
                background-color: #334155;
                color: #e2e8f0;
                padding: 0.25rem 0.75rem;
                border-radius: 9999px;
                font-size: 0.875rem;
                font-weight: 500;
                margin-right: 0.5rem;
                margin-bottom: 0.5rem;
                border: 1px solid #475569;
            ">
                {label}
                {level_indicator}
            </span>
            """,
            unsafe_allow_html=True
        )

def init_modern_ui():
    ModernUI.apply_custom_theme()