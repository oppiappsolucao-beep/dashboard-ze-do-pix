import re
import unicodedata
from datetime import datetime, date, timedelta

import gspread
import pandas as pd
import plotly.express as px
import streamlit as st
from google.oauth2.service_account import Credentials

# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------

st.set_page_config(
    page_title="Dashboard — Zé do Pix",
    page_icon="💸",
    layout="wide"
)

APP_USER = "operacao"
APP_PASS = "100316"

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1jZwhiehWGGqVNucPIB7URzrhg_-vASpwFJtgg1mI5Mg/edit?usp=sharing"
WORKSHEET_NAME = "Página1"

# ---------------------------------------------------
# LOGIN
# ---------------------------------------------------

def ensure_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if st.session_state.logged_in:
        return True

    st.markdown(
        """
        <style>
            .stApp {
                background: #f5f7fb;
            }
            .login-wrap {
                max-width: 440px;
                margin: 8vh auto 0 auto;
                padding: 0 14px;
                font-family: Inter, system-ui, -apple-system, Segoe UI, Arial, sans-serif;
            }
            .login-card {
                background: #ffffff;
                border-radius: 22px;
                padding: 32px 28px 28px 28px;
                box-shadow: 0 10px 30px rgba(16, 24, 40, 0.08);
                border: 1px solid rgba(15, 23, 42, 0.06);
            }
            .login-title {
                text-align: center;
                font-size: 32px;
                font-weight: 800;
                color: #0f2d5c;
                margin-bottom: 8px;
            }
            .login-subtitle {
                text-align: center;
                color: #667085;
                font-size: 15px;
                margin-bottom: 24px;
            }
            .login-footer {
                text-align: center;
                color: #98a2b3;
                font-size: 12px;
                margin-top: 12px;
            }
            .stTextInput > div > div > input {
                border-radius: 12px !important;
                border: 1px solid #d0d5dd !important;
                padding: 12px 14px !important;
                font-size: 15px !important;
            }
            .stButton > button,
            div[data-testid="stFormSubmitButton"] > button {
                width: 100% !important;
                border-radius: 12px !important;
                background: #111827 !important;
                color: white !important;
                border: none !important;
                padding: 12px 16px !important;
                font-size: 15px !important;
                font-weight: 700 !important;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.markdown('<div class="login-title">💸 Zé do Pix</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">Acesse o dashboard financeiro</div>', unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=False):
        usuario = st.text_input("Usuário", placeholder="Digite seu usuário")
        senha = st.text_input("Senha", type="password", placeholder="Digite sua senha")
        entrar = st.form_submit_button("Entrar")

    if entrar:
        if usuario == APP_USER and senha == APP_PASS:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos.")

    st.markdown('<div class="login-footer">Acesso restrito</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    return False


if not ensure_login():
    st.stop()

# ---------------------------------------------------
# CSS PRINCIPAL (ALTERAÇÃO AQUI)
# ---------------------------------------------------

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 3rem;
            padding-bottom: 2rem;
            max-width: 1240px;
        }
        .page-title {
            font-size: 34px;
            font-weight: 800;
            color: #0f2d5c;
            margin: 0;
        }
        .page-subtitle {
            color: #667085;
            margin-top: 6px;
            font-size: 16px;
        }
        .kpi-card {
            background: #ffffff;
            border-radius: 20px;
            padding: 18px 18px 14px 18px;
            box-shadow: 0 6px 18px rgba(16,24,40,0.05);
            border-left: 10px solid #0f2d5c;
            min-height: 128px;
        }
        .kpi-title {
            font-size: 15px;
            color: #0f172a;
            font-weight: 700;
            margin-bottom: 8px;
        }
        .kpi-value {
            font-size: 28px;
            font-weight: 800;
            color: #0f2d5c;
        }
        .section-card {
            background: #ffffff;
            border-radius: 20px;
            padding: 14px 16px 10px 16px;
            box-shadow: 0 6px 18px rgba(16,24,40,0.05);
        }
        .section-title {
            font-size: 15px;
            font-weight: 800;
            color: #0f2d5c;
            margin: 4px 0 12px 0;
        }
        .status-chip {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
        }
        .chip-pago {
            background: #e7f8ee;
            color: #067647;
        }
        .chip-aberto {
            background: #eef4ff;
            color: #1849a9;
        }
        .chip-vencido {
            background: #fff1f3;
            color: #c01048;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------------------------------
# TOPO
# ---------------------------------------------------

top1, top2, top3 = st.columns([4, 2, 2])

with top1:
    st.markdown('<div class="page-title">💸 Dashboard — Zé do Pix</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Painel de lançamentos, vencimentos e lucro estimado.</div>', unsafe_allow_html=True)

with top2:
    if st.button("🔄 Atualizar agora", use_container_width=True):
        st.rerun()

with top3:
    if st.button("Sair", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

st.markdown("---")

# ---------------------------------------------------
# RESTANTE DO DASHBOARD
# (permanece exatamente igual ao que você já tem)
# ---------------------------------------------------
