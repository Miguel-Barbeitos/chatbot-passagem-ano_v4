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
    get_contexto_base,
)
from llm_groq import gerar_resposta_llm

# Novos imports
from modules.confirmacoes import (
    confirmar_pessoa,
    get_confirmados,
    get_estatisticas,
    detectar_intencao_confirmacao,
    confirmar_familia_completa
)
from modules.perfis_manager import buscar_perfil, listar_familia 

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
# 📂 DADOS BASE - NOVO SISTEMA (com fallback)
# =====================================================
try:
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    
    from modules.perfis_manager import listar_todos_perfis, buscar_perfil
    
    print("🔍 A carregar perfis do Qdrant...")
    perfis_lista = listar_todos_perfis()
    
    print(f"📦 Resultado: {len(perfis_lista)} perfis")
    
    if not perfis_lista or len(perfis_lista) == 0:
        # Fallback: lê do JSON diretamente
        st.warning("⚠️ Qdrant vazio. A ler do JSON como fallback...")
        import json
        json_path = os.path.join(os.path.dirname(__file__), "data", "perfis_base.json")
        
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                perfis_lista = json.load(f)
            st.info(f"✅ {len(perfis_lista)} perfis carregados do JSON")
        else:
            st.error(f"❌ Ficheiro não encontrado: {json_path}")
            st.stop()
    else:
        st.success(f"✅ {len(perfis_lista)} perfis carregados do Qdrant")
    
    # Cria lista de nomes para o selectbox
    nomes = sorted([p["nome"] for p in perfis_lista])
    
except Exception as e:
    st.error(f"⚠️ Erro ao carregar perfis: {e}")
    import traceback
    st.code(traceback.format_exc())
    
    # Tenta fallback
    try:
        st.warning("Tentando fallback para JSON...")
        import json
        json_path = os.path.join(os.path.dirname(__file__), "data", "perfis_base.json")
        with open(json_path, "r", encoding="utf-8") as f:
            perfis_lista = json.load(f)
        nomes = sorted([p["nome"] for p in perfis_lista])
        st.info(f"✅ {len(perfis_lista)} perfis do JSON")
    except Exception as e2:
        st.error(f"❌ Fallback também falhou: {e2}")
        st.stop()

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

# Busca perfil completo do Qdrant (ou fallback para lista)
try:
    perfil_completo = buscar_perfil(nome)
    if not perfil_completo:
        # Fallback: busca na lista carregada
        perfil_completo = next((p for p in perfis_lista if p["nome"] == nome), None)
    
    if not perfil_completo:
        st.error(f"⚠️ Perfil de '{nome}' não encontrado!")
        st.stop()
except Exception as e:
    st.error(f"⚠️ Erro ao buscar perfil: {e}")
    st.stop()

# =====================================================
# 🎉 SIDEBAR — INFO DO EVENTO
# =====================================================
contexto = get_contexto_base(raw=True)

# Lê confirmados do novo sistema
try:
    confirmados = get_confirmados()
    stats = get_estatisticas()
except Exception as e:
    print(f"⚠️ Erro ao ler confirmações: {e}")
    confirmados = []
    stats = {"total_confirmados": 0, "familias_completas": 0}

with st.sidebar:
    st.markdown("### 🧍‍♂️ Confirmados")
    if confirmados:
        st.markdown(f"**Total: {stats['total_confirmados']}** | Famílias: {stats['familias_completas']}")
        for nome_confirmado in confirmados:
            st.markdown(f"- ✅ **{nome_confirmado}**")
    else:
        st.markdown("_Ainda ninguém confirmou 😅_")


# =====================================================
# 👋 SAUDAÇÃO PERSONALIZADA
# =====================================================
# Personalidade
personalidade = perfil_completo.get("personalidade", {})
humor = personalidade.get("humor", 5)
emojis = personalidade.get("emojis", 5)
formalidade = personalidade.get("formalidade", 5)
detalhismo = personalidade.get("detalhismo", 5)

hora = datetime.now().hour
saud = "Bom dia" if hora < 12 else "Boa tarde" if hora < 20 else "Boa noite"

# Escolhe saudação baseada em humor + formalidade
saudacoes = {
    "humor_alto_informal": [
        f"{saud}, {nome}! 👋 Pronto para organizar a festa do século? 🎉🎆",
        f"Olá {nome}! 🎉 Vamos tornar esta passagem de ano épica? 🚀",
        f"E aí {nome}! 😄 Bora lá organizar a melhor festa de sempre? 🎊"
    ],
    "humor_alto_formal": [
        f"{saud}, {nome}! 👋 Espero poder ajudar na organização desta festa especial 🎉",
        f"{saud}! Que bom ter-te aqui, {nome}. Vamos trabalhar juntos nesta festa? 🎆"
    ],
    "humor_medio_informal": [
        f"{saud}, {nome}! 👋 Bem-vindo! Sou o teu assistente da festa 🎉",
        f"Olá {nome}! Estou aqui para ajudar com a organização 😊",
        f"Hey {nome}! 👋 Vamos organizar esta festa juntos?"
    ],
    "humor_medio_formal": [
        f"{saud}, {nome}. Bem-vindo ao assistente da festa 🎉",
        f"{saud}! Estou disponível para ajudar, {nome}."
    ],
    "humor_baixo_informal": [
        f"{saud}, {nome}. Estou aqui para ajudar.",
        f"Olá {nome}. Como posso ajudar com a festa?"
    ],
    "humor_baixo_formal": [
        f"{saud}, {nome}. Estou aqui para ajudar com a organização da festa.",
        f"{saud}. Sou o assistente da organização da festa, {nome}."
    ]
}

# Seleciona categoria de saudação
if humor >= 7:
    categoria = "humor_alto_formal" if formalidade >= 6 else "humor_alto_informal"
elif humor >= 4:
    categoria = "humor_medio_formal" if formalidade >= 6 else "humor_medio_informal"
else:
    categoria = "humor_baixo_formal" if formalidade >= 6 else "humor_baixo_informal"

msg_saudacao = random.choice(saudacoes[categoria])

# Adiciona contexto extra se detalhismo alto
if detalhismo >= 7:
    msg_saudacao += "\n\nPodes perguntar-me sobre quintas, confirmações, detalhes da festa ou o que precisares!"

# Remove emojis se preferência baixa
if emojis < 3:
    import re
    msg_saudacao = re.sub(r'[😀-🙏🌀-🗿🚀-🛿👋🎉🎆🎊]', '', msg_saudacao).strip()
