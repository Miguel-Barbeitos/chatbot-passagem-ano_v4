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
    identificar_intencao,
    procurar_resposta_semelhante,
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
st.set_page_config(page_title="🎉 Chat da Festa 2025/2026", page_icon="🎆")
st.title("🎆 Assistente da Passagem de Ano 🥳")

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
# 👋 SAUDAÇÃO
# =====================================================
hora = datetime.now().hour
saud = "Bom dia" if hora < 12 else "Boa tarde" if hora < 20 else "Boa noite"
st.success(f"{saud}, {nome}! 👋 Bem-vindo! E sou o teu assistente virtual da festa 🎉")

# =====================================================
# 🎉 LISTA DE CONFIRMADOS (Sidebar)
# =====================================================
with st.sidebar:
    st.header("🎉 Confirmados")
    confirmados = get_confirmacoes()
    if confirmados:
        for pessoa in confirmados:
            st.write(f"✅ {pessoa}")
    else:
        st.write("Ainda ninguém confirmou 😅")

# =====================================================
# 🧠 MOTOR DE RESPOSTA
# =====================================================
def gerar_resposta(pergunta: str, perfil: dict):
    pergunta_l = normalizar(pergunta)
    intencao = identificar_intencao(pergunta_l)
    contexto_base = get_contexto_base()

    # ✅ 1 — Se o utilizador confirmar presença
    if any(p in pergunta_l for p in ["confirmo", "vou", "lá estarei", "sim vou", "confirmar"]):
        guardar_confirmacao(perfil["nome"])
        confirmados = get_confirmacoes()  # 🔄 Atualiza lista logo após guardar
        resposta = f"Boa! 🎉 Fico feliz por saber que vais, {perfil['nome']}. Já estás na lista!"
        guardar_mensagem(perfil["nome"], pergunta, resposta, contexto="confirmacoes", perfil=perfil)
        return resposta

    # ✅ 2 — Perguntas sobre confirmações
    confirmados = get_confirmacoes()  # 🔄 Garante que lê sempre do Qdrant atualizado
    if any(p in pergunta_l for p in ["quem vai", "quem confirmou", "vai à festa", "vai a festa", "quantos somos", "quantos sao"]):
        if confirmados:
            lista = ", ".join(confirmados)
            num = len(confirmados)
            resposta = f"Até agora confirmaram: {lista} 🎉 (Somos {num})"
        else:
            resposta = f"Ainda ninguém confirmou oficialmente 😅 E tu, {perfil['nome']}, já confirmaste?"
        guardar_mensagem(perfil["nome"], pergunta, resposta, contexto="confirmacoes", perfil=perfil)
        return resposta

    # ✅ 3 — Procura em Qdrant / regras
    resposta_memoria = procurar_resposta_semelhante(pergunta_l, intencao, limite_conf=0.6)
    if resposta_memoria and not USE_GROQ_ALWAYS:
        guardar_mensagem(perfil["nome"], pergunta, resposta_memoria, contexto=intencao, perfil=perfil)
        return resposta_memoria

    # ✅ 4 — Caso não encontre, usa o LLM (Groq)
    confirmados = get_confirmacoes()  # 🧩 Atualiza mais uma vez antes de enviar ao LLM
    resposta_llm = gerar_resposta_llm(
        pergunta=pergunta,
        perfil=perfil,
        confirmados=confirmados,
        contexto_base=contexto_base,
    )
    guardar_mensagem(perfil["nome"], pergunta, resposta_llm, contexto=intencao, perfil=perfil)
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
