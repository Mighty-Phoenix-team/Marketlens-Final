import streamlit as st


def apply_styles():
    st.markdown(
        """
        <style>
            .block-container {
                max-width: 1180px;
                padding-top: 2rem;
                padding-bottom: 4rem;
            }

            [data-testid="stSidebar"] {
                border-right: 1px solid rgba(128, 128, 128, 0.18);
            }

            h1 {
                letter-spacing: -0.035em;
            }

            h2, h3 {
                letter-spacing: -0.02em;
            }

            .muted {
                opacity: 0.65;
                font-size: 0.9rem;
            }

            .eyebrow {
                opacity: 0.55;
                font-size: 0.72rem;
                font-weight: 600;
                letter-spacing: 0.08em;
                text-transform: uppercase;
            }

            .score {
                font-size: 1.7rem;
                font-weight: 600;
                letter-spacing: -0.03em;
            }

            div[data-testid="stMetric"] {
                background: transparent;
                border: 0;
                padding: 0;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )