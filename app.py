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
# GOOGLE SHEETS
# ---------------------------------------------------

def normalize_private_key(pk):
    return pk.replace("\\n", "\n") if pk else pk


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

    if not values:
        return pd.DataFrame(), []

    headers = values[0]
    rows = values[1:]

    if not rows:
        return pd.DataFrame(columns=headers), headers

    max_cols = len(headers)
    rows_norm = []
    for row in rows:
        if len(row) < max_cols:
            row = row + [""] * (max_cols - len(row))
        else:
            row = row[:max_cols]
        rows_norm.append(row)

    df = pd.DataFrame(rows_norm, columns=headers)
    df["_row"] = range(2, len(df) + 2)

    return df, headers


def update_status(row_number, status):
    ws = get_worksheet()
    headers = ws.row_values(1)

    status_col_idx = None
    for idx, col in enumerate(headers, start=1):
        if str(col).strip().lower() == "status":
            status_col_idx = idx
            break

    if status_col_idx is None:
        raise ValueError("Não encontrei a coluna 'Status' na planilha.")

    ws.update_cell(int(row_number), int(status_col_idx), status)
    load_data.clear()


# ---------------------------------------------------
# UTIL
# ---------------------------------------------------

def pick_col(df, options):
    cols_norm = {str(c).strip().lower(): c for c in df.columns}
    for opt in options:
        key = str(opt).strip().lower()
        if key in cols_norm:
            return cols_norm[key]
    return None


def money_to_float(v):
    if pd.isna(v):
        return 0.0

    s = str(v).strip()
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


def format_money(v):
    try:
        v = float(v)
    except Exception:
        v = 0.0
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def parse_date(d):
    if pd.isna(d):
        return pd.NaT

    s = str(d).strip()
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


def status_chip(status):
    if status == "Pago":
        return '<span class="status-chip chip-pago">Pago</span>'
    if status == "Vencido":
        return '<span class="status-chip chip-vencido">Vencido</span>'
    return '<span class="status-chip chip-aberto">Em aberto</span>'


# ---------------------------------------------------
# CSS PRINCIPAL
# ---------------------------------------------------

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
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------------------------------
# TESTE DE CONEXÃO
# ---------------------------------------------------

try:
    _ws = get_worksheet()
except Exception as e:
    st.error("Erro ao conectar com Google Sheets API. Verifique Secrets, URL da planilha e compartilhamento.")
    st.exception(e)
    st.stop()

# ---------------------------------------------------
# TOPO
# ---------------------------------------------------

top1, top2, top3 = st.columns([4, 2, 2])

with top1:
    st.markdown('<div class="page-title">💸 Dashboard — Zé do Pix</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Painel de lançamentos, vencimentos e lucro estimado.</div>', unsafe_allow_html=True)

with top2:
    if st.button("🔄 Atualizar agora", use_container_width=True):
        load_data.clear()
        st.cache_resource.clear()
        st.rerun()

