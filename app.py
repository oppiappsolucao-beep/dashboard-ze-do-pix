import streamlit as st
import pandas as pd
import plotly.express as px
import re
import time
from datetime import date, timedelta
import gspread
from google.oauth2.service_account import Credentials
from streamlit_autorefresh import st_autorefresh

# ===============================
# LOGIN
# ===============================
APP_USER = "operacao"
APP_PASS = "100316"

def login():

    if "logged" not in st.session_state:
        st.session_state.logged = False

    if st.session_state.logged:
        return True

    st.markdown("""
    <style>

    .stApp{
        background:#f3f4f6;
    }

    .login-box{
        max-width:600px;
        margin:auto;
        margin-top:80px;
        background:white;
        padding:40px;
        border-radius:20px;
        box-shadow:0 10px 30px rgba(0,0,0,0.08);
    }

    .stTextInput input{
        background:#eef2f7;
        border-radius:10px;
    }

    .stButton button{
        background:black;
        color:white;
        width:100%;
        border-radius:10px;
        height:45px;
        font-weight:700;
    }

    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-box">', unsafe_allow_html=True)

    usuario = st.text_input("usuario")
    senha = st.text_input("senha", type="password")

    if st.button("Entrar"):

        if usuario == APP_USER and senha == APP_PASS:
            st.session_state.logged = True
            st.rerun()

        else:
            st.error("Usuário ou senha inválidos")

    st.markdown('</div>', unsafe_allow_html=True)

    return False


if not login():
    st.stop()


# ===============================
# CONFIG
# ===============================

st.set_page_config(
    page_title="Dashboard Zé do Pix",
    page_icon="💰",
    layout="wide"
)

st_autorefresh(interval=15000)

SHEET_ID = "1jZwhiehWGGqVNucPIB7URzrhg_-vASpwFJtgg1mI5Mg"

# ===============================
# GOOGLE SHEETS
# ===============================

def connect_sheet():

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )

    client = gspread.authorize(creds)

    sheet = client.open_by_key(SHEET_ID).sheet1

    data = sheet.get_all_records()

    df = pd.DataFrame(data)

    df["row"] = range(2, len(df)+2)

    return df, sheet


# ===============================
# FORMATAÇÃO
# ===============================

def parse_money(v):

    if pd.isna(v):
        return 0

    v = str(v)

    v = v.replace("R$", "")
    v = v.replace(".", "")
    v = v.replace(",", ".")

    try:
        return float(v)
    except:
        return 0


def brl(v):

    v = f"{v:,.2f}"

    v = v.replace(",", "X")
    v = v.replace(".", ",")
    v = v.replace("X", ".")

    return f"R$ {v}"


# ===============================
# LOAD
# ===============================

try:
    df, sheet = connect_sheet()

except Exception as e:
    st.error("Erro ao conectar com Google Sheets")
    st.exception(e)
    st.stop()


df["valor_emprestado"] = df["Valor emprestado"].apply(parse_money)
df["valor_a_pagar"] = df["Valor a pagar"].apply(parse_money)

df["data"] = pd.to_datetime(df["Data do dia"], dayfirst=True)

df["vencimento"] = pd.to_datetime(df["Data do pagamento"], dayfirst=True)

df["mes"] = df["data"].dt.strftime("%m/%Y")

# ===============================
# HEADER
# ===============================

col1, col2 = st.columns([3,1])

with col1:
    st.title("💸 Dashboard — Zé do Pix")
    st.caption("Painel de lançamentos, vencimentos e lucro estimado")

with col2:

    if st.button("🔄 Atualizar agora"):
        st.rerun()

# ===============================
# FILTROS
# ===============================

c1, c2, c3 = st.columns(3)

with c1:
    meses = ["Todos"] + sorted(df["mes"].unique())
    mes = st.selectbox("Mês", meses)

with c2:
    status = st.selectbox("Status", ["Todos","Pago","Em aberto","Vencido"])

with c3:
    busca = st.text_input("Buscar por nome")

fdf = df.copy()

if mes != "Todos":
    fdf = fdf[fdf["mes"] == mes]

if status != "Todos":
    fdf = fdf[fdf["Status"] == status]

if busca:
    fdf = fdf[fdf["Emprestado"].str.contains(busca, case=False)]

# ===============================
# KPIs
# ===============================

total_emprestado = fdf["valor_emprestado"].sum()
total_receber = fdf["valor_a_pagar"].sum()

lucro = total_receber - total_emprestado

pagos = len(fdf[fdf["Status"] == "Pago"])
aberto = len(fdf[fdf["Status"] == "Em aberto"])
vencidos = len(fdf[fdf["Status"] == "Vencido"])

k1,k2,k3,k4,k5 = st.columns(5)

k1.metric("Total emprestado", brl(total_emprestado))
k2.metric("Total a receber", brl(total_receber))
k3.metric("Lucro estimado", brl(lucro))
k4.metric("Pagos", pagos)
k5.metric("Vencidos", vencidos)

# ===============================
# GRÁFICOS
# ===============================

c1,c2 = st.columns(2)

with c1:

    status_valor = fdf.groupby("Status")["valor_a_pagar"].sum().reset_index()

    fig = px.pie(
        status_valor,
        names="Status",
        values="valor_a_pagar",
        hole=.6
    )

    st.plotly_chart(fig, use_container_width=True)


with c2:

    hoje = df["data"].max()

    inicio = hoje - timedelta(days=6)

    ultimos = df[df["data"] >= inicio]

    graf = ultimos.groupby("data")["valor_emprestado"].sum().reset_index()

    graf["data"] = graf["data"].dt.strftime("%d/%m")

    fig = px.bar(
        graf,
        y="data",
        x="valor_emprestado",
        orientation="h"
    )

    st.plotly_chart(fig, use_container_width=True)

# ===============================
# TABELA
# ===============================

st.subheader("Registros")

st.dataframe(
    fdf.sort_values("data", ascending=False),
    use_container_width=True
)

# ===============================
# ALTERAR STATUS
# ===============================

st.subheader("Atualizar status")

if len(fdf) > 0:

    idx = st.selectbox(
        "Registro",
        fdf.index,
        format_func=lambda i: f"{fdf.loc[i,'Emprestado']} | {fdf.loc[i,'Data do dia']}"
    )

    row = fdf.loc[idx,"row"]

    col1,col2,col3 = st.columns(3)

    if col1.button("Marcar Pago"):
        sheet.update_cell(row,7,"Pago")
        st.rerun()

    if col2.button("Em aberto"):
        sheet.update_cell(row,7,"Em aberto")
        st.rerun()

    if col3.button("Vencido"):
        sheet.update_cell(row,7,"Vencido")
        st.rerun()
