# -*- coding: utf-8 -*-
"""
App principal do Chatbot de Passagem de Ano
"""

import streamlit as st
import re
from datetime import datetime

# Importações principais
from llm_groq import gerar_resposta_llm
from modules.organizacao import responder_pergunta_organizacao
from modules.confirmacoes import (
    confirmar_pessoa,
    get_confirmados,
    get_estatisticas,
  
)
from modules.perfis_manager import listar_todos_perfis, normalizar_texto

# ==============================
# CONFIGURAÇÃO DA APP
# ==============================

st.set_page_config(page_title="Chatbot Passagem de Ano", layout="centered")
st.title("🎉 Chatbot Passagem de Ano")

# ==============================
# SECÇÃO: PERFIL DO UTILIZADOR
# ==============================

st.markdown("### 👤 Quem és tu?")

perfis_lista = listar_todos_perfis()

# Evita nomes repetidos e perfis sem nome
nomes = sorted(set(p["nome"] for p in perfis_lista if p.get("nome")))

col1, col2 = st.columns([3, 1])
with col1:
    nome_sel = st.selectbox("Quem és tu?", nomes, index=0)
with col2:
    confirmar = st.button("Confirmar Presença 🎟️")

if confirmar:
    resultado = confirmar_pessoa(nome_sel)
    st.success(resultado["mensagem"])

# ==============================
# SECÇÃO: CHAT PRINCIPAL
# ==============================

st.markdown("---")
st.markdown("### 💬 Fala comigo!")

pergunta = st.text_input("Escreve a tua pergunta:", placeholder="Ex: Já temos quinta? ou O João Paulo vai?")
botao = st.button("Enviar")

def gerar_resposta(pergunta: str):
    """Centraliza a lógica de decisão da resposta."""

    if not pergunta:
        return "😅 Podes repetir a pergunta?"

    pergunta_l = pergunta.lower().strip()

    # ======================================================
    # PRIORIDADE 1: ORGANIZAÇÃO / QUINTAS
    # ======================================================
    resposta_org = responder_pergunta_organizacao(pergunta)
    if resposta_org:
        return resposta_org

    # ======================================================
    # PRIORIDADE 2: CONFIRMAÇÕES
    # ======================================================
    tem_quinta = any(p in pergunta_l for p in ["quinta", "quintas", "reserva", "local", "evento", "sítio", "sitio"])

    if not tem_quinta and any(p in pergunta_l for p in ["vai", "vem", "comparece", "presente", "confirmou"]):

        # Ignorar perguntas genéricas como "quem vai?" ou "quem confirmou?"
        if pergunta_l.startswith("quem "):
            confirmados = get_confirmados()
            if confirmados:
                lista = ", ".join(confirmados[:10])
                extra = f" ... e mais {len(confirmados) - 10}" if len(confirmados) > 10 else ""
                return f"🎉 Até agora confirmaram: {lista}{extra}."
            else:
                return "😅 Ainda ninguém confirmou presença."

        # Caso haja um nome na pergunta
        match_nome = re.search(
            r"\b([A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+)*)\b",
            pergunta,
            flags=re.IGNORECASE
        )

        if match_nome:
            nome_mencionado = match_nome.group(1).strip()
            nome_mencionado = normalizar_texto(nome_mencionado)
            return verificar_confirmacao_pessoa(nome_mencionado)

    # ======================================================
    # PRIORIDADE 3: ESTATÍSTICAS DE CONFIRMAÇÕES
    # ======================================================
    if "quantos" in pergunta_l and any(p in pergunta_l for p in ["confirmados", "confirmou", "vão", "presentes"]):
        stats = get_estatisticas()
        return (
            f"📊 Confirmados: {stats['total_confirmados']} pessoas\n"
            f"👨‍👩‍👧‍👦 Famílias completas: {stats['familias_completas']}\n"
            f"🏡 Famílias parciais: {stats['familias_parciais']}"
        )

    # ======================================================
    # PRIORIDADE 4: INTENÇÕES DE CONFIRMAÇÃO
    # ======================================================
    if any(p in pergunta_l for p in ["confirmo", "vou", "conta comigo", "podes confirmar", "marca-me"]):
        resultado = confirmar_pessoa(nome_sel)
        return resultado["mensagem"]

    # ======================================================
    # PRIORIDADE 5: FALLBACK — LLM
    # ======================================================
    perfil_selecionado = None
    for p in perfis_lista:
        if p.get("nome") == nome_sel:
            perfil_selecionado = p
            break

    if not perfil_selecionado:
        perfil_selecionado = {}

    resposta_llm = gerar_resposta_llm(pergunta, perfil_completo=perfil_selecionado)
    return resposta_llm


if botao and pergunta:
    resposta = gerar_resposta(pergunta)
    st.markdown("---")
    st.markdown(f"**🤖 Resposta:**\n\n{resposta}")

# ==============================
# RODAPÉ
# ==============================

st.markdown("---")
st.caption(f"© {datetime.now().year} — Chatbot Passagem de Ano 🎆")