with top3:
    if st.button("Sair", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

st.markdown("---")

# ---------------------------------------------------
# LOAD DATA
# ---------------------------------------------------

try:
    df, headers = load_data()
except Exception as e:
    st.error("Erro ao carregar a planilha.")
    st.exception(e)
    st.stop()

if df.empty:
    st.warning("A planilha está vazia.")
    st.stop()

# ---------------------------------------------------
# DETECTAR COLUNAS AUTOMATICAMENTE
# ---------------------------------------------------

col_data = pick_col(df, ["Data do dia", "Data"])
col_nome = pick_col(df, ["Emprestado", "Cliente", "Nome"])
col_telefone = pick_col(df, ["Telefone", "WhatsApp", "Celular"])
col_valor_emprestado = pick_col(df, ["Valor emprestado", "Valor Emprestado"])
col_valor_pagar = pick_col(df, ["Valor a pagar", "Valor a Receber", "Total a pagar"])
col_vencimento = pick_col(df, ["Data de pagamento", "Data Pagamento", "Vencimento", "Data de vencimento"])
col_status = pick_col(df, ["Status"])

faltando = []
if not col_data:
    faltando.append("Data do dia")
if not col_nome:
    faltando.append("Emprestado")
if not col_telefone:
    faltando.append("Telefone")
if not col_valor_emprestado:
    faltando.append("Valor emprestado")
if not col_valor_pagar:
    faltando.append("Valor a pagar")
if not col_vencimento:
    faltando.append("Data de pagamento")
if not col_status:
    faltando.append("Status")

if faltando:
    st.error("Faltam colunas necessárias na planilha.")
    st.write("Colunas encontradas:", list(df.columns))
    st.write("Colunas faltando:", faltando)
    st.stop()

# ---------------------------------------------------
# PROCESS DATA
# ---------------------------------------------------

df["valor_emprestado"] = df[col_valor_emprestado].apply(money_to_float)
df["valor_pagar"] = df[col_valor_pagar].apply(money_to_float)
df["lucro"] = df["valor_pagar"] - df["valor_emprestado"]
df["data"] = df[col_data].apply(parse_date)
df["vencimento"] = df[col_vencimento].apply(parse_date)

today = date.today()

def calc_status(row):
    status = str(row[col_status]).strip().lower()

    if "pago" in status:
        return "Pago"

    if "vencido" in status:
        return "Vencido"

    if pd.notna(row["vencimento"]) and row["vencimento"] < today:
        return "Vencido"

    return "Em aberto"

df["status_dash"] = df.apply(calc_status, axis=1)

# ---------------------------------------------------
# FILTROS
# ---------------------------------------------------

f1, f2, f3 = st.columns(3)

meses_validos = []
datas_validas = [d for d in df["data"] if pd.notna(d)]
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
        df_filtrado["data"].apply(lambda d: d.strftime("%m/%Y") if pd.notna(d) else "") == selected_month
    ]

if selected_status != "Todos":
    df_filtrado = df_filtrado[df_filtrado["status_dash"] == selected_status]

if search_name.strip():
    df_filtrado = df_filtrado[
        df_filtrado[col_nome].astype(str).str.contains(search_name, case=False, na=False)
    ]

st.markdown(f"**Total de registros filtrados: {len(df_filtrado)}**")

# ---------------------------------------------------
# KPIs
# ---------------------------------------------------

total_emprestado = df_filtrado["valor_emprestado"].sum()
total_receber = df_filtrado["valor_pagar"].sum()
lucro = df_filtrado["lucro"].sum()
pagos = int((df_filtrado["status_dash"] == "Pago").sum())
aberto = int((df_filtrado["status_dash"] == "Em aberto").sum())
vencido = int((df_filtrado["status_dash"] == "Vencido").sum())

c1, c2, c3, c4, c5, c6 = st.columns(6)

cards = [
    ("💰 Total emprestado", format_money(total_emprestado), "soma do valor emprestado"),
    ("📥 Total a receber", format_money(total_receber), "soma do valor a pagar"),
    ("📝 Lucro estimado", format_money(lucro), "a pagar − emprestado"),
    ("💳 Pagos", str(pagos), "qtd (Status = Pago)"),
    ("⏳ Em aberto", str(aberto), "a vencer / pendente"),
    ("⚠️ Vencidos", str(vencido), "vencimento < hoje"),
]

for col, card in zip([c1, c2, c3, c4, c5, c6], cards):
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

# ---------------------------------------------------
# GRÁFICOS
# ---------------------------------------------------

g1, g2 = st.columns(2)

with g1:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📌 Status por vencimento (valor total)</div>', unsafe_allow_html=True)

    status_group = (
        df_filtrado.groupby("status_dash", dropna=False)["valor_pagar"]
        .sum()
        .reset_index()
        .rename(columns={"status_dash": "Status", "valor_pagar": "Total"})
    )

    if not status_group.empty and status_group["Total"].sum() > 0:
        fig1 = px.pie(status_group, names="Status", values="Total", hole=0.55)
        fig1.update_traces(textinfo="label+value")
        fig1.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("Sem dados para o gráfico.")
    st.markdown("</div>", unsafe_allow_html=True)

with g2:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📊 Valor emprestado (últimos 7 dias)</div>', unsafe_allow_html=True)

    hoje = date.today()
    ultimos_7 = [hoje - timedelta(days=i) for i in range(6, -1, -1)]

    rows_7 = []
    for d in ultimos_7:
        total_dia = df_filtrado.loc[df_filtrado["data"] == d, "valor_emprestado"].sum()
        rows_7.append({"Dia": d.strftime("%d/%m/%Y"), "Total": total_dia})

    df_7 = pd.DataFrame(rows_7)

    fig2 = px.bar(df_7, x="Total", y="Dia", orientation="h", text="Total")
    fig2.update_traces(texttemplate="R$ %{text:,.2f}", textposition="outside")
    fig2.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="Dia", xaxis_title="Total (R$)")
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("")

