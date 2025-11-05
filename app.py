# -*- coding: utf-8 -*-
"""
Chatbot Passagem de Ano — app principal Streamlit
"""

import streamlit as st
from datetime import datetime
import unicodedata
import re

# Importações principais
from llm_groq import gerar_resposta_llm
from modules.organizacao import responder_pergunta_organizacao
from modules.confirmacoes import (
    confirmar_pessoa,
    get_confirmados,
    get_estatisticas,
    verificar_confirmacao_pessoa
)

st.set_page_config(page_title="🎉 Chatbot — Passagem de Ano", layout="centered")

# =====================================================
# 🔤 Funções auxiliares
# =====================================================

def normalizar_texto(txt):
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return txt.lower().strip()


def extrair_nome(pergunta):
    palavras = pergunta.split()
    nome = " ".join([p.capitalize() for p in palavras if p.isalpha()])
    return nome.strip()


# =====================================================
# 💬 Lógica principal
# =====================================================

def gerar_resposta(pergunta: str):
    pergunta_l = normalizar_texto(pergunta)

    # PRIORIDADE 1: CONFIRMAR PRESENÇA
    if any(p in pergunta_l for p in ["vou", "vamos", "confirmo", "confirmar", "estou dentro"]):
        nome = "Barbeitos"  # Podes substituir por identificação dinâmica no futuro
        resultado = confirmar_pessoa(nome, confirmado_por=nome)
        if resultado["sucesso"]:
            resposta = f"🎉 **{resultado['mensagem']}**"
            if resultado["familia_sugerida"]:
                resposta += f"\n\n👨‍👩‍👧‍👦 Mais alguém da família também vai:\n"
                resposta += "\n".join([f"• {n}" for n in resultado["familia_sugerida"]])
            return resposta
        else:
            return f"❌ {resultado['mensagem']}"

    # PRIORIDADE 2: CONSULTAR QUEM VAI / CONFIRMOU
    if any(p in pergunta_l for p in ["quem vai", "quem confirmou", "quem está confirmado"]):
        confirmados = get_confirmados()
        if confirmados:
            return f"🎉 Confirmaram: {', '.join(confirmados)}"
        else:
            return "😅 Ainda ninguém confirmou presença."

    # PRIORIDADE 3: CONSULTAR UMA PESSOA ESPECÍFICA
    nome_mencionado = None
    match = re.search(r"\b([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)\b", pergunta)
    if match:
        nome_mencionado = match.group(1)

    if nome_mencionado:
        return verificar_confirmacao_pessoa(nome_mencionado)

    # PRIORIDADE 4: ESTATÍSTICAS / QUANTOS SOMOS
    if any(p in pergunta_l for p in ["quantos somos", "somos quantos", "quem confirmou", "confirmados", "presentes"]):
        confirmados = get_confirmados()
        if confirmados:
            total = len(confirmados)
            return f"🎉 Somos {total} pessoas confirmadas até agora: {', '.join(confirmados)}"
        else:
            return "😅 Ainda ninguém confirmou presença."

    # PRIORIDADE 4B: ESTATÍSTICAS DETALHADAS
    if "quantos" in pergunta_l and any(p in pergunta_l for p in ["confirmados", "confirmou", "vão", "presentes"]):
        stats = get_estatisticas()
        return (
            f"📊 Confirmados: {stats.get('total_confirmados', 0)} pessoas\n"
            f"👨‍👩‍👧‍👦 Famílias completas: {stats.get('familias_completas', 0)}\n"
            f"👨‍👩‍👧 Famílias parciais: {stats.get('familias_parciais', 0)}\n"
            f"🕒 Última atualização: {stats.get('ultima_atualizacao', '—')}"
        )

    # PRIORIDADE 5: QUESTÕES DE ORGANIZAÇÃO
    if any(p in pergunta_l for p in ["quinta", "local", "hotel", "sitio", "onde vai ser", "dormir", "quintas"]):
        return responder_pergunta_organizacao(pergunta)

    # PRIORIDADE 6: FALLBACK → LLM (resposta gerada)
    perfil_mock = {"nome": "Barbeitos", "personalidade": {"humor": 5, "formalidade": 4, "emojis": 5}}
    return gerar_resposta_llm(pergunta, perfil_completo=perfil_mock)


# =====================================================
# 🌐 Interface Streamlit
# =====================================================

st.title("🎊 Chatbot — Passagem de Ano")
st.markdown("💬 Fala comigo!")

pergunta = st.text_input("Escreve a tua pergunta:")

if pergunta:
    with st.spinner("A pensar... 🤔"):
        resposta = gerar_resposta(pergunta)
    st.markdown(f"### 🤖 Resposta:\n{resposta}")
