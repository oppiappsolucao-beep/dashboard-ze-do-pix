import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import re

# ==========================================
# CONFIG
# ==========================================
st.set_page_config(
    page_title="Dashboard — Zé do Pix",
    page_icon="💸",
    layout="wide"
)

APP_USER = "operacao"
APP_PASS = "100316"

# ID da sua planilha
SHEET_ID = "COLE_AQUI_O_ID_DA_PLANILHA"

# Nome da aba (se quiser usar por nome)
WORKSHEET_NAME = "Página1"

# Se preferir por índice da aba, use:
WORKSHEET_INDEX = 0


# ==========================================
# LOGIN
# ==========================================
def ensure_login() -> bool:
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if st.session_state.logged_in:
        return True

    st.markdown("""
    <style>
        .stApp {
            background: #f4f7fb;
        }

        .login-wrap {
            max-width: 430px;
            margin: 8vh auto 0 auto;
            padding: 0 16px;
            font-family: Inter, system-ui, -apple-system, Segoe UI, Arial, sans-serif;
        }

        .login-card {
            background: #ffffff;
            border-radius: 22px;
            padding: 34px 28px 28px 28px;
            box-shadow: 0 10px 35px rgba(16, 24, 40, 0.08);
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
            margin-bottom: 26px;
        }

        .login-hint {
            text-align: center;
            margin-top: 14px;
            color: #98a2b3;
            font-size: 12px;
        }

        div[data-testid="stForm"] {
            border: 0 !important;
            background: transparent !important;
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
    """, unsafe_allow_html=True)

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

    st.markdown('<div class="login-hint">Acesso restrito</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    return False


# ==========================================
# GOOGLE SHEETS
# ==========================================
def normalize_private_key(pk: str) -> str:
    if not pk:
        return pk
    return pk.replace("\\n", "\n")


@st.cache_resource
def get_gsheet_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
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
    client = gspread.authorize(credentials)
    return client


@st.cache_resource
def get_worksheet():
    client = get_gsheet_client()
    sh = client.open_by_key(SHEET_ID)

    try:
        ws = sh.worksheet(WORKSHEET_NAME)
    except Exception:
        ws = sh.get_worksheet(WORKSHEET_INDEX)

    return ws


@st.cache_data(ttl=30)
def load_sheet_data():
    ws = get_worksheet()
    values = ws.get_all_values()

    if not values or len(values) < 2:
        return pd.DataFrame(), []

    headers = values[0]
    rows = values[1:]

    max_cols = len(headers)
    rows = [row + [""] * (max_cols - len(row)) if len(row) < max_cols else row[:max_cols] for row in rows]

    df = pd.DataFrame(rows, columns=headers)
    df["_row_number"] = range(2, len(df) + 2)
    return df, headers


def find_col(headers, possible_names):
    headers_map = {str(h).strip().lower(): idx + 1 for idx, h in enumerate(headers)}
    for name in possible_names:
        key = name.strip().lower()
        if key in headers_map:
            return headers_map[key], name
    return None, None


def update_status_in_sheet(row_number, new_status):
    ws = get_worksheet()
    _, headers = load_sheet_data()

    possible_status_cols = [
        "Status (usado no dash)",
        "Status usado no dash",
        "Status Dashboard",
        "Status do Dash",
        "Status"
    ]

    status_col_idx, _ = find_col(headers, possible_status_cols)

    if status_col_idx is None:
        raise ValueError(
            "Nenhuma coluna de status encontrada. Crie uma coluna chamada "
            "'Status (usado no dash)' ou 'Status'."
        )

    ws.update_cell(int(row_number), int(status_col_idx), new_status)
    load_sheet_data.clear()


# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================
def clean_money(value):
    if pd.isna(value):
        return 0.0

    s = str(value).strip()
    if s == "":
        return 0.0

    s = s.replace("R$", "").replace(" ", "")

    # formato BR: 1.234,56
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")

    # formato simples com vírgula decimal: 123,45
    elif "," in s and "." not in s:
        s = s.replace(".", "").replace(",", ".")

    # remove caracteres estranhos
    s = re.sub(r"[^0-9.\-]", "", s)

    try:
        return float(s)
    except:
        return 0.0


def parse_date(value):
    if pd.isna(value):
        return pd.NaT

    s = str(value).strip()
    if s == "":
        return pd.NaT

    # tenta formatos comuns
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return pd.to_datetime(datetime.strptime(s[:10], fmt)).date()
        except:
            pass

    try:
        return pd.to_datetime(s, dayfirst=True, errors="coerce").date()
    except:
        return pd.NaT


def fmt_brl(value):
    try:
        v = float(value)
    except:
        v = 0.0
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def choose_column(df, options):
    for col in options:
        if col in df.columns:
            return col
    return None


def build_dashboard_status(row, dash_col, status_col, due_col):
    # prioridade 1: coluna manual do dashboard
    if dash_col and str(row.get(dash_col, "")).strip() != "":
        return str(row.get(dash_col, "")).strip()

    # prioridade 2: se status estiver pago
    if status_col:
        raw = str(row.get(status_col, "")).strip().lower()
        if raw in ["pago", "paga", "quitado", "recebido"]:
            return "Pago"

    # prioridade 3: calcula por vencimento
    due = row.get("_due_date")
    if pd.isna(due) or due is None:
        return "Em aberto"

    hoje = date.today()
    if due < hoje:
        return "Vencido"
    return "Em aberto"


# ==========================================
# APP
# ==========================================
if not ensure_login():
    st.stop()

# CSS principal
st.markdown("""
<style>
    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }

    .title-wrap {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 18px;
        margin-bottom: 8px;
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

    .top-btn button {
        border-radius: 12px !important;
        min-height: 44px !important;
    }

    .kpi-card {
        background: #fff;
        border-radius: 20px;
        padding: 18px 18px 14px 18px;
        box-shadow: 0 6px 18px rgba(16,24,40,0.05);
        border-left: 10px solid #0f2d5c;
        min-height: 125px;
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
        background: #fff;
        border-radius: 20px;
        padding: 14px 16px 8px 16px;
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

    .small-btn button {
        border-radius: 10px !important;
        padding: 0.3rem 0.5rem !important;
        font-size: 13px !important;
    }

    hr {
        margin-top: 1.2rem !important;
        margin-bottom: 1.2rem !important;
    }
</style>
""", unsafe_allow_html=True)

# topo
top1, top2, top3 = st.columns([4, 2, 2])

with top1:
    st.markdown('<div class="page-title">💸 Dashboard — Zé do Pix</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Painel de lançamentos, vencimentos e lucro estimado.</div>', unsafe_allow_html=True)

with top2:
    if st.button("🔄 Atualizar agora", use_container_width=True):
        load_sheet_data.clear()
        st.rerun()

with top3:
    if st.button("Sair", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

st.markdown("---")

# carrega planilha
try:
    df, headers = load_sheet_data()
except Exception as e:
    st.error("Erro ao conectar com Google Sheets API. Verifique Secrets e compartilhamento da planilha.")
    st.exception(e)
    st.stop()

if df.empty:
    st.warning("A planilha está vazia ou sem linhas de dados.")
    st.stop()

# descobrir colunas
date_col = choose_column(df, ["Data do dia", "Data", "Data Empréstimo", "Data do empréstimo"])
name_col = choose_column(df, ["Emprestado", "Cliente", "Nome", "Nome do cliente"])
phone_col = choose_column(df, ["Telefone", "WhatsApp", "Celular"])
loan_col = choose_column(df, ["Valor emprestado", "Valor Emprestado", "Emprestado (R$)"])
pay_col = choose_column(df, ["Valor a pagar", "Valor a Receber", "Total a pagar", "A receber"])
due_col = choose_column(df, ["Data do pagamento", "Vencimento", "Data de vencimento", "Data Pagamento"])
status_col = choose_column(df, ["Status"])
dash_status_col = choose_column(df, [
    "Status (usado no dash)",
    "Status usado no dash",
    "Status Dashboard",
    "Status do Dash"
])

if not loan_col or not pay_col:
    st.error("Não encontrei as colunas de valores. Verifique os nomes da planilha.")
    st.write("Colunas encontradas:", list(df.columns))
    st.stop()

# tratamentos
df["_loan"] = df[loan_col].apply(clean_money)
df["_pay"] = df[pay_col].apply(clean_money)
df["_profit"] = df["_pay"] - df["_loan"]

if date_col:
    df["_date"] = df[date_col].apply(parse_date)
else:
    df["_date"] = pd.NaT

if due_col:
    df["_due_date"] = df[due_col].apply(parse_date)
else:
    df["_due_date"] = pd.NaT

df["_dash_status"] = df.apply(
    lambda row: build_dashboard_status(row, dash_status_col, status_col, due_col),
    axis=1
)

# filtros
f1, f2, f3 = st.columns(3)

with f1:
    if date_col and df["_date"].notna().any():
        meses_validos = sorted(
            {d.strftime("%m/%Y") for d in df["_date"] if pd.notna(d)},
            key=lambda x: datetime.strptime(x, "%m/%Y")
        )
        meses_validos = list(reversed(meses_validos))
        selected_month = st.selectbox("Mês", options=["Todos"] + meses_validos, index=1 if len(meses_validos) >= 1 else 0)
    else:
        selected_month = "Todos"
        st.selectbox("Mês", options=["Todos"], index=0)

with f2:
    status_options = ["Todos", "Pago", "Em aberto", "Vencido"]
    selected_status = st.selectbox("Status", options=status_options, index=0)

with f3:
    search_name = st.text_input("Buscar por nome", placeholder="Ex: Nataly, Irene...")

df_filtrado = df.copy()

if selected_month != "Todos" and date_col:
    df_filtrado = df_filtrado[
        df_filtrado["_date"].apply(
            lambda d: d.strftime("%m/%Y") if pd.notna(d) else ""
        ) == selected_month
    ]

if selected_status != "Todos":
    df_filtrado = df_filtrado[df_filtrado["_dash_status"] == selected_status]

if search_name.strip() and name_col:
    df_filtrado = df_filtrado[
        df_filtrado[name_col].astype(str).str.contains(search_name, case=False, na=False)
    ]

st.markdown(f"**Total de registros filtrados: {len(df_filtrado)}**")

# KPIs
total_emprestado = df_filtrado["_loan"].sum()
total_receber = df_filtrado["_pay"].sum()
lucro_estimado = df_filtrado["_profit"].sum()
qtd_pagos = (df_filtrado["_dash_status"] == "Pago").sum()
qtd_aberto = (df_filtrado["_dash_status"] == "Em aberto").sum()
qtd_vencidos = (df_filtrado["_dash_status"] == "Vencido").sum()

k1, k2, k3, k4, k5, k6 = st.columns(6)

with k1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">💰 Total emprestado</div>
        <div class="kpi-value">{fmt_brl(total_emprestado)}</div>
        <div class="kpi-sub">soma do valor emprestado</div>
    </div>
    """, unsafe_allow_html=True)

with k2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">📥 Total a receber</div>
        <div class="kpi-value">{fmt_brl(total_receber)}</div>
        <div class="kpi-sub">soma do valor a pagar</div>
    </div>
    """, unsafe_allow_html=True)

with k3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">📝 Lucro estimado</div>
        <div class="kpi-value">{fmt_brl(lucro_estimado)}</div>
        <div class="kpi-sub">a pagar − emprestado</div>
    </div>
    """, unsafe_allow_html=True)

with k4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">💳 Pagos</div>
        <div class="kpi-value">{qtd_pagos}</div>
        <div class="kpi-sub">qtd (Status = Pago)</div>
    </div>
    """, unsafe_allow_html=True)

