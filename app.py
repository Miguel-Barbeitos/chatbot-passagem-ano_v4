# ─────────────────────────────────────────────────────────────────────────────
# app.py  —  Entrada principal (UI)
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys
from datetime import datetime
import streamlit as st

# 🧩 Diagnóstico automático: onde estamos realmente?
print("📍 Diretório atual (CWD):", os.getcwd())
print("📂 Conteúdo do diretório atual:", os.listdir())

# 🧠 Determinar raiz do projeto de forma robusta
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICES_DIR = os.path.join(BASE_DIR, "services")

if not os.path.exists(SERVICES_DIR):
    PARENT_DIR = os.path.dirname(BASE_DIR)
    SERVICES_DIR = os.path.join(PARENT_DIR, "services")
    if os.path.exists(SERVICES_DIR):
        BASE_DIR = PARENT_DIR

# Adicionar caminhos ao sys.path
for path in [BASE_DIR, SERVICES_DIR]:
    if path not in sys.path and os.path.exists(path):
        sys.path.append(path)
        print(f"✅ Adicionado ao sys.path: {path}")
    else:
        print(f"⚠️ Caminho inexistente ou já presente: {path}")

# Imports
from services.utils import carregar_json, logger
from services.learning_qdrant import get_confirmacoes, get_contexto_base, exportar_confirmacoes_json
from ui_components import (
    mostrar_sidebar,
    mostrar_saudacao,
    mostrar_chat_historico,
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

# Seleção de utilizador
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
    confirmados = get_confirmacoes()
    mostrar_sidebar(confirmados)
    botoes_utilidade()

with col_chat:
    mostrar_saudacao(nome)
    mostrar_chat_historico()

    # Input + botão "Enviar"
    col1, col2 = st.columns([6, 1])
    with col1:
        prompt = st.text_input("Escreve a tua mensagem…", key="input_mensagem")
    with col2:
        enviar = st.button("➡️", use_container_width=True)

    # Processar envio
    if (enviar or prompt) and prompt.strip():
        intencao = identificar_intencao(prompt)
        indicador_intencao_ui(intencao)

        with st.spinner("💭 A pensar..."):
            resposta = gerar_resposta(prompt, perfil)

        # Render mensagens
        with st.chat_message("user"):
            st.markdown(f"**{nome}:** {prompt}")
        with st.chat_message("assistant"):
            st.markdown(f"**Assistente:** {resposta}")

        # Guardar histórico
        ts = datetime.now().strftime('%H:%M')
        if "historico" not in st.session_state:
            st.session_state.historico = []
        st.session_state.historico.append(
            {"role": "user", "content": f"**{nome} ({ts}):** {prompt}"}
        )
        st.session_state.historico.append(
            {"role": "assistant", "content": f"**Assistente ({ts}):** {resposta}"}
        )

        # ✅ Limpar campo input de forma segura
        if "input_mensagem" in st.session_state:
            st.session_state["input_mensagem"] = ""
        else:
            st.session_state.setdefault("input_mensagem", "")

        st.rerun()
