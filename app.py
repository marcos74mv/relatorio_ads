import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Relatório Meta Ads", layout="wide")

st.title("📊 Relatório de Campanha – Meta Ads")
st.write("Carregue o CSV exportado do Meta Ads para gerar o relatório automático.")

# ======================
# 1. Upload do arquivo
# ======================
uploaded_file = st.file_uploader("Envie o arquivo CSV do Meta Ads", type=["csv"])

@st.cache_data
def carregar_e_tratar_dados(file):
    df = pd.read_csv(file)

    # Renomear colunas para nomes mais simples
    df.columns = [
        "anuncio", "criativo", "alcance", "impressoes", "frequencia",
        "moeda", "valor_usado", "atribuicao", "cliques_link",
        "cpc", "cpm", "engajamento", "conversas_mensagem",
        "custo_por_conversa", "ctr", "inicio", "fim"
    ]

    # --- Limpeza numérica ---

    def limpa_dinheiro(serie):
        s = (
            serie.astype(str)
            .str.replace("R$", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        return pd.to_numeric(s, errors="coerce")

    # valor investido
    df["valor_usado"] = limpa_dinheiro(df["valor_usado"])

    # cpc / cpm / custo por conversa
    for col in ["cpc", "cpm", "custo_por_conversa"]:
        df[col] = limpa_dinheiro(df[col])

    # ctr em decimal
    df["ctr"] = (
        df["ctr"]
        .astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    df["ctr"] = pd.to_numeric(df["ctr"], errors="coerce") / 100

    # numéricos básicos
    numeric_cols = [
        "alcance", "impressoes", "frequencia", "cliques_link",
        "engajamento", "conversas_mensagem"
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # datas
    df["inicio"] = pd.to_datetime(df["inicio"], errors="coerce")
    df["fim"] = pd.to_datetime(df["fim"], errors="coerce")

    # --- separar total x criativos ---

    # no seu arquivo, a linha 0 tem criativo NaN = total
    mask_total = df["criativo"].isna()
    df_total = df.loc[mask_total].reset_index(drop=True)
    df_criativos = df.loc[~mask_total].reset_index(drop=True)

    # pegar somente uma linha de total (a primeira)
    linha_total = df_total.iloc[0] if len(df_total) > 0 else None

    # criar versões formatadas para exibição
    def formata_reais(x):
        if pd.isna(x):
            return "-"
        return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    df_formatado = df_criativos.copy()
    df_formatado["valor_usado"] = df_formatado["valor_usado"].apply(formata_reais)
    df_formatado["cpc"] = df_formatado["cpc"].apply(formata_reais)
    df_formatado["cpm"] = df_formatado["cpm"].apply(formata_reais)
    df_formatado["custo_por_conversa"] = df_formatado["custo_por_conversa"].apply(formata_reais)
    df_formatado["ctr"] = df_formatado["ctr"].apply(
        lambda x: "-" if pd.isna(x) else f"{x*100:.2f}%"
    )

    return df, df_criativos, df_formatado, linha_total


if uploaded_file is not None:
    df_raw, df_criativos_num, df_criativos_fmt, total = carregar_e_tratar_dados(uploaded_file)

    st.success("Arquivo carregado com sucesso! ✅")

    # ======================
    # 2. KPIs gerais
    # ======================
    st.subheader("Visão geral da campanha")

    col1, col2, col3, col4 = st.columns(4)

    investimento_total = total["valor_usado"]
    impressoes_totais = total["impressoes"]
    alcance_total = total["alcance"]
    cliques_totais = total["cliques_link"]
    conversas_totais = total["conversas_mensagem"]
    ctr_medio = total["ctr"]
    cpc_medio = total["cpc"]
    cpm_medio = total["cpm"]

    col1.metric("Investimento total", f"R$ {investimento_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col2.metric("Impressões", f"{int(impressoes_totais):,}".replace(",", "."))
    col3.metric("Alcance", f"{int(alcance_total):,}".replace(",", "."))
    col4.metric("CTR médio", f"{ctr_medio*100:.2f}%")

    col5, col6, col7 = st.columns(3)
    col5.metric("Cliques no link", f"{int(cliques_totais):,}".replace(",", "."))
    col6.metric("CPC médio", f"R$ {cpc_medio:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col7.metric("CPM médio", f"R$ {cpm_medio:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    # ======================
    # 3. Tabela por criativo
    # ======================
    st.subheader("Desempenho por criativo")

    colunas_meta = [
        "criativo",
        "alcance",
        "impressoes",
        "frequencia",
        "valor_usado",
        "cliques_link",
        "cpc",
        "cpm",
        "engajamento",
        "conversas_mensagem",
        "custo_por_conversa",
        "ctr"
    ]

    st.dataframe(df_criativos_fmt[colunas_meta], use_container_width=True)

    # ======================
    # 4. Gráficos
    # ======================
    st.subheader("Gráficos de performance")

    # garantir que não usamos a linha de total aqui
    df_plot = df_criativos_num.copy()

    # evitar NaN em criativo
    df_plot["criativo"] = df_plot["criativo"].fillna("Sem nome")

    tab1, tab2, tab3 = st.tabs(["CTR por criativo", "CPC por criativo", "CPM por criativo"])

    with tab1:
        st.bar_chart(df_plot.set_index("criativo")["ctr"])

    with tab2:
        st.bar_chart(df_plot.set_index("criativo")["cpc"])

    with tab3:
        st.bar_chart(df_plot.set_index("criativo")["cpm"])

    # ======================
    # 5. Download em Excel
    # ======================
    st.subheader("Exportar relatório")

    df_export = df_criativos_num.copy()
    df_export["ctr_percent"] = df_export["ctr"] * 100

    @st.cache_data
    def to_excel(df):
        out = pd.ExcelWriter("relatorio_meta_ads.xlsx", engine="xlsxwriter")
        df.to_excel(out, index=False, sheet_name="Relatorio")
        out.close()
        with open("relatorio_meta_ads.xlsx", "rb") as f:
            return f.read()

    if st.button("Gerar arquivo Excel"):
        xlsx_bytes = to_excel(df_export)
        st.download_button(
            label="Baixar Excel",
            data=xlsx_bytes,
            file_name="relatorio_meta_ads.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.info("Envie o CSV para começar o relatório.")