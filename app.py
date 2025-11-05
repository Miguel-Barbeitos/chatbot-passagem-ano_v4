# -*- coding: utf-8 -*-
"""
App principal do Chatbot de Passagem de Ano 🎉
Integra confirmações, quintas e respostas gerais via LLM.
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
from modules.perfis_manager import listar_todos_perfis, buscar_perfil

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

pergunta = st.text_input(
    "Escreve a tua pergunta:",
    placeholder="Ex: Já temos quinta? ou O João Paulo vai?"
)
botao = st.button("Enviar")


# ======================================================
# FUNÇÃO PRINCIPAL DE RESPOSTA
# ======================================================

def gerar_resposta(pergunta: str):
    """Centraliza a lógica de decisão da resposta."""

    if not pergunta:
        return "😅 Podes repetir a pergunta?"

    pergunta_l = pergunta.lower().strip()

    # PRIORIDADE 1: Organização / Quintas
    resposta_org = responder_pergunta_organizacao(pergunta)
    if resposta_org:
        return resposta_org

    # PRIORIDADE 2: CONFIRMAÇÕES DE PESSOAS
    tem_quinta = any(p in pergunta_l for p in ["quinta", "quintas", "reserva", "local", "evento", "sítio", "sitio"])

    if not tem_quinta and any(p in pergunta_l for p in ["vai", "vem", "comparece", "presente", "confirmou"]):

        # Caso seja pergunta genérica (quem vai?)
        if pergunta_l.startswith("quem "):
            confirmados = get_confirmados()
            if confirmados:
                # Corrigido: confirmados já é lista de strings
                nomes_confirmados = confirmados
                if len(nomes_confirmados) > 10:
                    return (
                        "🎉 Até agora confirmaram: "
                        + ", ".join(nomes_confirmados[:10])
                        + f" ... e mais {len(nomes_confirmados) - 10}!"
                    )
                else:
                    return "🎉 Confirmaram: " + ", ".join(nomes_confirmados)
            else:
                return "😅 Ainda ninguém confirmou presença."

        # Procurar nome específico na pergunta
        palavras_ignoradas = {"o", "a", "os", "as", "vai", "vem", "foi", "irá", "comparece", "confirmou"}
        tokens = [w.capitalize() for w in re.findall(r"[A-Za-zÀ-ÿ]+", pergunta) if w.lower() not in palavras_ignoradas]

        if not tokens:
            return "🤔 Podes repetir quem queres confirmar?"

        # Considera nomes compostos (ex: João Paulo)
        nome_mencionado = " ".join(tokens[:2]) if len(tokens) >= 2 else tokens[0]

        perfil = buscar_perfil(nome_mencionado)
        if perfil:
            if perfil.get("confirmado"):
                return f"✅ Sim! {perfil['nome']} já confirmou presença."
            else:
                return f"❌ {perfil['nome']} ainda não confirmou presença."
        else:
            return f"🤔 Não encontrei ninguém chamado '{nome_mencionado}' na lista de convidados."

    # PRIORIDADE 3: ESTATÍSTICAS
    if "quantos" in pergunta_l and any(p in pergunta_l for p in ["confirmados", "confirmou", "vão", "presentes"]):
        stats = get_estatisticas()
        return (
            f"📊 Confirmados: {stats.get('total_confirmados', 0)} pessoas\n"
            f"👨‍👩‍👧‍👦 Famílias completas: {stats.get('familias_completas', 0)}\n"
            f"👨‍👩‍👧 Famílias parciais: {stats.get('familias_parciais', 0)}\n"
            f"🕒 Última atualização: {stats.get('ultima_atualizacao', '—')}"
        )

    # PRIORIDADE 4: INTENÇÕES DE CONFIRMAÇÃO
    if any(p in pergunta_l for p in ["confirmo", "vou", "conta comigo", "podes confirmar", "marca-me"]):
        resultado = confirmar_pessoa(nome_sel)
        return resultado["mensagem"]

    # PRIORIDADE 5: FALLBACK — LLM
    perfil_selecionado = next((p for p in perfis_lista if p.get("nome") == nome_sel), {})
    resposta_llm = gerar_resposta_llm(pergunta, perfil_completo=perfil_selecionado)
    return resposta_llm


# ======================================================
# EXECUÇÃO DO CHAT
# ======================================================

if botao and pergunta:
    resposta = gerar_resposta(pergunta)
    st.markdown("---")
    st.markdown(f"**🤖 Resposta:**\n\n{resposta}")

# ==============================
# RODAPÉ
# ==============================

st.markdown("---")
st.caption(f"© {datetime.now().year} — Chatbot Passagem de Ano 🎆")
