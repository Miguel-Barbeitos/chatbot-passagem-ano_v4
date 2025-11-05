import os
import streamlit as st
import json
import random
import time
import re
import unicodedata
from datetime import datetime

# Importações internas
from learning_qdrant import guardar_mensagem, get_contexto_base
from llm_groq import gerar_resposta_llm
from modules.confirmacoes import (
    confirmar_pessoa,
    get_confirmados,
    get_estatisticas,
    detectar_intencao_confirmacao,
    confirmar_familia_completa,
    verificar_confirmacao_pessoa
)
from modules.perfis_manager import buscar_perfil, listar_familia
from modules.organizacao import responder_pergunta_organizacao


# =====================================================
# ⚙️ CONFIGURAÇÃO
# =====================================================
USE_GROQ_ALWAYS = False
st.set_page_config(page_title="🎆 Chat da Festa 2025/2026", page_icon="🎉", layout="wide")

# =====================================================
# 🔧 FUNÇÕES AUXILIARES
# =====================================================
def normalizar(txt: str) -> str:
    if not isinstance(txt, str):
        return ""
    t = txt.lower().strip()
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

# =====================================================
# 📂 DADOS BASE (Qdrant)
# =====================================================
from modules.perfis_manager import listar_todos_perfis, buscar_perfil
perfis_lista = listar_todos_perfis()
nomes = sorted([p["nome"] for p in perfis_lista])

# =====================================================
# 🧍 UTILIZADOR ATUAL
# =====================================================
params = st.query_params
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

perfil_completo = buscar_perfil(nome) or next((p for p in perfis_lista if p["nome"] == nome), None)
if not perfil_completo:
    st.error(f"⚠️ Perfil de '{nome}' não encontrado!")
    st.stop()

# =====================================================
# 🎉 SIDEBAR — INFO DO EVENTO
# =====================================================
confirmados = get_confirmados()
stats = get_estatisticas()
with st.sidebar:
    st.markdown("### 🧍‍♂️ Confirmados")
    if confirmados:
        st.markdown(f"**Total: {stats['total_confirmados']}** | Famílias: {stats['familias_completas']}")
        for n in confirmados:
            st.markdown(f"- ✅ **{n}**")
    else:
        st.markdown("_Ainda ninguém confirmou 😅_")

# =====================================================
# 🤖 SISTEMA DE RESPOSTA
# =====================================================
def gerar_resposta(pergunta: str, perfil_completo: dict) -> str:
    nome = perfil_completo.get("nome", "amigo")
    pergunta_l = pergunta.lower().strip()
    contexto_base = get_contexto_base()
    contexto_conversa = st.session_state.get("historico", [])

    # PRIORIDADE 0: SAUDAÇÕES
    if any(p in pergunta_l for p in ["olá", "ola", "oi", "hey", "hi", "bom dia", "boa tarde", "boa noite"]):
        return f"Olá, {nome}! 👋 Como posso ajudar com a festa?"

    if any(p in pergunta_l for p in ["obrigado", "obrigada", "thanks"]):
        return "De nada! 😊 Estou aqui para ajudar!"

    if any(p in pergunta_l for p in ["tudo bem", "como estás", "como esta"]):
        return "Tudo ótimo por aqui! 🎉 E contigo?"

    # PRIORIDADE 1: ORGANIZAÇÃO / QUINTAS
    resposta_org = responder_pergunta_organizacao(pergunta)
    if resposta_org:
        return resposta_org

    # PRIORIDADE 2: CONFIRMAÇÕES DIRETAS
    if any(p in pergunta_l for p in ["confirmo", "vou", "eu vou", "conta comigo", "posso confirmar"]):
        intencao = detectar_intencao_confirmacao(pergunta)

        if intencao["tipo"] == "familia":
            familia_id = perfil_completo.get("familia_id")
            resultado = confirmar_familia_completa(familia_id, nome)
            if resultado["sucesso"]:
                return f"🎉 **Confirmado!** Toda a família vai:\n" + "\n".join([f"✅ {n}" for n in resultado["confirmados"]])
            return "❌ Erro ao confirmar família."

        elif intencao["tipo"] == "individual":
            resultado = confirmar_pessoa(nome, confirmado_por=nome)
            if resultado["sucesso"]:
                resposta = f"🎉 **{resultado['mensagem']}**"
                if resultado["familia_sugerida"]:
                    resposta += f"\n\n👨‍👩‍👧‍👦 Mais alguém da família vai?\n"
                    resposta += "\n".join([f"• {n}" for n in resultado["familia_sugerida"]])
                return resposta
            return f"❌ {resultado['mensagem']}"

    # PRIORIDADE 2.1: CONSULTAR QUEM VAI / CONFIRMOU
    tem_quinta = any(p in pergunta_l for p in ["quinta", "quintas", "sitio", "local", "reserva"])
    if not tem_quinta and any(p in pergunta_l for p in ["vai", "vem", "comparece", "presente", "confirmou"]):
        match_nome = re.search(
            r"\b([A-ZÁÉÍÓÚÂÊÎÔÛÃÕ][a-záéíóúâêîôûãõç]+(?:\s+[A-ZÁÉÍÓÚÂÊÎÔÛÃÕ][a-záéíóúâêîôûãõç]+)*)\b",
            pergunta
        )
        if match_nome:
            nome_mencionado = match_nome.group(1).strip()
            from modules.perfis_manager import normalizar_texto
            nome_mencionado = normalizar_texto(nome_mencionado)
            return verificar_confirmacao_pessoa(nome_mencionado)

    # PRIORIDADE 3: LLM (GERAL)
    resposta_llm = gerar_resposta_llm(
        pergunta=pergunta,
        perfil_completo=perfil_completo,
        contexto_base=contexto_base,
        contexto_conversa=contexto_conversa
    )
    guardar_mensagem(perfil_completo["nome"], pergunta, resposta_llm, contexto="geral", perfil=perfil_completo)
    return resposta_llm

# =====================================================
# 💬 INTERFACE DE CHAT
# =====================================================
if "mensagens" not in st.session_state:
    st.session_state.mensagens = []
if "historico" not in st.session_state:
    st.session_state.historico = []

for mensagem in st.session_state.mensagens:
    with st.chat_message(mensagem["role"]):
        st.markdown(mensagem["content"])

if prompt := st.chat_input("Escreve a tua mensagem..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.mensagens.append({"role": "user", "content": prompt})
    st.session_state.historico.append({"role": "user", "content": prompt})
    resposta = gerar_resposta(prompt, perfil_completo)
    with st.chat_message("assistant"):
        st.markdown(resposta)
    st.session_state.mensagens.append({"role": "assistant", "content": resposta})
    st.session_state.historico.append({"role": "assistant", "content": resposta})
