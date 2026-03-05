import time
import re
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import date
from streamlit_autorefresh import st_autorefresh  # ✅ auto-refresh

# =========================================
# CONFIG
# =========================================
st.set_page_config(page_title="Zé do Pix — Dashboard", page_icon="💸", layout="wide")

# 🔄 Atualiza automaticamente a página (em ms)
# Ajuste aqui: 5_000 = 5s | 10_000 = 10s
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

# ✅ cache curtinho para atualizar quase imediato
@st.cache_data(ttl=5, show_spinner=False)
def load_data_cached(url: str) -> pd.DataFrame:
    return pd.read_csv(url)

def load_data(url: str, bust: bool = False) -> pd.DataFrame:
    if bust:
        url = url + f"&_ts={int(time.time()*1000)}"
    return load_data_cached(url)

# =========================================
# HEADER
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
    st.markdown("<div class='btn-navy'>", unsafe_allow_html=True)
    refresh_now = st.button("🔄 Atualizar agora", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================
# LOAD
# =========================================
csv_url = gsheet_csv_url(SHEET_ID, GID)

try:
    raw = load_data(csv_url, bust=refresh_now).copy()
except Exception as e:
    st.error(
        "Não consegui ler a planilha. Garanta que ela está acessível como 'Qualquer pessoa com o link (Leitor)' "
        "ou que foi 'Publicada na Web'."
    )
    st.exception(e)
    st.stop()

def pick(name):
    for c in raw.columns:
        if c.strip().lower() == name.strip().lower():
            return c
    return None

c_data = pick("Data do dia")
c_nome = pick("Emprestado")
c_ve = pick("Valor emprestado")
c_vp = pick("Valor a pagar")
c_venc = pick("Data do pagamento")
c_tel = pick("Telefone")
c_luc = pick("Lucro")

needed = [c_data, c_nome, c_ve, c_vp, c_venc]
if any(x is None for x in needed):
    st.error("Títulos de colunas diferentes do esperado. Use exatamente:")
    st.code("Data do dia | Emprestado | Valor emprestado | Valor a pagar | Data do pagamento | Telefone | Lucro")
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
df["status"] = "Em aberto"
df.loc[df["data_pagamento"].notna() & (df["data_pagamento"] < today), "status"] = "Vencido"
df.loc[df["data_pagamento"].isna(), "status"] = "Sem vencimento"

# =========================================
# FILTROS
# =========================================
st.markdown("---")
f1, f2, f3 = st.columns([1.2, 1.2, 1.6])

with f1:
    meses = sorted([m for m in df["mes_ref"].dropna().unique().tolist() if isinstance(m, str)])
    mes_sel = st.selectbox("Mês", options=["Todos"] + meses, index=(len(meses) if meses else 0))

with f2:
    status_sel = st.selectbox("Status", options=["Todos", "Em aberto", "Vencido", "Sem vencimento"])

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
qtd_vencidos = int((fdf["status"] == "Vencido").sum())
qtd_abertos = int((fdf["status"] == "Em aberto").sum())
ticket_medio = float(fdf["valor_emprestado"].mean()) if len(fdf) else 0.0

st.markdown(f"<p class='subtle'>Total de registros filtrados: <b>{total_registros}</b></p>", unsafe_allow_html=True)

st.markdown(
    f"""
    <div class="kpi-grid">
      <div class="kpi"><h4>💰 Total emprestado</h4><p class="big">{brl(total_emprestado)}</p><p class="small">soma do valor emprestado</p></div>
      <div class="kpi"><h4>📥 Total a receber</h4><p class="big">{brl(total_a_receber)}</p><p class="small">soma do valor a pagar</p></div>
      <div class="kpi"><h4>📈 Lucro estimado</h4><p class="big">{brl(lucro_total)}</p><p class="small">a pagar − emprestado</p></div>
      <div class="kpi"><h4>⏳ Em aberto</h4><p class="big">{qtd_abertos}</p><p class="small">a vencer / pendente</p></div>
      <div class="kpi"><h4>⚠️ Vencidos</h4><p class="big">{qtd_vencidos}</p><p class="small">vencimento &lt; hoje</p></div>
      <div class="kpi"><h4>🎯 Ticket médio</h4><p class="big">{brl(ticket_medio)}</p><p class="small">média emprestado</p></div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("")

# =========================================
# GRÁFICOS
# =========================================
g1, g2 = st.columns([1, 1], gap="large")

# ✅ Status por vencimento (VALOR total)
with g1:
    st.markdown("<div class='card'><h3>📌 Status por vencimento (valor total)</h3>", unsafe_allow_html=True)

    status_value = (
        fdf.groupby("status")["valor_a_pagar"]
        .sum()
        .reset_index()
        .rename(columns={"valor_a_pagar": "total"})
    )

    # labels BRL (para hover)
    status_value["label"] = status_value["total"].apply(brl)

    fig = px.pie(status_value, names="status", values="total", hole=0.6)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=360, showlegend=True)

    # Mostra valores (sem porcentagem)
    fig.update_traces(
        textinfo="label+value",
        hovertemplate="Status: %{label}<br>Total a pagar: %{customdata}<extra></extra>",
        customdata=status_value["label"],
    )

    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ✅ “Estatístico” de linha horizontal + valores no ponto (7 em 7 dias)
with g2:
    st.markdown("<div class='card'><h3>📈 Valor emprestado (a cada 7 dias)</h3>", unsafe_allow_html=True)

    tmp = fdf.dropna(subset=["data_dia"]).copy()
    tmp["data_dia"] = pd.to_datetime(tmp["data_dia"])
    tmp = tmp.set_index("data_dia")

    s = tmp["valor_emprestado"].resample("7D").sum()
    by_7d = s.reset_index()
    by_7d.columns = ["inicio_periodo", "total"]
    by_7d["inicio_periodo"] = pd.to_datetime(by_7d["inicio_periodo"])
    by_7d["label"] = by_7d["total"].apply(brl)

    fig2 = px.line(
        by_7d,
        x="inicio_periodo",
        y="total",
        markers=True,
        text="label",  # ✅ valor no ponto
    )
    fig2.update_traces(
        textposition="top center",
        hovertemplate="Período: %{x|%d/%m/%Y}<br>Total emprestado: %{text}<extra></extra>",
    )
    fig2.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=360,
        xaxis_title="",
        yaxis_title="",
    )
    fig2.update_xaxes(tickformat="%d/%m/%Y", tickangle=0, showgrid=True)
    fig2.update_yaxes(showgrid=True)

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

# ✅ “Estatístico” de linha horizontal + valores no ponto (vencimentos)
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
    venc["label"] = venc["total"].apply(brl)

    fig4 = px.line(
        venc,
        x="data",
        y="total",
        markers=True,
        text="label",  # ✅ valor no ponto
    )
    fig4.update_traces(
        textposition="top center",
        hovertemplate="Data: %{x|%d/%m/%Y}<br>Total a pagar: %{text}<extra></extra>",
    )
    fig4.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=360,
        xaxis_title="",
        yaxis_title="",
    )
    fig4.update_xaxes(tickformat="%d/%m/%Y", tickangle=0, showgrid=True)
    fig4.update_yaxes(showgrid=True)

    st.plotly_chart(fig4, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("")

# =========================================
# TABELA
# =========================================
st.markdown("<div class='card'><h3>🧾 Registros</h3>", unsafe_allow_html=True)

show_cols = [c for c in [c_data, c_nome, c_tel, c_ve, c_vp, c_venc] if c in fdf.columns]

view = fdf.copy()
view["Lucro (calc)"] = view["lucro"]
view["Status"] = view["status"]

table_cols = show_cols + ["Lucro (calc)", "Status"]
view_sorted = view.sort_values(by="data_dia", ascending=False, na_position="last")

st.dataframe(
    view_sorted[table_cols],
    use_container_width=True,
    height=420,
)

st.markdown("</div>", unsafe_allow_html=True)