with k5:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">⏳ Em aberto</div>
        <div class="kpi-value">{qtd_aberto}</div>
        <div class="kpi-sub">a vencer / pendente</div>
    </div>
    """, unsafe_allow_html=True)

with k6:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">⚠️ Vencidos</div>
        <div class="kpi-value">{qtd_vencidos}</div>
        <div class="kpi-sub">vencimento &lt; hoje</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("")

# ==========================================
# GRÁFICOS
# ==========================================
c1, c2 = st.columns(2)

with c1:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📌 Status por vencimento (valor total)</div>', unsafe_allow_html=True)

    status_group = df_filtrado.groupby("_dash_status", dropna=False)["_pay"].sum().reset_index()
    status_group.columns = ["Status", "Total"]

    if not status_group.empty and status_group["Total"].sum() > 0:
        fig1 = px.pie(
            status_group,
            values="Total",
            names="Status",
            hole=0.55
        )
        fig1.update_traces(textinfo="label+value")
        fig1.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("Sem dados para o gráfico.")
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📊 Valor emprestado (últimos 7 dias)</div>', unsafe_allow_html=True)

    if date_col and df_filtrado["_date"].notna().any():
        hoje = date.today()
        ultimos_7 = pd.date_range(end=pd.Timestamp(hoje), periods=7).date

        rows_7 = []
        for d in ultimos_7:
            total_dia = df_filtrado.loc[df_filtrado["_date"] == d, "_loan"].sum()
            rows_7.append({
                "Dia": d.strftime("%d/%m/%Y"),
                "Total": total_dia
            })

        df_7 = pd.DataFrame(rows_7)
        fig2 = px.bar(df_7, x="Total", y="Dia", orientation="h", text="Total")
        fig2.update_traces(texttemplate="R$ %{text:,.2f}", textposition="outside")
        fig2.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="Dia", xaxis_title="Total (R$)")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Sem coluna de data válida para montar esse gráfico.")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("")

c3, c4 = st.columns(2)

with c3:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🏆 Top 10 (maior valor emprestado)</div>', unsafe_allow_html=True)

    if name_col:
        top10 = (
            df_filtrado.groupby(name_col, dropna=False)["_loan"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )
        top10.columns = ["Cliente", "Total"]

        if not top10.empty:
            fig3 = px.bar(top10, x="Cliente", y="Total")
            fig3.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="", yaxis_title="total")
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Sem dados para o gráfico.")
    else:
        st.info("Sem coluna de nome/cliente.")
    st.markdown('</div>', unsafe_allow_html=True)

with c4:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🗓️ Vencimentos (valor a pagar)</div>', unsafe_allow_html=True)

    if due_col and df_filtrado["_due_date"].notna().any():
        venc = (
            df_filtrado.groupby("_due_date", dropna=False)["_pay"]
            .sum()
            .reset_index()
            .sort_values("_due_date")
        )
        venc["Data"] = venc["_due_date"].apply(lambda d: d.strftime("%d/%m/%Y") if pd.notna(d) else "Sem data")

        fig4 = px.bar(venc, x="Total a pagar" if "Total a pagar" in venc.columns else "_pay", y="Data", orientation="h")
        fig4.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="Total a pagar (R$)", yaxis_title="Data")
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("Sem coluna de vencimento válida.")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("")

# ==========================================
# TABELA + ATUALIZAÇÃO DA PLANILHA
# ==========================================
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">🧾 Registros</div>', unsafe_allow_html=True)

# versão visual da tabela
mostrar_cols = {}

if date_col:
    mostrar_cols[date_col] = "Data do dia"
if name_col:
    mostrar_cols[name_col] = "Emprestado"
if phone_col:
    mostrar_cols[phone_col] = "Telefone"

mostrar_cols[loan_col] = "Valor emprestado"
mostrar_cols[pay_col] = "Valor a pagar"

if due_col:
    mostrar_cols[due_col] = "Data do pagamento"
if status_col:
    mostrar_cols[status_col] = "Status"
if "_profit" not in mostrar_cols:
    pass

df_show = df_filtrado.copy()

df_show["Valor emprestado"] = df_show["_loan"].apply(fmt_brl)
df_show["Valor a pagar"] = df_show["_pay"].apply(fmt_brl)
df_show["Lucro (calc)"] = df_show["_profit"].apply(lambda x: f"{int(x)}" if float(x).is_integer() else f"{x:.2f}".replace(".", ","))
df_show["Status (usado no dash)"] = df_show["_dash_status"]

cols_final = []
if date_col:
    cols_final.append(date_col)
if name_col:
    cols_final.append(name_col)
if phone_col:
    cols_final.append(phone_col)

cols_final += ["Valor emprestado", "Valor a pagar"]

if due_col:
    cols_final.append(due_col)
if status_col:
    cols_final.append(status_col)

cols_final += ["Lucro (calc)", "Status (usado no dash)"]

st.dataframe(
    df_show[cols_final],
    use_container_width=True,
    height=400
)

st.markdown("### Atualizar status da planilha")

if len(df_filtrado) == 0:
    st.info("Nenhum registro para atualizar.")
else:
    for _, row in df_filtrado.iterrows():
        with st.container(border=True):
            a1, a2, a3, a4, a5 = st.columns([3, 2, 1.4, 1.4, 1.4])

            nome_exib = str(row.get(name_col, "-")) if name_col else "-"
            tel_exib = str(row.get(phone_col, "-")) if phone_col else "-"
            status_exib = str(row.get("_dash_status", "-"))

            with a1:
                st.write(f"**{nome_exib}**")
                st.caption(f"Telefone: {tel_exib}")

            with a2:
                st.write(f"**{fmt_brl(row['_pay'])}**")
                st.caption(f"Status atual: {status_exib}")

            with a3:
                if st.button("✔ Pago", key=f"pago_{row['_row_number']}", use_container_width=True):
                    try:
                        update_status_in_sheet(row["_row_number"], "Pago")
                        st.success(f"{nome_exib}: status atualizado para Pago")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao atualizar: {e}")

            with a4:
                if st.button("⏳ Em aberto", key=f"aberto_{row['_row_number']}", use_container_width=True):
                    try:
                        update_status_in_sheet(row["_row_number"], "Em aberto")
                        st.success(f"{nome_exib}: status atualizado para Em aberto")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao atualizar: {e}")

            with a5:
                if st.button("⚠ Vencido", key=f"vencido_{row['_row_number']}", use_container_width=True):
                    try:
                        update_status_in_sheet(row["_row_number"], "Vencido")
                        st.success(f"{nome_exib}: status atualizado para Vencido")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao atualizar: {e}")

st.markdown('</div>', unsafe_allow_html=True)
