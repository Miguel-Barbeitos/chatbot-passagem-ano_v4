import os
import streamlit as st
import json
import random
import time
import re
import unicodedata
from datetime import datetime

# Importações internas
from learning_qdrant import (
    guardar_mensagem,
    guardar_confirmacao,
    get_confirmacoes,
    get_contexto_base,
)
from llm_groq import gerar_resposta_llm 

# =====================================================
# ⚙️ CONFIGURAÇÃO
# =====================================================
USE_GROQ_ALWAYS = False  # 👈 muda para True se quiseres usar sempre o LLM

# =====================================================
# 🎨 LAYOUT E VISUAL
# =====================================================
st.set_page_config(
    page_title="🎆 Chat da Festa 2025/2026",
    page_icon="🎉",
    layout="wide",
)

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

def carregar_json(path, default=None):
    import json
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"⚠️ Erro a carregar JSON em {path}: {e}")
        return default or []

# =====================================================
# 📂 DADOS BASE
# =====================================================
profiles_path = os.path.join(os.path.dirname(__file__), "data", "profiles.json")
profiles = carregar_json(profiles_path, default=[])
if not profiles:
    st.error("⚠️ Faltam perfis em 'profiles.json'.")
    st.stop()

# =====================================================
# 🧍 UTILIZADOR ATUAL
# =====================================================
nomes = [p["nome"] for p in profiles]
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

perfil = next(p for p in profiles if p["nome"] == nome)

# =====================================================
# 🎉 SIDEBAR — INFO DO EVENTO
# =====================================================
contexto = get_contexto_base(raw=True)
confirmados = get_confirmacoes()

with st.sidebar:
    st.markdown("### 🧍‍♂️ Confirmados")
    if confirmados:
        for nome in confirmados:
            st.markdown(f"- ✅ **{nome}**")
    else:
        st.markdown("_Ainda ninguém confirmou 😅_")


# =====================================================
# 👋 SAUDAÇÃO
# =====================================================
hora = datetime.now().hour
saud = "Bom dia" if hora < 12 else "Boa tarde" if hora < 20 else "Boa noite"
st.success(f"{saud}, {nome}! 👋 Bem-vindo! E sou o teu assistente virtual da festa 🎉")