elif emojis < 5:
    # Mantém poucos emojis
    msg_saudacao = msg_saudacao.replace("🎆", "").replace("🎊", "").replace("🚀", "")

st.success(msg_saudacao)


# =====================================================
# 🧠 MOTOR DE RESPOSTA
# =====================================================
def gerar_resposta(pergunta: str, perfil_completo: dict):
    pergunta_l = normalizar(pergunta)
    # =====================================================

    mapa_numeros = {
        "1": 0, "primeira": 0, "1a": 0, "1ª": 0, "primeiro": 0,
        "2": 1, "segunda": 1, "2a": 1, "2ª": 1, "segundo": 1,
        "3": 2, "terceira": 2, "3a": 2, "3ª": 2, "terceiro": 2,
        "4": 3, "quarta": 3, "4a": 3, "4ª": 3, "quarto": 3,
        "5": 4, "quinta": 4, "5a": 4, "5ª": 4, "quinto": 4,
        "6": 5, "sexta": 5, "6a": 5, "6ª": 5, "sexto": 5,
        "7": 6, "setima": 6, "sétima": 6, "7a": 6, "7ª": 6, "setimo": 6,
        "8": 7, "oitava": 7, "8a": 7, "8ª": 7, "oitavo": 7,
        "9": 8, "nona": 8, "9a": 8, "9ª": 8, "nono": 8,
        "10": 9, "decima": 9, "décima": 9, "10a": 9, "10ª": 9, "decimo": 9,
    }
    
    if "ultima_lista_quintas" in st.session_state and st.session_state.ultima_lista_quintas:
        import re
        for ref, idx in mapa_numeros.items():
            padroes = [
                rf'\be\s+da\s+{re.escape(ref)}\b',
                rf'\bda\s+{re.escape(ref)}\b',
                rf'^{re.escape(ref)}$',
            ]
            
            if any(re.search(p, pergunta_l, re.IGNORECASE) for p in padroes):
                if idx < len(st.session_state.ultima_lista_quintas):
                    quinta_nome = st.session_state.ultima_lista_quintas[idx]
                    
                    if "website" in pergunta_l or "site" in pergunta_l:
                        pergunta = f"website da {quinta_nome}"
                    elif "morada" in pergunta_l:
                        pergunta = f"morada da {quinta_nome}"
                    elif "email" in pergunta_l:
                        pergunta = f"email da {quinta_nome}"
                    else:
                        pergunta = f"website da {quinta_nome}"
                    
                    pergunta_l = normalizar(pergunta)


    mapa_numeros = {
        "1": 0, "primeira": 0, "1a": 0, "1ª": 0, "primeiro": 0,
        "2": 1, "segunda": 1, "2a": 1, "2ª": 1, "segundo": 1,
        "3": 2, "terceira": 2, "3a": 2, "3ª": 2, "terceiro": 2,
        "4": 3, "quarta": 3, "4a": 3, "4ª": 3, "quarto": 3,
        "5": 4, "quinta": 4, "5a": 4, "5ª": 4, "quinto": 4,
        "6": 5, "sexta": 5, "6a": 5, "6ª": 5, "sexto": 5,
        "7": 6, "setima": 6, "sétima": 6, "7a": 6, "7ª": 6, "setimo": 6,
        "8": 7, "oitava": 7, "8a": 7, "8ª": 7, "oitavo": 7,
        "9": 8, "nona": 8, "9a": 8, "9ª": 8, "nono": 8,
        "10": 9, "decima": 9, "décima": 9, "10a": 9, "10ª": 9, "decimo": 9,
    }
    
    if "ultima_lista_quintas" in st.session_state and st.session_state.ultima_lista_quintas:
        import re
        for ref, idx in mapa_numeros.items():
            padroes = [
                rf'\be\s+da\s+{re.escape(ref)}\b',
                rf'\bda\s+{re.escape(ref)}\b',
                rf'^{re.escape(ref)}$',
            ]
            
            if any(re.search(p, pergunta_l, re.IGNORECASE) for p in padroes):
                if idx < len(st.session_state.ultima_lista_quintas):
                    quinta_nome = st.session_state.ultima_lista_quintas[idx]
                    
                    if "website" in pergunta_l or "site" in pergunta_l:
                        pergunta = f"website da {quinta_nome}"
                    elif "morada" in pergunta_l:
                        pergunta = f"morada da {quinta_nome}"
                    elif "email" in pergunta_l:
                        pergunta = f"email da {quinta_nome}"
                    else:
                        pergunta = f"website da {quinta_nome}"
                    
                    pergunta_l = normalizar(pergunta)


    mapa_numeros = {
        "1": 0, "primeira": 0, "1a": 0, "1ª": 0, "primeiro": 0,
        "2": 1, "segunda": 1, "2a": 1, "2ª": 1, "segundo": 1,
        "3": 2, "terceira": 2, "3a": 2, "3ª": 2, "terceiro": 2,
        "4": 3, "quarta": 3, "4a": 3, "4ª": 3, "quarto": 3,
        "5": 4, "quinta": 4, "5a": 4, "5ª": 4, "quinto": 4,
        "6": 5, "sexta": 5, "6a": 5, "6ª": 5, "sexto": 5,
        "7": 6, "setima": 6, "sétima": 6, "7a": 6, "7ª": 6, "setimo": 6,
        "8": 7, "oitava": 7, "8a": 7, "8ª": 7, "oitavo": 7,
        "9": 8, "nona": 8, "9a": 8, "9ª": 8, "nono": 8,
        "10": 9, "decima": 9, "décima": 9, "10a": 9, "10ª": 9, "decimo": 9,
    }
    
    if "ultima_lista_quintas" in st.session_state and st.session_state.ultima_lista_quintas:
        import re
        for ref, idx in mapa_numeros.items():
            padroes = [
                rf'\be\s+da\s+{re.escape(ref)}\b',
                rf'\bda\s+{re.escape(ref)}\b',
                rf'^{re.escape(ref)}$',
            ]
            
            if any(re.search(p, pergunta_l, re.IGNORECASE) for p in padroes):
                if idx < len(st.session_state.ultima_lista_quintas):
                    quinta_nome = st.session_state.ultima_lista_quintas[idx]
                    
                    if "website" in pergunta_l or "site" in pergunta_l:
                        pergunta = f"website da {quinta_nome}"
                    elif "morada" in pergunta_l:
                        pergunta = f"morada da {quinta_nome}"
                    elif "email" in pergunta_l:
                        pergunta = f"email da {quinta_nome}"
                    else:
                        pergunta = f"website da {quinta_nome}"
                    
                    pergunta_l = normalizar(pergunta)


    mapa_numeros = {
        "1": 0, "primeira": 0, "1a": 0, "1ª": 0, "primeiro": 0,
        "2": 1, "segunda": 1, "2a": 1, "2ª": 1, "segundo": 1,
        "3": 2, "terceira": 2, "3a": 2, "3ª": 2, "terceiro": 2,
        "4": 3, "quarta": 3, "4a": 3, "4ª": 3, "quarto": 3,
        "5": 4, "quinta": 4, "5a": 4, "5ª": 4, "quinto": 4,
        "6": 5, "sexta": 5, "6a": 5, "6ª": 5, "sexto": 5,
        "7": 6, "setima": 6, "sétima": 6, "7a": 6, "7ª": 6, "setimo": 6,
        "8": 7, "oitava": 7, "8a": 7, "8ª": 7, "oitavo": 7,
        "9": 8, "nona": 8, "9a": 8, "9ª": 8, "nono": 8,
        "10": 9, "decima": 9, "décima": 9, "10a": 9, "10ª": 9, "decimo": 9,
    }
    
    if "ultima_lista_quintas" in st.session_state and st.session_state.ultima_lista_quintas:
        import re
        for ref, idx in mapa_numeros.items():
            padroes = [
                rf'\be\s+da\s+{re.escape(ref)}\b',
                rf'\bda\s+{re.escape(ref)}\b',
                rf'^{re.escape(ref)}$',
            ]
            
            if any(re.search(p, pergunta_l, re.IGNORECASE) for p in padroes):
                if idx < len(st.session_state.ultima_lista_quintas):
                    quinta_nome = st.session_state.ultima_lista_quintas[idx]
                    
                    if "website" in pergunta_l or "site" in pergunta_l:
                        pergunta = f"website da {quinta_nome}"
                    elif "morada" in pergunta_l:
                        pergunta = f"morada da {quinta_nome}"
                    elif "email" in pergunta_l:
                        pergunta = f"email da {quinta_nome}"
                    else:
                        pergunta = f"website da {quinta_nome}"
                    
                    pergunta_l = normalizar(pergunta)


    contexto_base = get_contexto_base(raw=True)
    


    lista_quintas_anterior = []
    ultima_quinta_mencionada = None
    
    if "historico" in st.session_state and len(st.session_state.historico) > 0:
        # Pega as últimas mensagens do assistente
        ultimas = [msg for msg in st.session_state.historico[-4:] if msg["role"] == "assistant"]
        if ultimas:
            contexto_anterior = ultimas[-1]["content"].replace("**Assistente:** ", "")
            
            # Extrai lista de quintas se existir (formato: • Nome (Zona))
            
            quintas_match = re.findall(r'•\s*([^(]+)\s*\(', contexto_anterior)
            if quintas_match:
                lista_quintas_anterior = [q.strip() for q in quintas_match]
                print(f"📋 Lista anterior: {lista_quintas_anterior}")
            
            # Extrai última quinta mencionada (formato: 📍 Nome (Zona))
            quinta_match = re.search(r'📍\s*\*?\*?([^(]+)\*?\*?\s*\(([^)]+)\)', contexto_anterior)
            if quinta_match:
                ultima_quinta_mencionada = {
                    "nome": quinta_match.group(1).strip(),
                    "zona": quinta_match.group(2).strip()
                }
            

    quinta_na_pergunta = re.search(
        r'(C\.R\.|Casa|Monte|Herdade|Quinta)\s+([A-Z][^\?]+?)(?:\s+é|\s+fica|\s+tem|\?|$)', 
        pergunta, 
        re.IGNORECASE
    )
    if quinta_na_pergunta:
        nome_detectado = quinta_na_pergunta.group(0).strip().rstrip('?').strip()
        # Remove palavras após "é", "fica", etc
        nome_detectado = re.sub(r'\s+(é|fica|tem|onde|como|quando).*$', '', nome_detectado, flags=re.IGNORECASE).strip()
        st.session_state.ultima_quinta_mencionada = nome_detectado
        print(f"🔍 Quinta detectada na pergunta: {nome_detectado}")
    


    mapa_numeros = {
        "1": 0, "primeira": 0, "1a": 0, "1ª": 0, "primeiro": 0,
        "2": 1, "segunda": 1, "2a": 1, "2ª": 1, "segundo": 1,
        "3": 2, "terceira": 2, "3a": 2, "3ª": 2, "terceiro": 2,
        "4": 3, "quarta": 3, "4a": 3, "4ª": 3, "quarto": 3,
        "5": 4, "quinta": 4, "5a": 4, "5ª": 4, "quinto": 4,
        "6": 5, "sexta": 5, "6a": 5, "6ª": 5, "sexto": 5,
        "7": 6, "setima": 6, "sétima": 6, "7a": 6, "7ª": 6, "setimo": 6,
        "8": 7, "oitava": 7, "8a": 7, "8ª": 7, "oitavo": 7,
        "9": 8, "nona": 8, "9a": 8, "9ª": 8, "nono": 8,
        "10": 9, "decima": 9, "décima": 9, "10a": 9, "10ª": 9, "decimo": 9,
    }
    
    if "ultima_lista_quintas" in st.session_state and st.session_state.ultima_lista_quintas:
        import re
        for ref, idx in mapa_numeros.items():
            padroes = [
                rf'\be\s+da\s+{re.escape(ref)}\b',
                rf'\bda\s+{re.escape(ref)}\b',
                rf'^{re.escape(ref)}$',
            ]
            
            if any(re.search(p, pergunta_l, re.IGNORECASE) for p in padroes):
                if idx < len(st.session_state.ultima_lista_quintas):
                    quinta_nome = st.session_state.ultima_lista_quintas[idx]
                    
                    if "website" in pergunta_l or "site" in pergunta_l:
                        pergunta = f"website da {quinta_nome}"
                    elif "morada" in pergunta_l:
                        pergunta = f"morada da {quinta_nome}"
                    elif "email" in pergunta_l:
                        pergunta = f"email da {quinta_nome}"
                    else:
                        pergunta = f"website da {quinta_nome}"
                    
                    pergunta_l = normalizar(pergunta)


    mapa_numeros = {
        "1": 0, "primeira": 0, "1a": 0, "1ª": 0, "primeiro": 0,
        "2": 1, "segunda": 1, "2a": 1, "2ª": 1, "segundo": 1,
        "3": 2, "terceira": 2, "3a": 2, "3ª": 2, "terceiro": 2,
        "4": 3, "quarta": 3, "4a": 3, "4ª": 3, "quarto": 3,
        "5": 4, "quinta": 4, "5a": 4, "5ª": 4, "quinto": 4,
        "6": 5, "sexta": 5, "6a": 5, "6ª": 5, "sexto": 5,
        "7": 6, "setima": 6, "sétima": 6, "7a": 6, "7ª": 6, "setimo": 6,
        "8": 7, "oitava": 7, "8a": 7, "8ª": 7, "oitavo": 7,
        "9": 8, "nona": 8, "9a": 8, "9ª": 8, "nono": 8,
        "10": 9, "decima": 9, "décima": 9, "10a": 9, "10ª": 9, "decimo": 9,
    }
    
    if "ultima_lista_quintas" in st.session_state and st.session_state.ultima_lista_quintas:
        import re
        for ref, idx in mapa_numeros.items():
            padroes = [
                rf'\be\s+da\s+{re.escape(ref)}\b',
                rf'\bda\s+{re.escape(ref)}\b',
                rf'^{re.escape(ref)}$',
            ]
            
            if any(re.search(p, pergunta_l, re.IGNORECASE) for p in padroes):
                if idx < len(st.session_state.ultima_lista_quintas):
                    quinta_nome = st.session_state.ultima_lista_quintas[idx]
                    
                    if "website" in pergunta_l or "site" in pergunta_l:
                        pergunta = f"website da {quinta_nome}"
                    elif "morada" in pergunta_l:
                        pergunta = f"morada da {quinta_nome}"
                    elif "email" in pergunta_l:
                        pergunta = f"email da {quinta_nome}"
                    else:
                        pergunta = f"website da {quinta_nome}"
                    
                    pergunta_l = normalizar(pergunta)


    mapa_numeros = {
        "1": 0, "primeira": 0, "1a": 0, "1ª": 0, "primeiro": 0,
        "2": 1, "segunda": 1, "2a": 1, "2ª": 1, "segundo": 1,
        "3": 2, "terceira": 2, "3a": 2, "3ª": 2, "terceiro": 2,
        "4": 3, "quarta": 3, "4a": 3, "4ª": 3, "quarto": 3,
        "5": 4, "quinta": 4, "5a": 4, "5ª": 4, "quinto": 4,
        "6": 5, "sexta": 5, "6a": 5, "6ª": 5, "sexto": 5,
        "7": 6, "setima": 6, "sétima": 6, "7a": 6, "7ª": 6, "setimo": 6,
        "8": 7, "oitava": 7, "8a": 7, "8ª": 7, "oitavo": 7,
        "9": 8, "nona": 8, "9a": 8, "9ª": 8, "nono": 8,
        "10": 9, "decima": 9, "décima": 9, "10a": 9, "10ª": 9, "decimo": 9,
    }
    
    if "ultima_lista_quintas" in st.session_state and st.session_state.ultima_lista_quintas:
        import re
        for ref, idx in mapa_numeros.items():
            padroes = [
                rf'\be\s+da\s+{re.escape(ref)}\b',
                rf'\bda\s+{re.escape(ref)}\b',
                rf'^{re.escape(ref)}$',
            ]
            
            if any(re.search(p, pergunta_l, re.IGNORECASE) for p in padroes):
                if idx < len(st.session_state.ultima_lista_quintas):
                    quinta_nome = st.session_state.ultima_lista_quintas[idx]
                    
                    if "website" in pergunta_l or "site" in pergunta_l:
                        pergunta = f"website da {quinta_nome}"
                    elif "morada" in pergunta_l:
                        pergunta = f"morada da {quinta_nome}"
                    elif "email" in pergunta_l:
                        pergunta = f"email da {quinta_nome}"
                    else:
                        pergunta = f"website da {quinta_nome}"
                    
                    pergunta_l = normalizar(pergunta)


    mapa_numeros = {
        "1": 0, "primeira": 0, "1a": 0, "1ª": 0, "primeiro": 0,
        "2": 1, "segunda": 1, "2a": 1, "2ª": 1, "segundo": 1,
        "3": 2, "terceira": 2, "3a": 2, "3ª": 2, "terceiro": 2,
        "4": 3, "quarta": 3, "4a": 3, "4ª": 3, "quarto": 3,
        "5": 4, "quinta": 4, "5a": 4, "5ª": 4, "quinto": 4,
        "6": 5, "sexta": 5, "6a": 5, "6ª": 5, "sexto": 5,
        "7": 6, "setima": 6, "sétima": 6, "7a": 6, "7ª": 6, "setimo": 6,
        "8": 7, "oitava": 7, "8a": 7, "8ª": 7, "oitavo": 7,
        "9": 8, "nona": 8, "9a": 8, "9ª": 8, "nono": 8,
        "10": 9, "decima": 9, "décima": 9, "10a": 9, "10ª": 9, "decimo": 9,
    }
    
    if "ultima_lista_quintas" in st.session_state and st.session_state.ultima_lista_quintas:
        import re
        for ref, idx in mapa_numeros.items():
            padroes = [
                rf'\be\s+da\s+{re.escape(ref)}\b',
                rf'\bda\s+{re.escape(ref)}\b',
                rf'^{re.escape(ref)}$',
            ]
            
            if any(re.search(p, pergunta_l, re.IGNORECASE) for p in padroes):
                if idx < len(st.session_state.ultima_lista_quintas):
                    quinta_nome = st.session_state.ultima_lista_quintas[idx]
                    
                    if "website" in pergunta_l or "site" in pergunta_l:
                        pergunta = f"website da {quinta_nome}"
                    elif "morada" in pergunta_l:
                        pergunta = f"morada da {quinta_nome}"
                    elif "email" in pergunta_l:
                        pergunta = f"email da {quinta_nome}"
                    else:
                        pergunta = f"website da {quinta_nome}"
                    
                    pergunta_l = normalizar(pergunta)


            print(f"🔄 Reformulado com contexto: '{pergunta}'")
    

    mapa_numeros = {
        "1": 0, "primeira": 0, "1a": 0, "1ª": 0, "primeiro": 0,
        "2": 1, "segunda": 1, "2a": 1, "2ª": 1, "segundo": 1,
        "3": 2, "terceira": 2, "3a": 2, "3ª": 2, "terceiro": 2,
        "4": 3, "quarta": 3, "4a": 3, "4ª": 3, "quarto": 3,
        "5": 4, "quinta": 4, "5a": 4, "5ª": 4, "quinto": 4,
        "6": 5, "sexta": 5, "6a": 5, "6ª": 5, "sexto": 5,
        "7": 6, "setima": 6, "sétima": 6, "7a": 6, "7ª": 6, "setimo": 6,
        "8": 7, "oitava": 7, "8a": 7, "8ª": 7, "oitavo": 7,
        "9": 8, "nona": 8, "9a": 8, "9ª": 8, "nono": 8,
        "10": 9, "decima": 9, "décima": 9, "10a": 9, "10ª": 9, "decimo": 9,
    }
    
    if "ultima_lista_quintas" in st.session_state and st.session_state.ultima_lista_quintas:
        import re
        for ref, idx in mapa_numeros.items():
            padroes = [
                rf'\be\s+da\s+{re.escape(ref)}\b',
                rf'\bda\s+{re.escape(ref)}\b',
                rf'^{re.escape(ref)}$',
            ]
            
            if any(re.search(p, pergunta_l, re.IGNORECASE) for p in padroes):
                if idx < len(st.session_state.ultima_lista_quintas):
                    quinta_nome = st.session_state.ultima_lista_quintas[idx]
                    
                    if "website" in pergunta_l or "site" in pergunta_l:
                        pergunta = f"website da {quinta_nome}"
                    elif "morada" in pergunta_l:
                        pergunta = f"morada da {quinta_nome}"
                    elif "email" in pergunta_l:
                        pergunta = f"email da {quinta_nome}"
                    else:
                        pergunta = f"website da {quinta_nome}"
                    
                    pergunta_l = normalizar(pergunta)


    mapa_numeros = {
        "1": 0, "primeira": 0, "1a": 0, "1ª": 0, "primeiro": 0,
        "2": 1, "segunda": 1, "2a": 1, "2ª": 1, "segundo": 1,
        "3": 2, "terceira": 2, "3a": 2, "3ª": 2, "terceiro": 2,
        "4": 3, "quarta": 3, "4a": 3, "4ª": 3, "quarto": 3,
        "5": 4, "quinta": 4, "5a": 4, "5ª": 4, "quinto": 4,
        "6": 5, "sexta": 5, "6a": 5, "6ª": 5, "sexto": 5,
        "7": 6, "setima": 6, "sétima": 6, "7a": 6, "7ª": 6, "setimo": 6,
        "8": 7, "oitava": 7, "8a": 7, "8ª": 7, "oitavo": 7,
        "9": 8, "nona": 8, "9a": 8, "9ª": 8, "nono": 8,
        "10": 9, "decima": 9, "décima": 9, "10a": 9, "10ª": 9, "decimo": 9,
    }
    
    if "ultima_lista_quintas" in st.session_state and st.session_state.ultima_lista_quintas:
        import re
        for ref, idx in mapa_numeros.items():
            padroes = [
                rf'\be\s+da\s+{re.escape(ref)}\b',
                rf'\bda\s+{re.escape(ref)}\b',
                rf'^{re.escape(ref)}$',
            ]
            
            if any(re.search(p, pergunta_l, re.IGNORECASE) for p in padroes):
                if idx < len(st.session_state.ultima_lista_quintas):
                    quinta_nome = st.session_state.ultima_lista_quintas[idx]
                    
                    if "website" in pergunta_l or "site" in pergunta_l:
                        pergunta = f"website da {quinta_nome}"
                    elif "morada" in pergunta_l:
                        pergunta = f"morada da {quinta_nome}"
                    elif "email" in pergunta_l:
                        pergunta = f"email da {quinta_nome}"
                    else:
                        pergunta = f"website da {quinta_nome}"
                    
                    pergunta_l = normalizar(pergunta)


    mapa_numeros = {
        "1": 0, "primeira": 0, "1a": 0, "1ª": 0, "primeiro": 0,
        "2": 1, "segunda": 1, "2a": 1, "2ª": 1, "segundo": 1,
        "3": 2, "terceira": 2, "3a": 2, "3ª": 2, "terceiro": 2,
        "4": 3, "quarta": 3, "4a": 3, "4ª": 3, "quarto": 3,
        "5": 4, "quinta": 4, "5a": 4, "5ª": 4, "quinto": 4,
        "6": 5, "sexta": 5, "6a": 5, "6ª": 5, "sexto": 5,
        "7": 6, "setima": 6, "sétima": 6, "7a": 6, "7ª": 6, "setimo": 6,
        "8": 7, "oitava": 7, "8a": 7, "8ª": 7, "oitavo": 7,
        "9": 8, "nona": 8, "9a": 8, "9ª": 8, "nono": 8,
        "10": 9, "decima": 9, "décima": 9, "10a": 9, "10ª": 9, "decimo": 9,
    }
    
    if "ultima_lista_quintas" in st.session_state and st.session_state.ultima_lista_quintas:
        import re
        for ref, idx in mapa_numeros.items():
            padroes = [
                rf'\be\s+da\s+{re.escape(ref)}\b',
                rf'\bda\s+{re.escape(ref)}\b',
                rf'^{re.escape(ref)}$',
            ]
            
            if any(re.search(p, pergunta_l, re.IGNORECASE) for p in padroes):
                if idx < len(st.session_state.ultima_lista_quintas):
                    quinta_nome = st.session_state.ultima_lista_quintas[idx]
                    
                    if "website" in pergunta_l or "site" in pergunta_l:
                        pergunta = f"website da {quinta_nome}"
                    elif "morada" in pergunta_l:
                        pergunta = f"morada da {quinta_nome}"
                    elif "email" in pergunta_l:
                        pergunta = f"email da {quinta_nome}"
                    else:
                        pergunta = f"website da {quinta_nome}"
                    
                    pergunta_l = normalizar(pergunta)


    mapa_numeros = {
        "1": 0, "primeira": 0, "1a": 0, "1ª": 0, "primeiro": 0,
        "2": 1, "segunda": 1, "2a": 1, "2ª": 1, "segundo": 1,
        "3": 2, "terceira": 2, "3a": 2, "3ª": 2, "terceiro": 2,
        "4": 3, "quarta": 3, "4a": 3, "4ª": 3, "quarto": 3,
        "5": 4, "quinta": 4, "5a": 4, "5ª": 4, "quinto": 4,
        "6": 5, "sexta": 5, "6a": 5, "6ª": 5, "sexto": 5,
        "7": 6, "setima": 6, "sétima": 6, "7a": 6, "7ª": 6, "setimo": 6,
        "8": 7, "oitava": 7, "8a": 7, "8ª": 7, "oitavo": 7,
        "9": 8, "nona": 8, "9a": 8, "9ª": 8, "nono": 8,
        "10": 9, "decima": 9, "décima": 9, "10a": 9, "10ª": 9, "decimo": 9,
    }
    
    if "ultima_lista_quintas" in st.session_state and st.session_state.ultima_lista_quintas:
        import re
        for ref, idx in mapa_numeros.items():
            padroes = [
                rf'\be\s+da\s+{re.escape(ref)}\b',
                rf'\bda\s+{re.escape(ref)}\b',
                rf'^{re.escape(ref)}$',
            ]
            
            if any(re.search(p, pergunta_l, re.IGNORECASE) for p in padroes):
                if idx < len(st.session_state.ultima_lista_quintas):
                    quinta_nome = st.session_state.ultima_lista_quintas[idx]
                    
                    if "website" in pergunta_l or "site" in pergunta_l:
                        pergunta = f"website da {quinta_nome}"
                    elif "morada" in pergunta_l:
                        pergunta = f"morada da {quinta_nome}"
                    elif "email" in pergunta_l:
                        pergunta = f"email da {quinta_nome}"
                    else:
                        pergunta = f"website da {quinta_nome}"
                    
                    pergunta_l = normalizar(pergunta)


            print(f"🔄 Contexto de continuação: '{pergunta}'")
    

    mapa_numeros = {
        "1": 0, "primeira": 0, "1a": 0, "1ª": 0, "primeiro": 0,
        "2": 1, "segunda": 1, "2a": 1, "2ª": 1, "segundo": 1,
        "3": 2, "terceira": 2, "3a": 2, "3ª": 2, "terceiro": 2,
        "4": 3, "quarta": 3, "4a": 3, "4ª": 3, "quarto": 3,
        "5": 4, "quinta": 4, "5a": 4, "5ª": 4, "quinto": 4,
        "6": 5, "sexta": 5, "6a": 5, "6ª": 5, "sexto": 5,
        "7": 6, "setima": 6, "sétima": 6, "7a": 6, "7ª": 6, "setimo": 6,
        "8": 7, "oitava": 7, "8a": 7, "8ª": 7, "oitavo": 7,
        "9": 8, "nona": 8, "9a": 8, "9ª": 8, "nono": 8,
        "10": 9, "decima": 9, "décima": 9, "10a": 9, "10ª": 9, "decimo": 9,
    }
    
    if "ultima_lista_quintas" in st.session_state and st.session_state.ultima_lista_quintas:
        import re
        for ref, idx in mapa_numeros.items():
            padroes = [
                rf'\be\s+da\s+{re.escape(ref)}\b',
                rf'\bda\s+{re.escape(ref)}\b',
                rf'^{re.escape(ref)}$',
            ]
            
            if any(re.search(p, pergunta_l, re.IGNORECASE) for p in padroes):
                if idx < len(st.session_state.ultima_lista_quintas):
                    quinta_nome = st.session_state.ultima_lista_quintas[idx]
                    
                    if "website" in pergunta_l or "site" in pergunta_l:
                        pergunta = f"website da {quinta_nome}"
                    elif "morada" in pergunta_l:
                        pergunta = f"morada da {quinta_nome}"
                    elif "email" in pergunta_l:
                        pergunta = f"email da {quinta_nome}"
                    else:
                        pergunta = f"website da {quinta_nome}"
                    
                    pergunta_l = normalizar(pergunta)


    mapa_numeros = {
        "1": 0, "primeira": 0, "1a": 0, "1ª": 0, "primeiro": 0,
        "2": 1, "segunda": 1, "2a": 1, "2ª": 1, "segundo": 1,
        "3": 2, "terceira": 2, "3a": 2, "3ª": 2, "terceiro": 2,
        "4": 3, "quarta": 3, "4a": 3, "4ª": 3, "quarto": 3,
        "5": 4, "quinta": 4, "5a": 4, "5ª": 4, "quinto": 4,
        "6": 5, "sexta": 5, "6a": 5, "6ª": 5, "sexto": 5,
        "7": 6, "setima": 6, "sétima": 6, "7a": 6, "7ª": 6, "setimo": 6,
        "8": 7, "oitava": 7, "8a": 7, "8ª": 7, "oitavo": 7,
        "9": 8, "nona": 8, "9a": 8, "9ª": 8, "nono": 8,
        "10": 9, "decima": 9, "décima": 9, "10a": 9, "10ª": 9, "decimo": 9,
    }
    
    if "ultima_lista_quintas" in st.session_state and st.session_state.ultima_lista_quintas:
        import re
        for ref, idx in mapa_numeros.items():
            padroes = [
                rf'\be\s+da\s+{re.escape(ref)}\b',
                rf'\bda\s+{re.escape(ref)}\b',
                rf'^{re.escape(ref)}$',
            ]
            
            if any(re.search(p, pergunta_l, re.IGNORECASE) for p in padroes):
                if idx < len(st.session_state.ultima_lista_quintas):
                    quinta_nome = st.session_state.ultima_lista_quintas[idx]
                    
                    if "website" in pergunta_l or "site" in pergunta_l:
                        pergunta = f"website da {quinta_nome}"
                    elif "morada" in pergunta_l:
                        pergunta = f"morada da {quinta_nome}"
                    elif "email" in pergunta_l:
                        pergunta = f"email da {quinta_nome}"
                    else:
                        pergunta = f"website da {quinta_nome}"
                    
                    pergunta_l = normalizar(pergunta)


    mapa_numeros = {
        "1": 0, "primeira": 0, "1a": 0, "1ª": 0, "primeiro": 0,
        "2": 1, "segunda": 1, "2a": 1, "2ª": 1, "segundo": 1,
        "3": 2, "terceira": 2, "3a": 2, "3ª": 2, "terceiro": 2,
        "4": 3, "quarta": 3, "4a": 3, "4ª": 3, "quarto": 3,
        "5": 4, "quinta": 4, "5a": 4, "5ª": 4, "quinto": 4,
        "6": 5, "sexta": 5, "6a": 5, "6ª": 5, "sexto": 5,
        "7": 6, "setima": 6, "sétima": 6, "7a": 6, "7ª": 6, "setimo": 6,
        "8": 7, "oitava": 7, "8a": 7, "8ª": 7, "oitavo": 7,
        "9": 8, "nona": 8, "9a": 8, "9ª": 8, "nono": 8,
        "10": 9, "decima": 9, "décima": 9, "10a": 9, "10ª": 9, "decimo": 9,
    }
    
    if "ultima_lista_quintas" in st.session_state and st.session_state.ultima_lista_quintas:
        import re
        for ref, idx in mapa_numeros.items():
            padroes = [
                rf'\be\s+da\s+{re.escape(ref)}\b',
                rf'\bda\s+{re.escape(ref)}\b',
                rf'^{re.escape(ref)}$',
            ]
            
            if any(re.search(p, pergunta_l, re.IGNORECASE) for p in padroes):
                if idx < len(st.session_state.ultima_lista_quintas):
                    quinta_nome = st.session_state.ultima_lista_quintas[idx]
                    
                    if "website" in pergunta_l or "site" in pergunta_l:
                        pergunta = f"website da {quinta_nome}"
                    elif "morada" in pergunta_l:
                        pergunta = f"morada da {quinta_nome}"
                    elif "email" in pergunta_l:
                        pergunta = f"email da {quinta_nome}"
                    else:
                        pergunta = f"website da {quinta_nome}"
                    
                    pergunta_l = normalizar(pergunta)


    mapa_numeros = {
        "1": 0, "primeira": 0, "1a": 0, "1ª": 0, "primeiro": 0,
        "2": 1, "segunda": 1, "2a": 1, "2ª": 1, "segundo": 1,
        "3": 2, "terceira": 2, "3a": 2, "3ª": 2, "terceiro": 2,
        "4": 3, "quarta": 3, "4a": 3, "4ª": 3, "quarto": 3,
        "5": 4, "quinta": 4, "5a": 4, "5ª": 4, "quinto": 4,
        "6": 5, "sexta": 5, "6a": 5, "6ª": 5, "sexto": 5,
        "7": 6, "setima": 6, "sétima": 6, "7a": 6, "7ª": 6, "setimo": 6,
        "8": 7, "oitava": 7, "8a": 7, "8ª": 7, "oitavo": 7,
        "9": 8, "nona": 8, "9a": 8, "9ª": 8, "nono": 8,
        "10": 9, "decima": 9, "décima": 9, "10a": 9, "10ª": 9, "decimo": 9,
    }
    
    if "ultima_lista_quintas" in st.session_state and st.session_state.ultima_lista_quintas:
        import re
        for ref, idx in mapa_numeros.items():
            padroes = [
                rf'\be\s+da\s+{re.escape(ref)}\b',
                rf'\bda\s+{re.escape(ref)}\b',
                rf'^{re.escape(ref)}$',
            ]
            
            if any(re.search(p, pergunta_l, re.IGNORECASE) for p in padroes):
                if idx < len(st.session_state.ultima_lista_quintas):
                    quinta_nome = st.session_state.ultima_lista_quintas[idx]
                    
                    if "website" in pergunta_l or "site" in pergunta_l:
                        pergunta = f"website da {quinta_nome}"
                    elif "morada" in pergunta_l:
                        pergunta = f"morada da {quinta_nome}"
                    elif "email" in pergunta_l:
                        pergunta = f"email da {quinta_nome}"
                    else:
                        pergunta = f"website da {quinta_nome}"
                    
                    pergunta_l = normalizar(pergunta)


    mapa_numeros = {
        "1": 0, "primeira": 0, "1a": 0, "1ª": 0, "primeiro": 0,
        "2": 1, "segunda": 1, "2a": 1, "2ª": 1, "segundo": 1,
        "3": 2, "terceira": 2, "3a": 2, "3ª": 2, "terceiro": 2,
        "4": 3, "quarta": 3, "4a": 3, "4ª": 3, "quarto": 3,
        "5": 4, "quinta": 4, "5a": 4, "5ª": 4, "quinto": 4,
        "6": 5, "sexta": 5, "6a": 5, "6ª": 5, "sexto": 5,
        "7": 6, "setima": 6, "sétima": 6, "7a": 6, "7ª": 6, "setimo": 6,
        "8": 7, "oitava": 7, "8a": 7, "8ª": 7, "oitavo": 7,
        "9": 8, "nona": 8, "9a": 8, "9ª": 8, "nono": 8,
        "10": 9, "decima": 9, "décima": 9, "10a": 9, "10ª": 9, "decimo": 9,
    }
    
    if "ultima_lista_quintas" in st.session_state and st.session_state.ultima_lista_quintas:
        import re
        for ref, idx in mapa_numeros.items():
            padroes = [
                rf'\be\s+da\s+{re.escape(ref)}\b',
                rf'\bda\s+{re.escape(ref)}\b',
                rf'^{re.escape(ref)}$',
            ]
            
            if any(re.search(p, pergunta_l, re.IGNORECASE) for p in padroes):
                if idx < len(st.session_state.ultima_lista_quintas):
                    quinta_nome = st.session_state.ultima_lista_quintas[idx]
                    
                    if "website" in pergunta_l or "site" in pergunta_l:
                        pergunta = f"website da {quinta_nome}"
                    elif "morada" in pergunta_l:
                        pergunta = f"morada da {quinta_nome}"
                    elif "email" in pergunta_l:
                        pergunta = f"email da {quinta_nome}"
                    else:
                        pergunta = f"website da {quinta_nome}"
                    
                    pergunta_l = normalizar(pergunta)


    mapa_numeros = {
        "1": 0, "primeira": 0, "1a": 0, "1ª": 0, "primeiro": 0,
        "2": 1, "segunda": 1, "2a": 1, "2ª": 1, "segundo": 1,
        "3": 2, "terceira": 2, "3a": 2, "3ª": 2, "terceiro": 2,
        "4": 3, "quarta": 3, "4a": 3, "4ª": 3, "quarto": 3,
        "5": 4, "quinta": 4, "5a": 4, "5ª": 4, "quinto": 4,
        "6": 5, "sexta": 5, "6a": 5, "6ª": 5, "sexto": 5,
        "7": 6, "setima": 6, "sétima": 6, "7a": 6, "7ª": 6, "setimo": 6,
        "8": 7, "oitava": 7, "8a": 7, "8ª": 7, "oitavo": 7,
        "9": 8, "nona": 8, "9a": 8, "9ª": 8, "nono": 8,
        "10": 9, "decima": 9, "décima": 9, "10a": 9, "10ª": 9, "decimo": 9,
    }
    
    if "ultima_lista_quintas" in st.session_state and st.session_state.ultima_lista_quintas:
        import re
        for ref, idx in mapa_numeros.items():
            padroes = [
                rf'\be\s+da\s+{re.escape(ref)}\b',
                rf'\bda\s+{re.escape(ref)}\b',
                rf'^{re.escape(ref)}$',
            ]
            
            if any(re.search(p, pergunta_l, re.IGNORECASE) for p in padroes):
                if idx < len(st.session_state.ultima_lista_quintas):
                    quinta_nome = st.session_state.ultima_lista_quintas[idx]
                    
                    if "website" in pergunta_l or "site" in pergunta_l:
                        pergunta = f"website da {quinta_nome}"
                    elif "morada" in pergunta_l:
                        pergunta = f"morada da {quinta_nome}"
                    elif "email" in pergunta_l:
                        pergunta = f"email da {quinta_nome}"
                    else:
                        pergunta = f"website da {quinta_nome}"
                    
                    pergunta_l = normalizar(pergunta)


    mapa_numeros = {
        "1": 0, "primeira": 0, "1a": 0, "1ª": 0, "primeiro": 0,
        "2": 1, "segunda": 1, "2a": 1, "2ª": 1, "segundo": 1,
        "3": 2, "terceira": 2, "3a": 2, "3ª": 2, "terceiro": 2,
        "4": 3, "quarta": 3, "4a": 3, "4ª": 3, "quarto": 3,
        "5": 4, "quinta": 4, "5a": 4, "5ª": 4, "quinto": 4,
        "6": 5, "sexta": 5, "6a": 5, "6ª": 5, "sexto": 5,
        "7": 6, "setima": 6, "sétima": 6, "7a": 6, "7ª": 6, "setimo": 6,
        "8": 7, "oitava": 7, "8a": 7, "8ª": 7, "oitavo": 7,
        "9": 8, "nona": 8, "9a": 8, "9ª": 8, "nono": 8,
        "10": 9, "decima": 9, "décima": 9, "10a": 9, "10ª": 9, "decimo": 9,
    }
    
    if "ultima_lista_quintas" in st.session_state and st.session_state.ultima_lista_quintas:
        import re
        for ref, idx in mapa_numeros.items():
            padroes = [
                rf'\be\s+da\s+{re.escape(ref)}\b',
                rf'\bda\s+{re.escape(ref)}\b',
                rf'^{re.escape(ref)}$',
            ]
            
            if any(re.search(p, pergunta_l, re.IGNORECASE) for p in padroes):
                if idx < len(st.session_state.ultima_lista_quintas):
                    quinta_nome = st.session_state.ultima_lista_quintas[idx]
                    
                    if "website" in pergunta_l or "site" in pergunta_l:
                        pergunta = f"website da {quinta_nome}"
                    elif "morada" in pergunta_l:
                        pergunta = f"morada da {quinta_nome}"
                    elif "email" in pergunta_l:
                        pergunta = f"email da {quinta_nome}"
                    else:
                        pergunta = f"website da {quinta_nome}"
                    
                    pergunta_l = normalizar(pergunta)


    mapa_numeros = {
        "1": 0, "primeira": 0, "1a": 0, "1ª": 0, "primeiro": 0,
        "2": 1, "segunda": 1, "2a": 1, "2ª": 1, "segundo": 1,
        "3": 2, "terceira": 2, "3a": 2, "3ª": 2, "terceiro": 2,
        "4": 3, "quarta": 3, "4a": 3, "4ª": 3, "quarto": 3,
        "5": 4, "quinta": 4, "5a": 4, "5ª": 4, "quinto": 4,
        "6": 5, "sexta": 5, "6a": 5, "6ª": 5, "sexto": 5,
        "7": 6, "setima": 6, "sétima": 6, "7a": 6, "7ª": 6, "setimo": 6,
        "8": 7, "oitava": 7, "8a": 7, "8ª": 7, "oitavo": 7,
        "9": 8, "nona": 8, "9a": 8, "9ª": 8, "nono": 8,
        "10": 9, "decima": 9, "décima": 9, "10a": 9, "10ª": 9, "decimo": 9,
    }
    
    if "ultima_lista_quintas" in st.session_state and st.session_state.ultima_lista_quintas:
        import re
        for ref, idx in mapa_numeros.items():
            padroes = [
                rf'\be\s+da\s+{re.escape(ref)}\b',
                rf'\bda\s+{re.escape(ref)}\b',
                rf'^{re.escape(ref)}$',
            ]
            
            if any(re.search(p, pergunta_l, re.IGNORECASE) for p in padroes):
                if idx < len(st.session_state.ultima_lista_quintas):
                    quinta_nome = st.session_state.ultima_lista_quintas[idx]
                    
                    if "website" in pergunta_l or "site" in pergunta_l:
                        pergunta = f"website da {quinta_nome}"
                    elif "morada" in pergunta_l:
                        pergunta = f"morada da {quinta_nome}"
                    elif "email" in pergunta_l:
                        pergunta = f"email da {quinta_nome}"
                    else:
                        pergunta = f"website da {quinta_nome}"
                    
                    pergunta_l = normalizar(pergunta)


    tem_nome_quinta = (
        re.search(r'[A-Z][a-z]+\s+[A-Z]', pergunta) or  # "Casa Lagoa", "Monte Verde"
        re.search(r'C\.R\.|quinta|casa|monte|herdade', pergunta_l) or
        any(len(palavra) > 3 and palavra[0].isupper() for palavra in pergunta.split())
    )
    
    # Perguntas sobre características específicas de quintas
    if any(p in pergunta_l for p in ["website", "link", "site", "endereco", "endereço", "morada", "contacto", "email", "telefone", "onde e", "onde fica"]) and tem_nome_quinta:
        resposta_llm = gerar_resposta_llm(
            pergunta=pergunta,
            perfil_completo=perfil_completo,  # ← CORRIGIDO
            contexto_base=contexto_base,
            contexto_conversa=contexto_anterior
        )
        guardar_mensagem(perfil_completo["nome"], pergunta, resposta_llm, contexto="quintas", perfil=perfil_completo)
        return resposta_llm

   if prompt := st.chat_input("Escreve a tua mensagem..."):
    # Adiciona mensagem do user
    with st.chat_message("user"):
        st.markdown(prompt)
    
    st.session_state.mensagens.append({"role": "user", "content": prompt})
    
    # Gera resposta
    resposta = gerar_resposta(prompt, perfil_completo)
    
    # Mostra resposta
    with st.chat_message("assistant"):
        st.markdown(resposta)



