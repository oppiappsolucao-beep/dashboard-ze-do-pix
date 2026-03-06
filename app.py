import re
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

# LINK CORRETO DA PLANILHA
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

    st.title("💸 Zé do Pix")

    user = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")

    if st.button("Entrar"):

        if user == APP_USER and password == APP_PASS:
            st.session_state.logged_in = True
            st.rerun()

        else:
            st.error("Usuário ou senha inválidos")

    return False


if not ensure_login():
    st.stop()

# ---------------------------------------------------
# GOOGLE SHEETS
# ---------------------------------------------------

def normalize_private_key(pk):
    return pk.replace("\\n", "\n")


@st.cache_resource
def get_gsheet_client():

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = st.secrets["gcp_service_account"]

    creds_dict = {
        "type": creds["type"],
        "project_id": creds["project_id"],
        "private_key_id": creds["private_key_id"],
        "private_key": normalize_private_key(creds["private_key"]),
        "client_email": creds["client_email"],
        "client_id": creds["client_id"],
        "auth_uri": creds["auth_uri"],
        "token_uri": creds["token_uri"],
        "auth_provider_x509_cert_url": creds["auth_provider_x509_cert_url"],
        "client_x509_cert_url": creds["client_x509_cert_url"],
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
def load_data():

    worksheet = get_worksheet()

    values = worksheet.get_all_values()

    headers = values[0]

    rows = values[1:]

    df = pd.DataFrame(rows, columns=headers)

    df["_row"] = range(2, len(df) + 2)

    return df


def update_status(row, status):

    ws = get_worksheet()

    headers = ws.row_values(1)

    col_index = headers.index("Status") + 1

    ws.update_cell(row, col_index, status)

    load_data.clear()


# ---------------------------------------------------
# UTIL
# ---------------------------------------------------

def money_to_float(v):

    if not v:
        return 0

    v = v.replace("R$", "").replace(".", "").replace(",", ".").strip()

    try:
        return float(v)

    except:
        return 0


def format_money(v):

    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def parse_date(d):

    try:
        return datetime.strptime(d, "%d/%m/%Y").date()

    except:
        return None


# ---------------------------------------------------
# LOAD DATA
# ---------------------------------------------------

try:

    df = load_data()

except Exception as e:

    st.error("Erro ao conectar com Google Sheets API")

    st.exception(e)

    st.stop()

# ---------------------------------------------------
# PROCESS DATA
# ---------------------------------------------------

df["valor_emprestado"] = df["Valor emprestado"].apply(money_to_float)

df["valor_pagar"] = df["Valor a pagar"].apply(money_to_float)

df["lucro"] = df["valor_pagar"] - df["valor_emprestado"]

df["data"] = df["Data do dia"].apply(parse_date)

df["vencimento"] = df["Data de pagamento"].apply(parse_date)

today = date.today()

def calc_status(row):

    status = str(row["Status"]).lower()

    if "pago" in status:
        return "Pago"

    if row["vencimento"] and row["vencimento"] < today:
        return "Vencido"

    return "Em aberto"


df["status_dash"] = df.apply(calc_status, axis=1)

# ---------------------------------------------------
# KPIs
# ---------------------------------------------------

total_emprestado = df["valor_emprestado"].sum()

total_receber = df["valor_pagar"].sum()

lucro = df["lucro"].sum()

pagos = (df["status_dash"] == "Pago").sum()

aberto = (df["status_dash"] == "Em aberto").sum()

vencido = (df["status_dash"] == "Vencido").sum()

c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric("Total emprestado", format_money(total_emprestado))

c2.metric("Total a receber", format_money(total_receber))

c3.metric("Lucro estimado", format_money(lucro))

c4.metric("Pagos", pagos)

c5.metric("Em aberto", aberto)

c6.metric("Vencidos", vencido)

st.divider()

# ---------------------------------------------------
# GRÁFICO STATUS
# ---------------------------------------------------

fig = px.pie(df, names="status_dash", values="valor_pagar")

st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------
# TABELA
# ---------------------------------------------------

st.subheader("Registros")

show = df[[
    "Data do dia",
    "Emprestado",
    "Telefone",
    "Valor emprestado",
    "Valor a pagar",
    "Data de pagamento",
    "Status"
]]

st.dataframe(show, use_container_width=True)

st.divider()

# ---------------------------------------------------
# ATUALIZAR STATUS
# ---------------------------------------------------

st.subheader("Atualizar status")

for _, row in df.iterrows():

    c1, c2, c3, c4 = st.columns([4,1,1,1])

    c1.write(row["Emprestado"])

    if c2.button("Pago", key=f"p{row['_row']}"):

        update_status(row["_row"], "Pago")

        st.rerun()

    if c3.button("A vencer", key=f"a{row['_row']}"):

        update_status(row["_row"], "A Vencer")

        st.rerun()

    if c4.button("Vencido", key=f"v{row['_row']}"):

        update_status(row["_row"], "Vencido")

        st.rerun()
