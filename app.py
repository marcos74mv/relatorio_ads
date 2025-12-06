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

    def reais(x: float) -> str:
        if pd.isna(x):
            return "-"
        return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def inteiro_br(x: float) -> str:
        if pd.isna(x):
            return "-"
        return f"{int(x):,}".replace(",", ".")

    investimento_total = total["valor_usado"]
    impressoes_totais = total["impressoes"]
    alcance_total = total["alcance"]
    cliques_totais = total["cliques_link"]
    conversas_totais = total["conversas_mensagem"]
    engaj_total = total["engajamento"]
    ctr_medio = total["ctr"]
    cpc_medio = total["cpc"]
    cpm_medio = total["cpm"]
    freq_media = total["frequencia"]
    custo_conversa_medio = total["custo_por_conversa"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Investimento total", reais(investimento_total))
    col2.metric("Impressões", inteiro_br(impressoes_totais))
    col3.metric("Alcance", inteiro_br(alcance_total))
    col4.metric("Frequência média", f"{freq_media:.2f}x")

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Cliques no link", inteiro_br(cliques_totais))
    col6.metric("Conversas iniciadas", inteiro_br(conversas_totais))
    col7.metric("CTR médio", f"{ctr_medio*100:.2f}%")
    col8.metric("CPC médio", reais(cpc_medio))

    col9, col10 = st.columns(2)
    col9.metric("CPM médio", reais(cpm_medio))
    col10.metric("Custo médio por conversa", reais(custo_conversa_medio))

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
    # 4. Texto pronto para WhatsApp
    # ======================
    st.subheader("Texto pronto para enviar no WhatsApp")

    data_inicio = total["inicio"].date() if not pd.isna(total["inicio"]) else None
    data_fim = total["fim"].date() if not pd.isna(total["fim"]) else None

    if data_inicio and data_fim:
        periodo_str = f"{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}"
    else:
        periodo_str = "período da campanha"

    texto_whatsapp = f"""
Relatório da campanha de Meta Ads ({periodo_str}) 📊

💰 Investimento total: {reais(investimento_total)}
👥 Alcance: {inteiro_br(alcance_total)} pessoas
📣 Impressões: {inteiro_br(impressoes_totais)}
🔁 Frequência média: {freq_media:.2f}x

🖱️ Cliques no link: {inteiro_br(cliques_totais)}
📨 Conversas iniciadas: {inteiro_br(conversas_totais)}
👍 Engajamentos: {inteiro_br(engaj_total)}

📊 Métricas de eficiência:
• CTR (taxa de cliques): {ctr_medio*100:.2f}%
• CPC médio (custo por clique): {reais(cpc_medio)}
• CPM médio (custo por mil impressões): {reais(cpm_medio)}
• Custo médio por conversa: {reais(custo_conversa_medio)}

Resumo geral:
A campanha está alcançando um público relevante, com bom volume de impressões, cliques e conversas pelo WhatsApp, mantendo um custo eficiente por clique e por conversa. Qualquer dúvida, posso te explicar cada métrica em detalhes 😊
""".strip()

    st.text_area(
        "Copie o texto abaixo e envie para o cliente pelo WhatsApp:",
        value=texto_whatsapp,
        height=350
    )

    # ======================
    # 5. Significado das siglas
    # ======================
    st.subheader("Significado das métricas e siglas")

    st.markdown("""
**Alcance** – Número de pessoas únicas que viram o anúncio pelo menos uma vez.  
**Impressões** – Quantidade total de vezes que o anúncio foi exibido (a mesma pessoa pode ver mais de uma vez).  
**Frequência** – Média de vezes que cada pessoa viu o anúncio (impressões ÷ alcance).  

**CTR (Click Through Rate)** – Taxa de cliques. É a porcentagem de cliques em relação ao total de impressões  
→ Fórmula: `CTR = cliques / impressões`.

**CPC (Custo Por Clique)** – Quanto você paga, em média, por cada clique no anúncio.  
→ Fórmula: `CPC = investimento / cliques`.

**CPM (Custo Por Mil Impressões)** – Quanto custa, em média, para exibir o anúncio mil vezes.  
→ Fórmula: `CPM = investimento / impressões * 1000`.

**Custo por conversa** – Quanto custa, em média, cada conversa iniciada a partir do anúncio.  
→ Fórmula: `Custo por conversa = investimento / conversas`.

**Engajamento** – Soma de interações com a página/anúncio (curtidas, comentários, compartilhamentos e outras ações de engajamento).  
""")

    # ======================
    # 6. Exportar dados (opcional)
    # ======================
    st.subheader("Exportar dados numéricos (opcional)")

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
