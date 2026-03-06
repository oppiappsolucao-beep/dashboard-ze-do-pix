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
# =========================================================
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.4rem;
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
            line-height: 1.1;
        }

        .kpi-sub {
            margin-top: 6px;
            font-size: 13px;
            color: #667085;
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

        .stButton > button {
            border-radius: 12px !important;
        }

        hr {
            margin-top: 1.2rem !important;
            margin-bottom: 1.2rem !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================================================
# TESTE DE CONEXÃO
# =========================================================
try:
    _ws = get_worksheet()
except Exception as e:
    st.error("Erro ao conectar com Google Sheets API. Verifique Secrets, URL da planilha e compartilhamento.")
    st.exception(e)
    st.stop()

# =========================================================
# TOPO
# =========================================================
top1, top2, top3 = st.columns([4, 2, 2])

with top1:
    st.markdown('<div class="page-title">💸 Dashboard — Zé do Pix</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Painel de lançamentos, vencimentos e lucro estimado.</div>', unsafe_allow_html=True)

with top2:
    if st.button("🔄 Atualizar agora", use_container_width=True):
        load_sheet_data.clear()
        st.cache_resource.clear()
        st.rerun()

with top3:
    if st.button("Sair", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

st.markdown("---")

# =========================================================
# CARREGAR DADOS
# =========================================================
try:
    df, headers, _ = load_sheet_data()
except Exception as e:
    st.error("Erro ao carregar a planilha.")
    st.exception(e)
    st.stop()

if df.empty:
    st.warning("A planilha está vazia.")
    st.stop()

# =========================================================
# MAPEAMENTO DE COLUNAS
# =========================================================
date_col = choose_column(df, ["Data do dia", "Data", "Data Empréstimo"])
name_col = choose_column(df, ["Emprestado", "Cliente", "Nome"])
loan_col = choose_column(df, ["Valor emprestado", "Valor Emprestado"])
pay_col = choose_column(df, ["Valor a pagar", "Valor a Receber", "Total a pagar"])
due_col = choose_column(df, ["Data de pagamento", "Vencimento", "Data de vencimento"])
phone_col = choose_column(df, ["Telefone", "WhatsApp", "Celular"])
status_col = choose_column(df, ["Status"])

missing_cols = []
for label, col in {
    "Data do dia": date_col,
    "Emprestado": name_col,
    "Valor emprestado": loan_col,
    "Valor a pagar": pay_col,
    "Data de pagamento": due_col,
    "Telefone": phone_col,
    "Status": status_col,
}.items():
    if col is None:
        missing_cols.append(label)

if missing_cols:
    st.error("Faltam colunas necessárias na planilha.")
    st.write("Colunas faltando:", missing_cols)
    st.write("Colunas encontradas:", list(df.columns))
    st.stop()

# =========================================================
# TRATAMENTO DOS DADOS
# =========================================================
df["_loan"] = df[loan_col].apply(clean_money)
df["_pay"] = df[pay_col].apply(clean_money)
df["_profit"] = df["_pay"] - df["_loan"]
df["_date"] = df[date_col].apply(parse_date)
df["_due_date"] = df[due_col].apply(parse_date)
df["_dash_status"] = df.apply(status_from_row, axis=1)

# =========================================================
# FILTROS
# =========================================================
f1, f2, f3 = st.columns(3)

meses_validos = []
datas_validas = [d for d in df["_date"] if pd.notna(d)]
if datas_validas:
    meses_validos = sorted(
        {d.strftime("%m/%Y") for d in datas_validas},
        key=lambda x: datetime.strptime(x, "%m/%Y"),
        reverse=True
    )

with f1:
    selected_month = st.selectbox("Mês", ["Todos"] + meses_validos if meses_validos else ["Todos"])

with f2:
    selected_status = st.selectbox("Status", ["Todos", "Pago", "Em aberto", "Vencido"], index=0)

with f3:
    search_name = st.text_input("Buscar por nome", placeholder="Ex: Nataly, Irene...")

df_filtrado = df.copy()

if selected_month != "Todos":
    df_filtrado = df_filtrado[
        df_filtrado["_date"].apply(lambda d: d.strftime("%m/%Y") if pd.notna(d) else "") == selected_month
    ]

if selected_status != "Todos":
    df_filtrado = df_filtrado[df_filtrado["_dash_status"] == selected_status]

if search_name.strip():
    df_filtrado = df_filtrado[
        df_filtrado[name_col].astype(str).str.contains(search_name, case=False, na=False)
    ]

st.markdown(f"**Total de registros filtrados: {len(df_filtrado)}**")

# =========================================================
# KPIs
# =========================================================
total_emprestado = df_filtrado["_loan"].sum()
total_receber = df_filtrado["_pay"].sum()
lucro_estimado = df_filtrado["_profit"].sum()
qtd_pagos = int((df_filtrado["_dash_status"] == "Pago").sum())
qtd_aberto = int((df_filtrado["_dash_status"] == "Em aberto").sum())
qtd_vencidos = int((df_filtrado["_dash_status"] == "Vencido").sum())

k1, k2, k3, k4, k5, k6 = st.columns(6)

cards = [
    ("💰 Total emprestado", fmt_brl(total_emprestado), "soma do valor emprestado"),
    ("📥 Total a receber", fmt_brl(total_receber), "soma do valor a pagar"),
    ("📝 Lucro estimado", fmt_brl(lucro_estimado), "a pagar − emprestado"),
    ("💳 Pagos", str(qtd_pagos), "qtd (Status = Pago)"),
    ("⏳ Em aberto", str(qtd_aberto), "a vencer / pendente"),
    ("⚠️ Vencidos", str(qtd_vencidos), "vencimento < hoje"),
]

for col, card in zip([k1, k2, k3, k4, k5, k6], cards):
    titulo, valor, sub = card
    with col:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">{titulo}</div>
                <div class="kpi-value">{valor}</div>
                <div class="kpi-sub">{sub}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

st.markdown("")

# =========================================================
# GRÁFICOS
# =========================================================
c1, c2 = st.columns(2)

with c1:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📌 Status por vencimento (valor total)</div>', unsafe_allow_html=True)

    status_group = (
        df_filtrado.groupby("_dash_status", dropna=False)["_pay"]
        .sum()
        .reset_index()
        .rename(columns={"_dash_status": "Status", "_pay": "Total"})
    )

    if not status_group.empty and status_group["Total"].sum() > 0:
        fig1 = px.pie(status_group, values="Total", names="Status", hole=0.55)
        fig1.update_traces(textinfo="label+value")
        fig1.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("Sem dados para o gráfico.")
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📊 Valor emprestado (últimos 7 dias)</div>', unsafe_allow_html=True)

    hoje = date.today()
    ultimos_7 = [hoje - timedelta(days=i) for i in range(6, -1, -1)]
    rows_7 = [{"Dia": d.strftime("%d/%m/%Y"), "Total": df_filtrado.loc[df_filtrado["_date"] == d, "_loan"].sum()} for d in ultimos_7]
    df_7 = pd.DataFrame(rows_7)

    fig2 = px.bar(df_7, x="Total", y="Dia", orientation="h", text="Total")
    fig2.update_traces(texttemplate="R$ %{text:,.2f}", textposition="outside")
    fig2.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="Dia", xaxis_title="Total (R$)")
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("")

c3, c4 = st.columns(2)

with c3:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🏆 Top 10 (maior valor emprestado)</div>', unsafe_allow_html=True)

    top10 = (
        df_filtrado.groupby(name_col, dropna=False)["_loan"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
        .rename(columns={name_col: "Cliente", "_loan": "Total"})
    )

    if not top10.empty:
        fig3 = px.bar(top10, x="Cliente", y="Total")
        fig3.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="", yaxis_title="Total")
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Sem dados para o gráfico.")
    st.markdown("</div>", unsafe_allow_html=True)

with c4:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🗓️ Vencimentos (valor a pagar)</div>', unsafe_allow_html=True)

    venc = (
        df_filtrado[df_filtrado["_due_date"].notna()]
        .groupby("_due_date")["_pay"]
        .sum()
        .reset_index()
        .rename(columns={"_due_date": "DataVenc", "_pay": "Total"})
        .sort_values("DataVenc")
    )

    if not venc.empty:
        venc["Data"] = venc["DataVenc"].apply(lambda d: d.strftime("%d/%m/%Y"))
        fig4 = px.bar(venc, x="Total", y="Data", orientation="h", text="Total")
        fig4.update_traces(texttemplate="R$ %{text:,.2f}", textposition="outside")
        fig4.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="Total a pagar (R$)", yaxis_title="Data")
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("Sem dados para o gráfico.")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("")

# =========================================================
# TABELA
# =========================================================
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">🧾 Registros</div>', unsafe_allow_html=True)

df_show = df_filtrado.copy()
df_show["Valor emprestado_fmt"] = df_show["_loan"].apply(fmt_brl)
df_show["Valor a pagar_fmt"] = df_show["_pay"].apply(fmt_brl)
df_show["Lucro (calc)"] = df_show["_profit"].apply(fmt_brl)
df_show["Status (usado no dash)"] = df_show["_dash_status"]

cols_show = [
    date_col,
    name_col,
    phone_col,
    "Valor emprestado_fmt",
    "Valor a pagar_fmt",
    due_col,
    status_col,
    "Lucro (calc)",
    "Status (usado no dash)"
]

renomear = {
    date_col: "Data do dia",
    name_col: "Emprestado",
    phone_col: "Telefone",
    "Valor emprestado_fmt": "Valor emprestado",
    "Valor a pagar_fmt": "Valor a pagar",
    due_col: "Data do pagamento",
    status_col: "Status",
    "Lucro (calc)": "Lucro (calc)",
    "Status (usado no dash)": "Status (usado no dash)"
}

st.dataframe(df_show[cols_show].rename(columns=renomear), use_container_width=True, height=420)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("")

# =========================================================
# ATUALIZAÇÃO DE STATUS
# =========================================================
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">✏️ Atualizar status da planilha</div>', unsafe_allow_html=True)

if df_filtrado.empty:
    st.info("Nenhum registro encontrado para atualização.")
else:
    for _, row in df_filtrado.iterrows():
        nome = str(row.get(name_col, "-"))
        telefone = str(row.get(phone_col, "-"))
        valor = fmt_brl(row.get("_pay", 0))
        status_atual = str(row.get("_dash_status", "Em aberto"))

        c1, c2, c3, c4, c5 = st.columns([3.2, 1.5, 1.2, 1.4, 1.2])

        with c1:
            st.markdown(f"**{nome}**")
            st.caption(f"Telefone: {telefone}")

        with c2:
            st.markdown(f"**{valor}**")
            st.markdown(status_chip(status_atual), unsafe_allow_html=True)

        with c3:
            if st.button("✔ Pago", key=f"pago_{row['_row_number']}", use_container_width=True):
                update_status_in_sheet(row["_row_number"], "Pago")
                st.success(f"{nome}: status atualizado para Pago.")
                st.rerun()

        with c4:
            if st.button("⏳ Em aberto", key=f"aberto_{row['_row_number']}", use_container_width=True):
                update_status_in_sheet(row["_row_number"], "A Vencer")
                st.success(f"{nome}: status atualizado para A Vencer.")
                st.rerun()

        with c5:
            if st.button("⚠ Vencido", key=f"vencido_{row['_row_number']}", use_container_width=True):
                update_status_in_sheet(row["_row_number"], "Vencido")
                st.success(f"{nome}: status atualizado para Vencido.")
                st.rerun()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
