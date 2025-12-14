import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
from pathlib import Path

px.defaults.template = "simple_white"
px.defaults.color_continuous_scale = px.colors.sequential.Tealgrn
PLOT_CONFIG = {
    "displaylogo": False,
    "toImageButtonOptions": {"filename": "dashboard-concursos"},
    "modeBarButtonsToRemove": ["autoScale2d"],
    "scrollZoom": True,
}
XLSX_PATH = Path(__file__).parent / "PERFIL_CUSTOS.xlsx"


def format_decimal_br(value: float) -> str:
    """
    Mostra valores decimais com duas casas no padrão brasileiro.
    """
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def style_decimal_df(df: pd.DataFrame):
    """Mantém apenas duas casas decimais nas colunas float ao exibir no Streamlit."""
    float_cols = df.select_dtypes(include=["float", "float64", "float32"]).columns
    if not len(float_cols):
        return df
    fmt = {col: (lambda x: format_decimal_br(x) if pd.notna(x) else "") for col in float_cols}
    return df.style.format(fmt)


def inject_styles():
    """Aplica tema visual mais profissional ao app."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap');
        :root {
            color-scheme: light;
            --bg-main: #f8fafc;
            --card: #ffffff;
            --stroke: rgba(15,23,42,0.08);
            --primary: #0f766e;
            --accent: #0ea5e9;
            --text: #0f172a;
            --muted: #475467;
        }
        * { font-family: 'Space Grotesk', 'Segoe UI', sans-serif; }
        html, body {
            background: var(--bg-main);
            color: var(--text);
        }
        .stApp {
            background:
                radial-gradient(circle at 12% 18%, rgba(14,165,233,0.08), transparent 28%),
                radial-gradient(circle at 88% 12%, rgba(16,185,129,0.08), transparent 24%),
                var(--bg-main);
        }
        [data-testid="stAppViewContainer"] > .main {
            padding-top: 1rem;
            padding-left: 1.2rem;
            padding-right: 1.2rem;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0b172a, #0b2f2a);
            color: #e2e8f0;
        }
        [data-testid="stSidebar"] * {
            color: #e2e8f0 !important;
        }
        [data-testid="stSidebar"] .stMultiSelect, [data-testid="stSidebar"] .stSelectbox {
            background: rgba(255,255,255,0.06);
        }
        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, rgba(16,185,129,0.12), rgba(14,165,233,0.10));
            border: 1px solid var(--stroke);
            padding: 14px 16px;
            border-radius: 16px;
            box-shadow: 0 16px 45px rgba(15,23,42,0.12);
        }
        div[data-testid="stMetricLabel"] {
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            font-size: 0.78rem;
            font-weight: 700;
        }
        div[data-testid="stMetricValue"] {
            color: var(--text);
            font-weight: 800;
            font-size: 1.9rem;
        }
        div[data-testid="stPlotlyChart"] {
            background: var(--card);
            border: 1px solid var(--stroke);
            border-radius: 16px;
            padding: 8px 8px 4px;
            box-shadow: 0 14px 40px rgba(15,23,42,0.08);
        }
        [data-testid="stDataFrame"] {
            background: var(--card);
            border: 1px solid var(--stroke);
            border-radius: 14px;
            box-shadow: 0 12px 36px rgba(15,23,42,0.06);
        }
        button[role="tab"] {
            background: var(--card);
            color: var(--text);
            border: 1px solid var(--stroke);
            border-radius: 12px !important;
            padding: 0.6rem 0.9rem;
            box-shadow: 0 8px 20px rgba(15,23,42,0.06);
            margin-right: 8px;
        }
        button[role="tab"][aria-selected="true"] {
            background: linear-gradient(120deg, #0f766e, #0ea5e9);
            color: #f8fafc;
            border: 1px solid transparent;
            box-shadow: 0 12px 32px rgba(14,165,233,0.25);
        }
        h1, h2, h3, h4, h5 {
            color: var(--text);
            letter-spacing: -0.02em;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

st.set_page_config(page_title="Dashboard - PERFIL | PAINEL | CUSTO", layout="wide")
inject_styles()

# =========================
# Leitura e limpeza
# =========================
@st.cache_data
def load_all():
    xlsx_file = XLSX_PATH
    if not xlsx_file.exists():
        raise FileNotFoundError("Arquivo PERFIL_CUSTOS.xlsx não encontrado no repositório.")

    # --- PERFIL ---
    perfil_raw = pd.read_excel(xlsx_file, sheet_name="PERFIL", engine="openpyxl")
    perfil_raw.columns = [c.strip() for c in perfil_raw.columns]

    # Mantém só colunas relevantes (as demais são artefatos de formatação)
    perfil_cols = [c for c in ["OM", "CARGOS", "NÍVEL", "ATIVIDADE", "REQUESITOS", "QTD"] if c in perfil_raw.columns]
    perfil = perfil_raw[perfil_cols].copy()
    if "CARGOS" in perfil.columns:
        perfil = perfil.dropna(subset=["CARGOS"]).reset_index(drop=True)

    # --- PAINEL ---
    painel_raw = pd.read_excel(xlsx_file, sheet_name="PAINEL", engine="openpyxl")
    painel_raw.columns = [c.strip() for c in painel_raw.columns]

    # A linha 1 (index 1) contém os nomes das OMs nas colunas "Unnamed: x"
    # No seu arquivo, as OMs válidas ficam em Unnamed: 2..8
    om_cols = []
    for idx, col in enumerate(painel_raw.columns):
        if idx >= 2:
            v = painel_raw.iloc[1, idx]
            if isinstance(v, str) and v.strip():
                om_cols.append((col, v.strip()))  # (coluna_unamed, nome_OM)

    # Dados começam a partir da linha 2 (index 2)
    data = painel_raw.iloc[2:].copy()
    data = data[data["PROFISSIONAIS"].apply(lambda x: isinstance(x, str) and x.strip() != "")].copy()
    data["QTD"] = pd.to_numeric(data["QTD"], errors="coerce")

    keep = ["PROFISSIONAIS", "QTD"] + [c for c, _ in om_cols]
    data = data[keep].copy()
    data = data.rename(columns={c: om for c, om in om_cols})

    painel_long = data.melt(
        id_vars=["PROFISSIONAIS", "QTD"],
        value_vars=[om for _, om in om_cols],
        var_name="OM",
        value_name="QTD_OM",
    )
    painel_long["QTD_OM"] = pd.to_numeric(painel_long["QTD_OM"], errors="coerce").fillna(0).astype(int)

    # --- CUSTO ---
    custo_raw = pd.read_excel(xlsx_file, sheet_name="CUSTO", engine="openpyxl")
    custo_raw.columns = [c.strip() for c in custo_raw.columns]

    # Remove as linhas de "cabeçalho mesclado" (onde PROFISSIONAIS está vazio)
    custo = custo_raw[custo_raw["PROFISSIONAIS"].notna()].copy()
    custo = custo[custo["PROFISSIONAIS"].apply(lambda x: isinstance(x, str) and x.strip() != "")].copy()

    # Converte colunas numéricas principais
    num_cols = [
        "VENC BÁSICO", "GDPGPE", "REMUN INDIV", "ENC. SOCIAIS/A", "AUX ALIM", "AUX TRANS",
        "CUSTO MENSAL", "CUSTO 12 MESES", "GRAT. NATALINA", "AD. FÉRIAS", "ENC. SOCIAIS/B",
        "CUSTO ANUAL INDIV", "CUSTO ANUAL TOTAL"
    ]
    for c in num_cols:
        if c in custo.columns:
            custo[c] = pd.to_numeric(custo[c], errors="coerce").round(2)
    if "QTD" in custo.columns:
        custo["QTD"] = pd.to_numeric(custo["QTD"], errors="coerce").astype("Int64")

    custo = custo.reset_index(drop=True)

    # --- Merge PAINEL x CUSTO para custo por OM ---
    custo_merge_cols = ["PROFISSIONAIS", "NÍVEL"] + [
        c for c in [
            "VENC BÁSICO", "GDPGPE", "REMUN INDIV", "ENC. SOCIAIS/A", "AUX ALIM", "AUX TRANS",
            "CUSTO MENSAL", "CUSTO 12 MESES", "GRAT. NATALINA", "AD. FÉRIAS", "ENC. SOCIAIS/B",
            "CUSTO ANUAL INDIV", "CUSTO ANUAL TOTAL"
        ] if c in custo.columns
    ]
    base = painel_long.merge(
        custo[custo_merge_cols],
        on="PROFISSIONAIS",
        how="left",
    )
    base["CUSTO_MENSAL_OM"] = (base["QTD_OM"] * base["CUSTO MENSAL"]).round(2)
    base["CUSTO_ANUAL_OM"] = (base["QTD_OM"] * base["CUSTO ANUAL INDIV"]).round(2)

    return perfil, data, painel_long, custo, base, [om for _, om in om_cols]

# =========================
# UI
# =========================
st.title("PAINEL - ANÁLISE DE PERFIL E CUSTO DE PESSOAL")

try:
    perfil, painel_matrix, painel_long, custo, base, oms = load_all()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

st.sidebar.subheader("Filtros")

oms = ["TODOS"] + oms
sel_om = st.sidebar.multiselect("OM", oms, default=["TODOS"])
nivels = sorted([x for x in base["NÍVEL"].dropna().unique()])
nivels = ["TODOS"] + nivels
sel_nivel = st.sidebar.multiselect("NÍVEL", nivels, default=["TODOS"])

profs = sorted([x for x in base["PROFISSIONAIS"].dropna().unique()])
profs = ["TODOS"] + profs
sel_prof = st.sidebar.multiselect("PROFISSIONAIS", profs, default=["TODOS"])

sel_om_values = [om for om in sel_om if om != "TODOS"]
sel_nivel_values = [n for n in sel_nivel if n != "TODOS"]
sel_prof_values = [p for p in sel_prof if p != "TODOS"]

mask = pd.Series(True, index=base.index)
if sel_om_values:
    mask &= base["OM"].isin(sel_om_values)
if sel_nivel_values:
    mask &= base["NÍVEL"].isin(sel_nivel_values)
if sel_prof_values:
    mask &= base["PROFISSIONAIS"].isin(sel_prof_values)

f = base[mask].copy()

# =========================
# KPIs
# =========================
total_qtd = int(f["QTD_OM"].sum())
total_custo_m = float(f["CUSTO_MENSAL_OM"].fillna(0).sum())
total_custo_a = float(f["CUSTO_ANUAL_OM"].fillna(0).sum())

cost_cols = [
    "VENC BÁSICO", "GDPGPE", "REMUN INDIV", "ENC. SOCIAIS/A", "AUX ALIM", "AUX TRANS",
    "CUSTO MENSAL", "CUSTO 12 MESES", "GRAT. NATALINA", "AD. FÉRIAS", "ENC. SOCIAIS/B",
    "CUSTO ANUAL TOTAL"
]
cost_totals = {
    col: float((f[col].fillna(0) * f["QTD_OM"]).sum()) if col in f.columns else 0.0
    for col in cost_cols
}
cost_totals["CUSTO MENSAL"] = total_custo_m
cost_totals["CUSTO ANUAL TOTAL"] = total_custo_a

metric_items = [
    ("Efetivo (QTD)", f"{total_qtd:,}".replace(",", ".")),
    ("Vencimento Básico (R$)", f"{cost_totals['VENC BÁSICO']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
    ("GDPGPE (R$)", f"{cost_totals['GDPGPE']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
    ("Remuneração Individual (R$)", f"{cost_totals['REMUN INDIV']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
    ("Enc. Sociais/A (R$)", f"{cost_totals['ENC. SOCIAIS/A']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
    ("Auxílio Alimentação (R$)", f"{cost_totals['AUX ALIM']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
    ("Custo Mensal (R$)", f"{cost_totals['CUSTO MENSAL']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
    ("Custo 12 Meses (R$)", f"{cost_totals['CUSTO 12 MESES']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
    ("Gratificação Natalina (R$)", f"{cost_totals['GRAT. NATALINA']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
    ("Adicional de Férias (R$)", f"{cost_totals['AD. FÉRIAS']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
    ("Enc. Sociais/B (R$)", f"{cost_totals['ENC. SOCIAIS/B']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
    ("Custo Anual Total (R$)", f"{cost_totals['CUSTO ANUAL TOTAL']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
]

for i in range(0, len(metric_items), 4):
    cols = st.columns(4)
    for col, (label, value) in zip(cols, metric_items[i:i+4]):
        col.metric(label, value)

st.divider()

# =========================
# Gráficos
# =========================
c1, c2 = st.columns(2)

with c1:
    st.subheader("Custo Anual por OM")
    g = f.groupby("OM", dropna=False)["CUSTO_ANUAL_OM"].sum().reset_index().sort_values("CUSTO_ANUAL_OM", ascending=False)
    fig = px.bar(
        g,
        y="OM",
        x="CUSTO_ANUAL_OM",
        orientation="h",
        color="CUSTO_ANUAL_OM",
        text="CUSTO_ANUAL_OM",
        color_continuous_scale=px.colors.sequential.Tealgrn,
    )
    fig.update_layout(
        font=dict(
            family="Space Grotesk, Segoe UI, sans-serif",
            size=13,
            color="#0f172a"
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>Custo anual: R$ %{x:,.2f}<extra></extra>",
        texttemplate="R$ %{x:,.2f}",
        marker_line_color="#1b4332",
        marker_line_width=0.6,
    )
    fig.update_layout(
        xaxis_title="Custo anual (R$)",
        yaxis_title=None,
        hovermode="y unified",
        coloraxis_showscale=False,
        bargap=0.25,
    )
    st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)

with c2:
    st.subheader("Efetivo (QTD) por OM")
    g2 = f.groupby("OM", dropna=False)["QTD_OM"].sum().reset_index().sort_values("QTD_OM", ascending=False)
    fig2 = px.bar(
        g2,
        x="OM",
        y="QTD_OM",
        color="QTD_OM",
        text="QTD_OM",
        color_continuous_scale=px.colors.sequential.Blues,
    )
    fig2.update_layout(
        font=dict(
            family="Space Grotesk, Segoe UI, sans-serif",
            size=13,
            color="#0f172a"
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig2.update_traces(
        hovertemplate="<b>%{x}</b><br>Efetivo: %{y:,}<extra></extra>",
        marker_line_color="#1f3b57",
        marker_line_width=0.6,
    )
    fig2.update_layout(
        xaxis_title=None,
        yaxis_title="Quantidade",
        hovermode="x unified",
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig2, use_container_width=True, config=PLOT_CONFIG)

c3, c4 = st.columns(2)

with c3:
    st.subheader("Top 15 – Custo Anual por Profissional (somando OMs)")
    g3 = f.groupby("PROFISSIONAIS", dropna=False)["CUSTO_ANUAL_OM"].sum().reset_index().sort_values("CUSTO_ANUAL_OM", ascending=False).head(15)
    fig3 = px.bar(
        g3,
        y="PROFISSIONAIS",
        x="CUSTO_ANUAL_OM",
        orientation="h",
        color="CUSTO_ANUAL_OM",
        text="CUSTO_ANUAL_OM",
        color_continuous_scale=px.colors.sequential.Tealgrn,
    )
    fig3.update_layout(
        font=dict(
            family="Space Grotesk, Segoe UI, sans-serif",
            size=13,
            color="#0f172a"
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig3.update_traces(
        hovertemplate="<b>%{y}</b><br>Custo anual: R$ %{x:,.2f}<extra></extra>",
        texttemplate="R$ %{x:,.2f}",
        marker_line_color="#1b4332",
        marker_line_width=0.6,
    )
    fig3.update_layout(
        xaxis_title="Custo anual (R$)",
        yaxis_title=None,
        hovermode="y unified",
        coloraxis_showscale=False,
        bargap=0.3,
        height=520,
    )
    st.plotly_chart(fig3, use_container_width=True, config=PLOT_CONFIG)

with c4:
    st.subheader("Distribuição por Nível")
    g4 = (
        f.groupby("NÍVEL", dropna=False)
        .agg(QTD=("QTD_OM","sum"), CUSTO_ANUAL=("CUSTO_ANUAL_OM","sum"))
        .reset_index()
        .sort_values("CUSTO_ANUAL", ascending=False)
    )
    fig4 = px.bar(
        g4,
        y="NÍVEL",
        x="CUSTO_ANUAL",
        orientation="h",
        color="QTD",
        text="QTD",
        color_continuous_scale=px.colors.sequential.Blues,
        custom_data=["QTD"],
    )
    fig4.update_layout(
        font=dict(
            family="Space Grotesk, Segoe UI, sans-serif",
            size=13,
            color="#0f172a"
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig4.update_traces(
        hovertemplate="<b>%{y}</b><br>Custo anual: R$ %{x:,.2f}<br>Efetivo: %{customdata[0]:,}<extra></extra>",
        marker_line_color="#1f3b57",
        marker_line_width=0.8,
        texttemplate="%{text:,}",
        textposition="outside",
    )
    fig4.update_layout(
        xaxis_title="Custo anual (R$)",
        yaxis_title=None,
        hovermode="y unified",
        coloraxis_showscale=False,
        showlegend=False,
        bargap=0.25,
    )
    st.plotly_chart(fig4, use_container_width=True, config=PLOT_CONFIG)

st.divider()

# =========================
# Tabelas (auditoria)
# =========================
t1, t2, t3, t4, t5 = st.tabs([
    "PERFIL",
    "PAINEL (matriz)",
    "CUSTO",
    "BASE (PAINEL x CUSTO)",
    "POR CARGO"
])

with t1:
    st.dataframe(style_decimal_df(perfil), use_container_width=True)

with t2:
    st.dataframe(style_decimal_df(painel_matrix), use_container_width=True)

with t3:
    custo_cols_order = [
        "PROFISSIONAIS", "NÍVEL", "QTD", "VENC BÁSICO", "GDPGPE", "REMUN INDIV",
        "ENC. SOCIAIS/A", "AUX ALIM", "AUX TRANS", "CUSTO MENSAL", "CUSTO 12 MESES",
        "GRAT. NATALINA", "AD. FÉRIAS", "ENC. SOCIAIS/B", "CUSTO ANUAL TOTAL"
    ]
    custo_view = custo[[c for c in custo_cols_order if c in custo.columns]]
    st.dataframe(style_decimal_df(custo_view), use_container_width=True)

with t4:
    cols = ["OM","PROFISSIONAIS","NÍVEL","QTD_OM","CUSTO MENSAL","CUSTO ANUAL INDIV","CUSTO_MENSAL_OM","CUSTO_ANUAL_OM"]
    cols = [c for c in cols if c in f.columns]
    st.dataframe(style_decimal_df(f[cols].sort_values(["OM","PROFISSIONAIS"])), use_container_width=True)

with t5:
    st.subheader("Visão por Cargo")
    cargos_disponiveis = sorted(perfil["CARGOS"].dropna().unique()) if "CARGOS" in perfil.columns else []
    if not cargos_disponiveis:
        st.info("Nenhum cargo encontrado na planilha PERFIL.")
    else:
        cargo_sel = st.selectbox("Cargo", cargos_disponiveis, key="cargo_tab")

        perfil_cargo = perfil[perfil["CARGOS"] == cargo_sel].copy()
        base_cargo = base[
            (base["PROFISSIONAIS"] == cargo_sel) &
            ((base["OM"].isin(sel_om_values)) if sel_om_values else True) &
            ((base["NÍVEL"].isin(sel_nivel_values)) if sel_nivel_values else True)
        ].copy()

        # Painel consolidado por OM que solicitou o cargo
        om_pedidos = base_cargo.groupby("OM", dropna=False).agg(
            QTD_SOLICITADA=("QTD_OM", "sum"),
            CUSTO_MENSAL_OM=("CUSTO_MENSAL_OM", "sum"),
            CUSTO_ANUAL_OM=("CUSTO_ANUAL_OM", "sum"),
        ).reset_index().sort_values("QTD_SOLICITADA", ascending=False)

        c_om, c_perfil = st.columns((1.2, 1))
        with c_om:
            st.markdown("**OMs que pediram esse cargo**")
            if om_pedidos.empty:
                st.info("Nenhuma OM solicitou esse cargo nos filtros atuais.")
            else:
                st.dataframe(
                    style_decimal_df(om_pedidos),
                    use_container_width=True,
                )

        with c_perfil:
            st.markdown("**Perfil profissiográfico e requisitos**")
            if perfil_cargo.empty:
                st.info("Sem perfil cadastrado para este cargo.")
            else:
                cols_show = [c for c in ["OM", "NÍVEL", "ATIVIDADE", "REQUESITOS", "QTD"] if c in perfil_cargo.columns]
                st.dataframe(perfil_cargo[cols_show], use_container_width=True)
