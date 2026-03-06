import re
from datetime import datetime, date, timedelta

import gspread
import pandas as pd
import plotly.express as px
import streamlit as st
from google.oauth2.service_account import Credentials


# =========================================================
# CONFIG GERAL
# =========================================================
st.set_page_config(
    page_title="Dashboard — Zé do Pix",
    page_icon="💸",
    layout="wide"
)

APP_USER = "operacao"
APP_PASS = "100316"

WORKSHEET_NAME = "Página1"
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1jZwhiehWGGqVNucPIB7URzrhg_-vASpwFJtgg1ml5Mg/edit?gid=0"


# =========================================================
# LOGIN
# =========================================================
def ensure_login() -> bool:
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


# =========================================================
# GOOGLE SHEETS
# =========================================================
def normalize_private_key(pk: str) -> str:
    if not pk:
        return pk
    return pk.replace("\\n", "\n")


@st.cache_resource
def get_gsheet_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds_dict = {
        "type": st.secrets["gcp_service_account"]["type"],
        "project_id": st.secrets["gcp_service_account"]["project_id"],
        "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
        "private_key": normalize_private_key(st.secrets["gcp_service_account"]["private_key"]),
        "client_email": st.secrets["gcp_service_account"]["client_email"],
        "client_id": st.secrets["gcp_service_account"]["client_id"],
        "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
        "token_uri": st.secrets["gcp_service_account"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"],
    }

    credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(credentials)


@st.cache_resource
def get_worksheet():
    client = get_gsheet_client()
    spreadsheet = client.open_by_url(SPREADSHEET_URL)
    worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
    return worksheet


@st.cache_data(ttl=20)
def load_sheet_data():
    worksheet = get_worksheet()
    values = worksheet.get_all_values()

    if not values:
        return pd.DataFrame(), [], worksheet.row_count

    headers = values[0]
    rows = values[1:]

    if not rows:
        return pd.DataFrame(columns=headers), headers, worksheet.row_count

    max_cols = len(headers)
    rows_normalized = []

    for row in rows:
        if len(row) < max_cols:
            row = row + [""] * (max_cols - len(row))
        else:
            row = row[:max_cols]
        rows_normalized.append(row)

    df = pd.DataFrame(rows_normalized, columns=headers)
    df["_row_number"] = range(2, len(df) + 2)

    return df, headers, worksheet.row_count


def find_column_index(headers, target_name):
    for idx, col in enumerate(headers, start=1):
        if str(col).strip().lower() == str(target_name).strip().lower():
            return idx
    return None


def update_status_in_sheet(row_number: int, new_status: str):
    worksheet = get_worksheet()
    _, headers, _ = load_sheet_data()

    status_col_idx = find_column_index(headers, "Status")
    if status_col_idx is None:
        raise ValueError("Não encontrei a coluna 'Status' na planilha.")

    worksheet.update_cell(int(row_number), int(status_col_idx), new_status)
    load_sheet_data.clear()


# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================
def choose_column(df, options):
    for col in options:
        if col in df.columns:
            return col
    return None


def clean_money(value):
    if pd.isna(value):
        return 0.0

    s = str(value).strip()
    if s == "":
        return 0.0

    s = s.replace("R$", "").replace(" ", "")

    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(".", "").replace(",", ".")

    s = re.sub(r"[^0-9.\-]", "", s)

    try:
        return float(s)
    except Exception:
        return 0.0


def parse_date(value):
    if pd.isna(value):
        return pd.NaT

    s = str(value).strip()
    if s == "":
        return pd.NaT

    formatos = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d/%m/%y",
    ]

    for fmt in formatos:
        try:
            return datetime.strptime(s[:10], fmt).date()
        except Exception:
            pass

    try:
        parsed = pd.to_datetime(s, dayfirst=True, errors="coerce")
        if pd.isna(parsed):
            return pd.NaT
        return parsed.date()
    except Exception:
        return pd.NaT


def fmt_brl(value):
    try:
        v = float(value)
    except Exception:
        v = 0.0
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def status_from_row(row):
    raw = str(row.get("Status", "")).strip().lower()
    due = row.get("_due_date", pd.NaT)
    hoje = date.today()

    if raw in ["pago", "paga", "quitado", "recebido"]:
        return "Pago"

    if raw in ["vencido"]:
        return "Vencido"

    if pd.notna(due):
        if due < hoje:
            return "Vencido"
        return "Em aberto"

    return "Em aberto"


def status_chip(status):
    if status == "Pago":
        return '<span class="status-chip chip-pago">Pago</span>'
    if status == "Vencido":
        return '<span class="status-chip chip-vencido">Vencido</span>'
    return '<span class="status-chip chip-aberto">Em aberto</span>'


# =========================================================
# LOGIN CHECK
# =========================================================
if not ensure_login():
    st.stop()


# =========================================================
# CSS PRINCIPAL
# =================================================
