# ─────────────────────────────────────────────────────────────────────────────
# app.py  —  Entrada principal (UI)
# ─────────────────────────────────────────────────────────────────────────────
import os
import json
from datetime import datetime
import streamlit as st

from services.utils import carregar_json, logger
from services.learning_qdrant import get_confirmacoes, get_contexto_base, exportar_confirmacoes_json
from ui_components import (
    mostrar_sidebar,
    mostrar_saudacao,
    mostrar_chat_historico,
    input_mensagem,
    botoes_utilidade,
    indicador_intencao_ui,
)
from chat_logic import gerar_resposta, identificar_intencao

# =====================================================
# ⚙️ Configuração base
# =====================================================
st.set_page_config(
    page_title="🎆 Chat da Festa 2025/2026",
    page_icon="🎉",
    layout="wide",
)

# =====================================================
# 📂 Dados de perfis
# =====================================================
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
PERFIS_PATH = os.path.join(DATA_DIR, "profiles.json")

profiles = carregar_json(PERFIS_PATH, default=[])
if not profiles:
    st.error("⚠️ Faltam perfis em 'data/profiles.json'.")
    st.stop()

nomes = [p["nome"] for p in profiles]
params = st.query_params

# Seleção de utilizador por query param, com fallback para selectbox
if "user" in params and params["user"] in nomes:
    nome = params["user"]
else:
    col1, col2 = st.columns([3, 1])
    with col1:
        nome_sel = st.selectbox("Quem és tu?", nomes, index=0)
    with col2:
        if st.button("Confirmar"):
            st.query_params.update({"user": nome_sel})
            st.rerun()
    st.stop()

perfil = next(p for p in profiles if p["nome"] == nome)

# =====================================================
# 🎨 Layout geral (chat à esquerda, utilidades à direita)
# =====================================================
col_chat, col_side = st.columns([3, 1])

with col_side:
    # Sidebar compacta com confirmados e ações
    confirmados = get_confirmacoes()
    mostrar_sidebar(confirmados)

    # Utilidades (limpar, exportar histórico, atualizar confirmados JSON)
    botoes_utilidade()

with col_chat:
    # Saudação + histórico + input
    mostrar_saudacao(nome)
    mostrar_chat_historico()

    # Input adaptável (text_area)
    prompt = input_mensagem()

    if prompt:
        # Intenção (para badge/indicador visual)
        intencao = identificar_intencao(prompt)
        indicador_intencao_ui(intencao)

        with st.spinner("💭 A pensar..."):
            resposta = gerar_resposta(prompt, perfil)

        # Render das mensagens
        with st.chat_message("user"):
            st.markdown(f"**{nome}:** {prompt}")
        with st.chat_message("assistant"):
            st.markdown(f"**Assistente:** {resposta}")

        # Guardar no histórico (com hora)
        ts = datetime.now().strftime('%H:%M')
        if "historico" not in st.session_state:
            st.session_state.historico = []
        st.session_state.historico.append({"role": "user", "content": f"**{nome} ({ts}):** {prompt}"})
        st.session_state.historico.append({"role": "assistant", "content": f"**Assistente ({ts}):** {resposta}"})