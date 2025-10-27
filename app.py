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
    
    # ✅ Pega contexto da última resposta do assistente (se existir)
    contexto_anterior = ""
    lista_quintas_anterior = []
    
    if "historico" in st.session_state and len(st.session_state.historico) > 0:
        # Pega as últimas mensagens do assistente
        ultimas = [msg for msg in st.session_state.historico[-4:] if msg["role"] == "assistant"]
        if ultimas:
            contexto_anterior = ultimas[-1]["content"].replace("**Assistente:** ", "")
            
            # Extrai lista de quintas se existir (formato: • Nome (Zona))
            import re
            quintas_match = re.findall(r'•\s*([^(]+)\s*\(', contexto_anterior)
            if quintas_match:
                lista_quintas_anterior = [q.strip() for q in quintas_match]
                print(f"📋 Lista anterior: {lista_quintas_anterior}")
    
    # ✅ CONTEXTO: Referências a posições (primeira, segunda, 3ª, etc.)
    referencias_posicao = {
        "primeira": 0, "1a": 0, "1ª": 0,
        "segunda": 1, "2a": 1, "2ª": 1,
        "terceira": 2, "3a": 2, "3ª": 2,
        "quarta": 3, "4a": 3, "4ª": 3,
        "quinta": 4, "5a": 4, "5ª": 4,
        "sexta": 5, "6a": 5, "6ª": 5,
        "setima": 6, "sétima": 6, "7a": 6, "7ª": 6,
        "oitava": 7, "8a": 7, "8ª": 7
    }
    
    # Verifica se há referência a posição + se há lista anterior
    if lista_quintas_anterior:
        for ref, idx in referencias_posicao.items():
            if ref in pergunta_l and idx < len(lista_quintas_anterior):
                quinta_referida = lista_quintas_anterior[idx]
                print(f"🎯 Referência '{ref}' → {quinta_referida}")
                
                # Se pede info específica (link, morada, etc)
                if any(p in pergunta_l for p in ["link", "website", "site", "morada", "endereco", "endereço", "contacto", "email", "telefone"]):
                    # Reformula a pergunta com o nome da quinta
                    if "link" in pergunta_l or "website" in pergunta_l or "site" in pergunta_l:
                        pergunta = f"website da {quinta_referida}"
                    elif "morada" in pergunta_l or "endereco" in pergunta_l:
                        pergunta = f"morada da {quinta_referida}"
                    elif "email" in pergunta_l:
                        pergunta = f"email da {quinta_referida}"
                    elif "telefone" in pergunta_l or "contacto" in pergunta_l:
                        pergunta = f"telefone da {quinta_referida}"
                    else:
                        pergunta = f"informação sobre {quinta_referida}"
                    
                    pergunta_l = normalizar(pergunta)
                    print(f"🔄 Reformulado: '{pergunta}'")
                    break

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

    # ✅ 4 — CONTEXTO: Se mencionou "quintas" antes e agora usa pronomes/referências
    mencoes_contextuais = ["as quintas", "essas quintas", "diz-me", "mostra", "lista", "quais sao", "quais são"]
    if contexto_anterior and any(palavra in contexto_anterior.lower() for palavra in ["quinta", "contactamos", "vimos"]):
        if any(ref in pergunta_l for ref in mencoes_contextuais) or (len(pergunta_l.split()) <= 3 and any(p in pergunta_l for p in ["quais", "quintas", "diz", "mostra"])):
            # Redireciona para query de quintas
            pergunta = "que quintas já contactámos"
            pergunta_l = normalizar(pergunta)

    # ✅ 4 — Perguntas ESPECÍFICAS sobre quintas (por nome) ou informações detalhadas
    # Deteta nomes de quintas na pergunta (palavras começadas com maiúscula ou termos específicos)
    import re
    # Procura por nomes próprios ou padrões tipo "C.R. Nome" ou "Quinta X"
    tem_nome_quinta = (
        re.search(r'[A-Z][a-z]+\s+[A-Z]', pergunta) or  # "Casa Lagoa", "Monte Verde"
        re.search(r'C\.R\.|quinta|casa|monte|herdade', pergunta_l) or
        any(len(palavra) > 3 and palavra[0].isupper() for palavra in pergunta.split())
    )
    
    # Perguntas sobre características específicas de quintas
    if any(p in pergunta_l for p in ["website", "link", "site", "endereco", "endereço", "morada", "contacto", "email", "telefone", "onde e", "onde fica"]) and tem_nome_quinta:
        resposta_llm = gerar_resposta_llm(
            pergunta=pergunta,
            perfil=perfil,
            contexto_base=contexto_base,
            contexto_conversa=contexto_anterior
        )
        guardar_mensagem(perfil["nome"], pergunta, resposta_llm, contexto="quintas", perfil=perfil)
        return resposta_llm

    # ✅ 5 — Perguntas sobre ZONAS, listas de quintas, ou queries SQL
    if any(p in pergunta_l for p in [
        "que quintas", "quais quintas", "quantas quintas", "quantas vimos", 
        "quantas contactamos", "lista", "opcoes", "opções", "nomes", 
        "em ", "zona", "quais", "mais perto", "proxima", "próxima",
        "responderam", "resposta", "numero de pessoas", "número de pessoas",
        "capacidade", "pessoas", "tem capacidade", "quantas tem",
        "ja vimos", "vimos", "contactamos"
    ]):
        resposta_llm = gerar_resposta_llm(
            pergunta=pergunta,
            perfil=perfil,
            contexto_base=contexto_base,
            contexto_conversa=contexto_anterior  # ← PASSA O CONTEXTO
        )
        guardar_mensagem(perfil["nome"], pergunta, resposta_llm, contexto="quintas", perfil=perfil)
        return resposta_llm
    
    # ✅ 6 — Perguntas diretas sobre "já vimos quintas" / "outras quintas" (fallback)
    if any(p in pergunta_l for p in ["outras quintas", "vimos outras"]):
        return (
            "Sim, já contactámos várias quintas! 🏡\n\n"
            "Pergunta-me:\n"
            "• 'Quantas quintas já contactámos?'\n"
            "• 'Que quintas já vimos?'\n"
            "• 'Quintas em que zonas?'\n"
            "• Ou qualquer outra coisa específica 😊"
        )
    
    # ✅ 7 — Perguntas GENÉRICAS sobre o local/quinta → resposta rápida
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