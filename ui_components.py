# ─────────────────────────────────────────────────────────────────────────────
# ui_components.py  —  Componentes reutilizáveis de UI
# ─────────────────────────────────────────────────────────────────────────────
import streamlit as st
import json
from services.utils import exportar_historico_local
from services.learning_qdrant import exportar_confirmacoes_json


def mostrar_sidebar(confirmados):
    st.markdown("### 🧍‍♂️ Confirmados")
    if confirmados:
        for nome in confirmados:
            st.markdown(f"- ✅ **{nome}**")
    else:
        st.markdown("_Ainda ninguém confirmou 😅_")


def mostrar_saudacao(nome: str):
    from datetime import datetime
    hora = datetime.now().hour
    saud = "Bom dia" if hora < 12 else "Boa tarde" if hora < 20 else "Boa noite"
    st.success(f"{saud}, {nome}! 👋 Bem-vindo! Eu sou o teu assistente virtual da festa 🎉")


def mostrar_chat_historico():
    if "historico" not in st.session_state:
        st.session_state.historico = []
    for msg in st.session_state.historico:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


def input_mensagem():
    # Text area para mensagens longas; cai para chat_input se preferires
    return st.text_area("Escreve a tua mensagem…", height=100, key="input_texto")


def botoes_utilidade():
    with st.expander("⚙️ Utilitários", expanded=True):
        cols = st.columns(3)
        with cols[0]:
            if st.button("🧹 Limpar chat"):
                st.session_state.historico = []
                st.toast("Histórico limpo ✨")
                st.rerun()
        with cols[1]:
            if st.button("💾 Exportar histórico"):
                exportar_historico_local(st.session_state.get("historico", []))
                st.success("Histórico exportado para 'data/chat_log.json' ✅")
        with cols[2]:
            if st.button("🔄 Atualizar confirmados (JSON)"):
                exportar_confirmacoes_json()
                st.success("Confirmados exportados para 'data/confirmados.json' ✅")


def indicador_intencao_ui(intencao: str):
    st.info(f"🧠 Intenção detetada: **{intencao}**")