g3, g4 = st.columns(2)

with g3:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🏆 Top 10 (maior valor emprestado)</div>', unsafe_allow_html=True)

    top10 = (
        df_filtrado.groupby(col_nome, dropna=False)["valor_emprestado"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
        .rename(columns={col_nome: "Cliente", "valor_emprestado": "Total"})
    )

    if not top10.empty:
        fig3 = px.bar(top10, x="Cliente", y="Total")
        fig3.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="", yaxis_title="Total")
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Sem dados para o gráfico.")
    st.markdown("</div>", unsafe_allow_html=True)

with g4:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🗓️ Vencimentos (valor a pagar)</div>', unsafe_allow_html=True)

    venc = (
        df_filtrado[df_filtrado["vencimento"].notna()]
        .groupby("vencimento")["valor_pagar"]
        .sum()
        .reset_index()
        .rename(columns={"vencimento": "DataVenc", "valor_pagar": "Total"})
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

# ---------------------------------------------------
# TABELA
# ---------------------------------------------------

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">🧾 Registros</div>', unsafe_allow_html=True)

df_show = df_filtrado.copy()
df_show["Valor emprestado_fmt"] = df_show["valor_emprestado"].apply(format_money)
df_show["Valor a pagar_fmt"] = df_show["valor_pagar"].apply(format_money)
df_show["Lucro (calc)"] = df_show["lucro"].apply(format_money)
df_show["Status (usado no dash)"] = df_show["status_dash"]

cols_show = [
    col_data,
    col_nome,
    col_telefone,
    "Valor emprestado_fmt",
    "Valor a pagar_fmt",
    col_vencimento,
    col_status,
    "Lucro (calc)",
    "Status (usado no dash)"
]

renomear = {
    col_data: "Data do dia",
    col_nome: "Emprestado",
    col_telefone: "Telefone",
    "Valor emprestado_fmt": "Valor emprestado",
    "Valor a pagar_fmt": "Valor a pagar",
    col_vencimento: "Data de pagamento",
    col_status: "Status",
    "Lucro (calc)": "Lucro (calc)",
    "Status (usado no dash)": "Status (usado no dash)"
}

st.dataframe(
    df_show[cols_show].rename(columns=renomear),
    use_container_width=True,
    height=420
)

st.markdown("</div>", unsafe_allow_html=True)
st.markdown("")

# ---------------------------------------------------
# ATUALIZAR STATUS
# ---------------------------------------------------

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">✏️ Atualizar status da planilha</div>', unsafe_allow_html=True)

if df_filtrado.empty:
    st.info("Nenhum registro encontrado para atualização.")
else:
    for _, row in df_filtrado.iterrows():
        nome = str(row.get(col_nome, "-"))
        telefone = str(row.get(col_telefone, "-"))
        valor = format_money(row.get("valor_pagar", 0))
        status_atual = str(row.get("status_dash", "Em aberto"))

        c1, c2, c3, c4, c5 = st.columns([3.2, 1.5, 1.2, 1.4, 1.2])

        with c1:
            st.markdown(f"**{nome}**")
            st.caption(f"Telefone: {telefone}")

        with c2:
            st.markdown(f"**{valor}**")
            st.markdown(status_chip(status_atual), unsafe_allow_html=True)

        with c3:
            if st.button("✔ Pago", key=f"pago_{row['_row']}", use_container_width=True):
                update_status(row["_row"], "Pago")
                st.success(f"{nome}: status atualizado para Pago.")
                st.rerun()

        with c4:
            if st.button("⏳ Em aberto", key=f"aberto_{row['_row']}", use_container_width=True):
                update_status(row["_row"], "A Vencer")
                st.success(f"{nome}: status atualizado para A Vencer.")
                st.rerun()

        with c5:
            if st.button("⚠ Vencido", key=f"vencido_{row['_row']}", use_container_width=True):
                update_status(row["_row"], "Vencido")
                st.success(f"{nome}: status atualizado para Vencido.")
                st.rerun()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
