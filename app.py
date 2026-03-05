import time
import re
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import date, timedelta
import requests
from io import StringIO
from streamlit_autorefresh import st_autorefresh

# ===============================
# LOGIN (ANTES DO DASH) — MESMO DESIGN
# ===============================
APP_USER = "operacao"
APP_PASS = "100316"

def ensure_login() -> bool:
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if st.session_state.logged_in:
        return True

    st.set_page_config(page_title="Acesso ao Painel", page_icon="🔒", layout="wide")

    st.markdown(
        """
        <style>
          .stApp { background: #F3F4F6; }
          .block-container { padding-top: 24px; }
          .login-wrap{
              max-width: 980px;
              margin: 6vh auto 0 auto;
              padding: 0 18px;
              font-family: Inter, system-ui, -apple-system, Segoe UI, Arial, sans-serif;
          }
          .login-title{
              display:flex; align-items:center; gap:10px;
              font-size: 28px; font-weight: 800; color:#0B1F3B;
              margin-bottom: 6px;
          }
          .login-sub{ color:#6B7280; margin: 0 0 18px 0; }
          .login-card{
              background:#ffffff;
              border-radius:18px;
              border: 1px solid rgba(11,31,59,0.08);
              box-shadow: 0 12px 28px rgba(16,42,82,0.08);
              padding: 18px;
          }
          .login-btn button{
              background:#000000 !important;
              color:#ffffff !important;
              border: 0 !important;
              width: 100% !important;
              padding: 14px 14px !important;
              border-radius: 14px !important;
              font-weight: 800 !important;
          }
          .login-input label { font-weight:700 !important; color:#0B1F3B !important; }
          .stTextInput > div > div,
          .stPasswordInput > div > div{
              background: #EEF2F7 !important;
              border-radius: 12px !important;
              border: 1px solid rgba(11,31,59,0.10) !important;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="login-wrap">
          <div class="login-title">🔒 Acesso ao Painel</div>
          <p class="login-sub">Digite usuário e senha</p>
          <div class="login-card">
        """,
        unsafe_allow_html=True,
    )

    usuario = st.text_input("usuario", key="login_user", placeholder="usuario")
    senha = st.text_input("senha", key="login_pass", placeholder="senha", type="password")

    st.markdown('<div class="login-btn">', unsafe_allow_html=True)
    entrar = st.button("Entrar")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)

    if entrar:
        if usuario.strip() == APP_USER and senha.strip() == APP_PASS:
            st.session_state.logged_in = True
            st.success("Acesso liberado!")
            time.sleep(0.4)
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos.")

    return False


# Se não estiver logado, para aqui (não mostra o dashboard)
if not ensure_login():
    st.stop()

# =========================================
# DASHBOARD (continua igual)
# =========================================
st.set_page_config(page_title="Zé do Pix — Dashboard", page_icon="💸", layout="wide")
st_autorefresh(interval=10_000, key="ze_do_pix_autorefresh")

SHEET_ID = "1jZwhiehWGGqVNucPIB7URzrhg_-vASpwFJtgg1mI5Mg"
GID = "0"