# =====================================================
# 🧠 MOTOR DE RESPOSTA
# =====================================================
def gerar_resposta(pergunta: str, perfil: dict):
    pergunta_l = normalizar(pergunta)
    contexto_base = get_contexto_base(raw=True)
    confirmados = get_confirmacoes()

    # ✅ 1 — Saudação
    if any(p in pergunta_l for p in ["ola", "olá", "bom dia", "boa tarde", "boa noite", "oi", "hey"]) and len(pergunta_l.split()) <= 3:
        return (
            f"Olá, {perfil['nome']}! 👋\n\n"
            "Estamos a organizar os detalhes da festa de passagem de ano 🎆\n"
            "Estou disponível para responder a qualquer questão que tenhas!"
        )

    # ✅ 2 — Confirmação de presença
    if any(p in pergunta_l for p in ["confirmo", "vou", "lá estarei", "sim vou", "confirmar"]):
        guardar_confirmacao(perfil["nome"])
        return f"Boa, {perfil['nome']} 🎉 Já estás na lista! Vê a lista ao lado 👈"

    # ✅ 3 — Perguntas sobre confirmados
    if any(p in pergunta_l for p in ["quem vai", "quem confirmou", "quantos somos", "quantos sao"]):
        return "Vê a lista de confirmados ao lado 👈"

    # ✅ 4 — Perguntas diretas sobre "já vimos quintas" / "outras quintas"
    if any(p in pergunta_l for p in ["ja vimos", "já vimos", "vimos quintas", "outras quintas", "vimos outras", "ja contactamos", "já contactámos"]):
        return (
            "Sim, já contactámos várias quintas! 🏡\n\n"
            "Pergunta-me:\n"
            "• 'Quantas quintas já contactámos?'\n"
            "• 'Que quintas já vimos?'\n"
            "• 'Quintas em que zonas?'\n"
            "• Ou qualquer outra coisa específica 😊"
        )

    # ✅ 5 — Perguntas ESPECÍFICAS sobre quintas → envia para o LLM/SQL
    if any(p in pergunta_l for p in ["que quintas", "quais quintas", "quantas quintas", "quantas vimos", "quantas contactamos", "lista", "opcoes", "opções", "nomes"]):
        resposta_llm = gerar_resposta_llm(
            pergunta=pergunta,
            perfil=perfil,
            contexto_base=contexto_base,
        )
        guardar_mensagem(perfil["nome"], pergunta, resposta_llm, contexto="quintas", perfil=perfil)
        return resposta_llm
    
    # ✅ 6 — Perguntas GENÉRICAS sobre o local/quinta → resposta rápida
    if any(p in pergunta_l for p in ["sitio", "local", "onde", "quinta", "ja ha", "reservado", "fechado", "decidido", "ja temos"]) and not any(p in pergunta_l for p in ["que", "quais", "quantas", "lista"]):
        return (
            "Ainda estamos a ver o local final 🏡\n\n"
            "Já temos o **Monte da Galega** reservado como plano B, mas estamos a contactar outras quintas.\n"
            "Pergunta-me sobre as quintas que já vimos! 😊"
        )

    # ✅ 4 — Perguntas sobre características do local (futuro)
    if "piscina" in pergunta_l:
        return "Ainda não temos quinta fechada, mas já perguntámos quais têm piscina 🏊 Queres saber quais são?"

    if "churrasqueira" in pergunta_l or "grelhados" in pergunta_l:
        return "Ainda não decidimos o local, mas já sabemos quais quintas têm churrasqueira 🔥 Queres que te diga?"

    if "snooker" in pergunta_l:
        return "Ainda estamos a decidir o local, mas já vimos quintas com snooker 🎱 Pergunta-me sobre as opções!"

    if any(p in pergunta_l for p in ["animais", "cao", "cão", "gato"]):
        return "Ainda não fechámos o local, mas posso dizer-te quais quintas aceitam animais 🐶 Queres saber?"

    # ✅ 5 — Perguntas sobre o que já foi feito
    if any(p in pergunta_l for p in ["fizeram", "fizeste", "andaram a fazer", "trabalho", "progresso"]):
        return (
            "Já contactámos várias quintas e temos o **Monte da Galega** reservado como backup 🏡 "
            "Pergunta-me sobre quintas específicas, zonas, preços ou capacidades! 😊"
        )

    # ✅ 6 — Perguntas genéricas (LLM trata do resto)
    resposta_llm = gerar_resposta_llm(
        pergunta=pergunta,
        perfil=perfil,
        contexto_base=contexto_base,
    )

    guardar_mensagem(perfil["nome"], pergunta, resposta_llm, contexto="geral", perfil=perfil)
    return resposta_llm

# =====================================================
# 💬 INTERFACE STREAMLIT (CHAT)
# =====================================================
if "historico" not in st.session_state:
    st.session_state.historico = []

# Mostrar histórico
for msg in st.session_state.historico:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input do utilizador
prompt = st.chat_input("Escreve a tua mensagem…")

if prompt:
    with st.chat_message("user"):
        st.markdown(f"**{nome}:** {prompt}")

    with st.spinner("💭 A pensar..."):
        time.sleep(0.3)
        resposta = gerar_resposta(prompt, perfil)

    with st.chat_message("assistant"):
        st.markdown(f"**Assistente:** {resposta}")

    st.session_state.historico.append({"role": "user", "content": f"**{nome}:** {prompt}"})
    st.session_state.historico.append({"role": "assistant", "content": f"**Assistente:** {resposta}"})