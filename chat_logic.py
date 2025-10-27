# ─────────────────────────────────────────────────────────────────────────────
# chat_logic.py  —  Regras e fluxo do chat
# ─────────────────────────────────────────────────────────────────────────────
import re
import streamlit as st
from services.utils import normalizar
from services.learning_qdrant import (
    guardar_mensagem,
    guardar_confirmacao,
    get_confirmacoes,
    get_contexto_base,
    identificar_intencao as _identificar_intencao_base,
)
from services.llm_groq import gerar_resposta_llm


INTENCOES = {
    "saudacao": ["ola", "olá", "bom dia", "boa tarde", "boa noite", "oi", "hey"],
    "confirmacao": ["confirmo", "vou", "lá estarei", "sim vou", "confirmar"],
    "confirmados": ["quem vai", "quem confirmou", "quantos somos", "quantos sao"],
    "quintas": ["que quintas", "quais quintas", "quantas quintas", "opcoes", "opções", "lista", "nomes"],
}


def identificar_intencao(pergunta: str) -> str:
    p = normalizar(pergunta)
    # Primeiro tenta o classificador simples do módulo base
    base = _identificar_intencao_base(pergunta)
    if base and base != "geral":
        return base
    # Depois, o dicionário local
    for k, termos in INTENCOES.items():
        if any(t in p for t in termos):
            return k
    return "geral"


def gerar_resposta(pergunta: str, perfil: dict) -> str:
    pergunta_l = normalizar(pergunta)
    contexto_base = get_contexto_base(raw=True)

    # 1) Intenções rápidas
    intent = identificar_intencao(pergunta)

    if intent == "saudacao" and len(pergunta_l.split()) <= 4:
        return (
            f"Olá, {perfil['nome']}! 👋\n\n"
            "Estamos a organizar os detalhes da festa de passagem de ano 🎆\n"
            "Diz-me no que posso ajudar!"
        )

    if intent == "confirmacao":
        guardar_confirmacao(perfil["nome"])
        return f"Boa, {perfil['nome']} 🎉 Já estás na lista! Vê a lista ao lado 👈"

    if intent == "confirmados":
        return "Vê a lista de confirmados ao lado 👈"

    # 2) Perguntas sobre quintas → LLM/SQL no serviço dedicado
    if "quinta" in pergunta_l or intent == "quintas":
        resposta_llm = gerar_resposta_llm(
            pergunta=pergunta,
            perfil=perfil,
            contexto_base=contexto_base,
        )
        guardar_mensagem(perfil["nome"], pergunta, resposta_llm, contexto="quintas", perfil=perfil)
        return resposta_llm

    # 3) Perguntas genéricas sobre local/estado
    if any(p in pergunta_l for p in ["sitio", "local", "onde", "quinta", "ja ha", "reservado", "fechado", "decidido", "ja temos"]) and not any(p in pergunta_l for p in ["que", "quais", "quantas", "lista"]):
        return (
            "Ainda estamos a ver o local final 🏡\n\n"
            "Já temos o **Monte da Galega** reservado como plano B, mas estamos a contactar outras quintas.\n"
            "Pergunta-me sobre as quintas que já vimos! 😊"
        )

    # 4) Características específicas (respostas curtas)
    if "piscina" in pergunta_l:
        return "Ainda não temos quinta fechada, mas já perguntámos quais têm piscina 🏊 Queres saber quais são?"
    if "churrasqueira" in pergunta_l or "grelhados" in pergunta_l:
        return "Ainda não decidimos o local, mas já sabemos quais quintas têm churrasqueira 🔥 Queres que te diga?"
    if "snooker" in pergunta_l:
        return "Ainda estamos a decidir o local, mas já vimos quintas com snooker 🎱 Pergunta-me sobre as opções!"
    if any(p in pergunta_l for p in ["animais", "cao", "cão", "gato"]):
        return "Ainda não fechámos o local, mas posso dizer-te quais quintas aceitam animais 🐶 Queres saber?"

    # 5) Progresso
    if any(p in pergunta_l for p in ["fizeram", "fizeste", "andaram a fazer", "trabalho", "progresso"]):
        return (
            "Já contactámos várias quintas e temos o **Monte da Galega** reservado como backup 🏡 "
            "Pergunta-me sobre quintas específicas, zonas, preços ou capacidades! 😊"
        )

    # 6) Caso geral → LLM evento
    resposta_llm = gerar_resposta_llm(
        pergunta=pergunta,
        perfil=perfil,
        contexto_base=contexto_base,
    )
    guardar_mensagem(perfil["nome"], pergunta, resposta_llm, contexto="geral", perfil=perfil)
    return resposta_llm