def gsheet_csv_url(sheet_id: str, gid: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

# =========================================
# DESIGN (AZUL MARINHO)
# =========================================
NAVY = "#0B1F3B"
NAVY_2 = "#102A52"
BG = "#F5F7FB"
CARD_BG = "#FFFFFF"
MUTED = "#6B7280"

st.markdown(
    f"""
    <style>
      .stApp {{ background: {BG}; }}
      .block-container {{ padding-top: 24px; padding-bottom: 40px; }}
      .oppi-title {{ display:flex; gap:12px; align-items:center; margin-bottom:6px; }}
      .oppi-title h1 {{ font-size: 34px; margin:0; font-weight:800; color:{NAVY}; letter-spacing:-0.6px; }}
      .subtle {{ color:{MUTED}; margin-top: 0px; }}
      .kpi-grid {{
        display:grid;
        grid-template-columns: repeat(6, minmax(0, 1fr));
        gap: 14px;
        margin-top: 10px;
      }}
      @media (max-width: 1200px) {{ .kpi-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
      .kpi {{
        background:{CARD_BG};
        border-radius: 18px;
        padding: 16px 16px 14px 16px;
        box-shadow: 0 10px 24px rgba(16,42,82,0.06);
        border: 1px solid rgba(11,31,59,0.08);
        position: relative;
        overflow:hidden;
        min-height: 104px;
      }}
      .kpi:before {{
        content:"";
        position:absolute; left:0; top:0; bottom:0;
        width: 10px; background:{NAVY_2};
        border-top-left-radius: 18px;
        border-bottom-left-radius: 18px;
      }}
      .kpi h4 {{ margin:0 0 6px 0; color:{NAVY}; font-size: 14px; font-weight: 700; }}
      .kpi .big {{ font-size: 30px; font-weight: 900; color:{NAVY}; margin:0; line-height: 1.0; }}
      .kpi .small {{ margin-top: 6px; color:{MUTED}; font-size: 12px; }}
      .card {{
        background:{CARD_BG};
        border-radius: 18px;
        padding: 14px 14px 10px 14px;
        box-shadow: 0 10px 24px rgba(16,42,82,0.06);
        border: 1px solid rgba(11,31,59,0.08);
      }}
      .card h3 {{ margin: 2px 0 12px 0; color:{NAVY}; font-size: 16px; font-weight: 800; }}
      .btn-navy button {{
        background:{NAVY} !important;
        color:white !important;
        border: 0 !important;
        padding: 10px 14px !important;
        border-radius: 12px !important;
      }}
      .btn-outline button {{
        background: white !important;
        color: {NAVY} !important;
        border: 1px solid rgba(11,31,59,0.20) !important;
        padding: 10px 14px !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================
# HELPERS
# =========================================
def parse_brl_money(x) -> float:
    if pd.isna(x):
        return 0.0
    s = str(x).strip()
    if s == "":
        return 0.0
    s = s.replace("R$", "").replace(" ", "")
    s = re.sub(r"[^0-9,.\-]", "", s)
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except:
        return 0.0

def parse_date_br(x):
    if pd.isna(x) or str(x).strip() == "":
        return pd.NaT
    return pd.to_datetime(x, errors="coerce", dayfirst=True)

def brl(v: float) -> str:
    s = f"{v:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"

def normalize_status(s: str) -> str:
    if s is None:
        return ""
    t = str(s).strip().lower()
    if t == "" or t == "nan":
        return ""
    if any(k in t for k in ["pago", "paga", "recebid", "quitad", "liquidad"]):
        return "Pago"
    if any(k in t for k in ["a vencer", "aberto", "em aberto", "pendente"]):
        return "Em aberto"
    if any(k in t for k in ["vencid", "atras"]):
        return "Vencido"
    return str(s).strip()

def load_sheet_no_cache(csv_base_url: str) -> pd.DataFrame:
    url = csv_base_url + f"&_ts={int(time.time()*1000)}"
    r = requests.get(url, timeout=25, headers={"Cache-Control": "no-cache"})
    r.raise_for_status()
    return pd.read_csv(StringIO(r.text))

# =========================================
# HEADER + BOTÕES
# =========================================
l, r = st.columns([1, 1], vertical_alignment="center")
with l:
    st.markdown(
        """
        <div class="oppi-title"><h1>💸 Dashboard — Zé do Pix</h1></div>
        <p class="subtle">Painel de lançamentos, vencimentos e lucro estimado.</p>
        """,
        unsafe_allow_html=True,
    )

with r:
    b1, b2 = st.columns([1, 1])
    with b1:
        st.markdown("<div class='btn-navy'>", unsafe_allow_html=True)
        refresh_now = st.button("🔄 Atualizar agora", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with b2:
        st.markdown("<div class='btn-outline'>", unsafe_allow_html=True)
        sair = st.button("Sair", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

if sair:
    st.session_state.logged_in = False
    st.rerun()

if refresh_now:
    st.rerun()

# =========================================
# LOAD
# =========================================
csv_url = gsheet_csv_url(SHEET_ID, GID)

try:
    raw = load_sheet_no_cache(csv_url).copy()
except Exception as e:
    st.error("Não consegui ler a planilha. Garanta que ela está como 'Qualquer pessoa com o link (Leitor)'.")
    st.exception(e)
    st.stop()

def pick(name):
    for c in raw.columns:
        if c.strip().lower() == name.strip().lower():
            return c
    return None

c_data   = pick("Data do dia")
c_nome   = pick("Emprestado")
c_ve     = pick("Valor emprestado")
c_vp     = pick("Valor a pagar")
c_venc   = pick("Data do pagamento")
c_tel    = pick("Telefone")
c_luc    = pick("Lucro")
c_status = pick("Status")

needed = [c_data, c_nome, c_ve, c_vp, c_venc]
if any(x is None for x in needed):
    st.error("Títulos de colunas diferentes do esperado. Use exatamente:")
    st.code("Data do dia | Emprestado | Valor emprestado | Valor a pagar | Data do pagamento | Telefone | Status | Lucro")
    st.write("Encontrei:", list(raw.columns))
    st.stop()

df = raw.copy()
df["data_dia"] = df[c_data].apply(parse_date_br)
df["data_pagamento"] = df[c_venc].apply(parse_date_br)

df["valor_emprestado"] = df[c_ve].apply(parse_brl_money)
df["valor_a_pagar"] = df[c_vp].apply(parse_brl_money)

if c_luc is not None:
    df["lucro"] = df[c_luc].apply(parse_brl_money)
    if float(df["lucro"].sum()) == 0.0:
        df["lucro"] = df["valor_a_pagar"] - df["valor_emprestado"]
else:
    df["lucro"] = df["valor_a_pagar"] - df["valor_emprestado"]

df["mes_ref"] = df["data_dia"].dt.strftime("%m/%Y")

today = pd.to_datetime(date.today())

if c_status is not None:
    df["status_planilha"] = df[c_status].apply(normalize_status)
else:
    df["status_planilha"] = ""

df["status_calc"] = "Em aberto"
df.loc[df["data_pagamento"].notna() & (df["data_pagamento"] < today), "status_calc"] = "Vencido"
df.loc[df["data_pagamento"].isna(), "status_calc"] = "Sem vencimento"

df["status"] = df["status_planilha"]
df.loc[df["status"].astype(str).str.strip() == "", "status"] = df.loc[df["status"].astype(str).str.strip() == "", "status_calc"]

# =========================================
# FILTROS
# =========================================
st.markdown("---")
f1, f2, f3 = st.columns([1.2, 1.2, 1.6])

with f1:
    meses = sorted([m for m in df["mes_ref"].dropna().unique().tolist() if isinstance(m, str)])
    mes_sel = st.selectbox("Mês", options=["Todos"] + meses, index=(len(meses) if meses else 0))

with f2:
    status_opts = ["Todos"] + sorted(df["status"].dropna().unique().tolist())
    status_sel = st.selectbox("Status", options=status_opts)

with f3:
    nome_busca = st.text_input("Buscar por nome", placeholder="Ex: Nataly, Irene...")

fdf = df.copy()
if mes_sel != "Todos":
    fdf = fdf[fdf["mes_ref"] == mes_sel]
if status_sel != "Todos":
    fdf = fdf[fdf["status"] == status_sel]
if nome_busca.strip():
    fdf = fdf[fdf[c_nome].astype(str).str.contains(nome_busca.strip(), case=False, na=False)]

# =========================================
# KPIs
# =========================================
total_registros = int(len(fdf))
total_emprestado = float(fdf["valor_emprestado"].sum())
total_a_receber = float(fdf["valor_a_pagar"].sum())
lucro_total = float(fdf["lucro"].sum())

qtd_abertos = int((fdf["status"] == "Em aberto").sum())
qtd_vencidos = int((fdf["status"] == "Vencido").sum())
qtd_pagos = int((fdf["status"] == "Pago").sum())

st.markdown(f"<p class='subtle'>Total de registros filtrados: <b>{total_registros}</b></p>", unsafe_allow_html=True)

st.markdown(
    f"""
    <div class="kpi-grid">
      <div class="kpi"><h4>💰 Total emprestado</h4><p class="big">{brl(total_emprestado)}</p><p class="small">soma do valor emprestado</p></div>
      <div class="kpi"><h4>📥 Total a receber</h4><p class="big">{brl(total_a_receber)}</p><p class="small">soma do valor a pagar</p></div>
      <div class="kpi"><h4>📈 Lucro estimado</h4><p class="big">{brl(lucro_total)}</p><p class="small">a pagar − emprestado</p></div>
      <div class="kpi"><h4>💳 Pagos</h4><p class="big">{qtd_pagos}</p><p class="small">qtd (Status = Pago)</p></div>
      <div class="kpi"><h4>⏳ Em aberto</h4><p class="big">{qtd_abertos}</p><p class="small">a vencer / pendente</p></div>
      <div class="kpi"><h4>⚠️ Vencidos</h4><p class="big">{qtd_vencidos}</p><p class="small">vencimento &lt; hoje</p></div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("")

# =========================================
# GRÁFICOS
# =========================================
g1, g2 = st.columns([1, 1], gap="large")

with g1:
    st.markdown("<div class='card'><h3>📌 Status por vencimento (valor total)</h3>", unsafe_allow_html=True)

    status_value = (
        fdf.groupby("status")["valor_a_pagar"]
        .sum()
        .reset_index()
        .rename(columns={"valor_a_pagar": "total"})
    )
    status_value["label"] = status_value["total"].apply(brl)

    fig = px.pie(status_value, names="status", values="total", hole=0.6)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=360, showlegend=True)
    fig.update_traces(
        textinfo="label+value",
        hovertemplate="Status: %{label}<br>Total a pagar: %{customdata}<extra></extra>",
        customdata=status_value["label"],
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with g2:
    st.markdown("<div class='card'><h3>📊 Valor emprestado (últimos 7 dias)</h3>", unsafe_allow_html=True)

    tmp = fdf.dropna(subset=["data_dia"]).copy()
    tmp["data_dia"] = pd.to_datetime(tmp["data_dia"]).dt.date

    if tmp.empty:
        st.info("Sem dados com data para exibir.")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        base = max(tmp["data_dia"])
        inicio = base - timedelta(days=6)

        tmp = tmp[(tmp["data_dia"] >= inicio) & (tmp["data_dia"] <= base)]

        last7 = (
            tmp.groupby("data_dia")["valor_emprestado"]
            .sum()
            .reset_index()
            .rename(columns={"data_dia": "dia", "valor_emprestado": "total"})
        )

        full_days = pd.DataFrame({"dia": [inicio + timedelta(days=i) for i in range(7)]})
        last7 = full_days.merge(last7, on="dia", how="left").fillna({"total": 0.0})

        last7["dia_label"] = pd.to_datetime(last7["dia"]).dt.strftime("%d/%m/%Y")
        last7["label"] = last7["total"].apply(brl)
        last7 = last7.sort_values("dia", ascending=False)

        fig2 = px.bar(last7, y="dia_label", x="total", orientation="h", text="label")
        fig2.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=360,
            xaxis_title="Total (R$)",
            yaxis_title="Dia",
        )
        fig2.update_traces(
            textposition="outside",
            hovertemplate="Dia: %{y}<br>Total emprestado: %{text}<extra></extra>",
            cliponaxis=False,
        )

        st.plotly_chart(fig2, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown("")
g3, g4 = st.columns([1, 1], gap="large")

with g3:
    st.markdown("<div class='card'><h3>🏆 Top 10 (maior valor emprestado)</h3>", unsafe_allow_html=True)

    top = (
        fdf.groupby(fdf[c_nome].astype(str))["valor_emprestado"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
        .rename(columns={c_nome: "nome", "valor_emprestado": "total"})
    )

    fig3 = px.bar(top, x="nome", y="total")
    fig3.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=360, xaxis_title="")
    st.plotly_chart(fig3, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with g4:
    st.markdown("<div class='card'><h3>📅 Vencimentos (valor a pagar)</h3>", unsafe_allow_html=True)

    venc = (
        fdf.dropna(subset=["data_pagamento"])
        .groupby(pd.to_datetime(fdf["data_pagamento"]).dt.date)["valor_a_pagar"]
        .sum()
        .reset_index()
        .rename(columns={"data_pagamento": "data", "valor_a_pagar": "total"})
    )

    venc["data"] = pd.to_datetime(venc["data"])
    venc["data_label"] = venc["data"].dt.strftime("%d/%m/%Y")
    venc["label"] = venc["total"].apply(brl)

    TOP_N = 12
    venc = venc.sort_values("total", ascending=False).head(TOP_N).sort_values("total", ascending=True)

    fig4 = px.bar(venc, y="data_label", x="total", orientation="h", text="label")
    fig4.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=360, xaxis_title="Total a pagar (R$)", yaxis_title="Data")
    fig4.update_traces(textposition="outside", hovertemplate="Data: %{y}<br>Total a pagar: %{text}<extra></extra>", cliponaxis=False)
    st.plotly_chart(fig4, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("")

# =========================================
# TABELA
# =========================================
st.markdown("<div class='card'><h3>🧾 Registros</h3>", unsafe_allow_html=True)

show_cols = [c for c in [c_data, c_nome, c_tel, c_ve, c_vp, c_venc, c_status] if c and c in fdf.columns]

view = fdf.copy()
view["Lucro (calc)"] = view["lucro"]
view["Status (usado no dash)"] = view["status"]

table_cols = show_cols + ["Lucro (calc)", "Status (usado no dash)"]
view_sorted = view.sort_values(by="data_dia", ascending=False, na_position="last")

st.dataframe(view_sorted[table_cols], use_container_width=True, height=420)
st.markdown("</div>", unsafe_allow_html=True)
