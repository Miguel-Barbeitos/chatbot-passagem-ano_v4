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
from modules.organizacao import (
    get_evento,
    get_datas_evento,
    get_tema_cor,
    get_orcamento,
    get_stats_quintas,
    responder_pergunta_organizacao
)

# =====================================================
# ⚙️ CONFIGURAÇÃO
# =====================================================
USE_GROQ_ALWAYS = False

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
    
    nomes = sorted([p["nome"] for p in perfis_lista])
    
except Exception as e:
    st.error(f"⚠️ Erro ao carregar perfis: {e}")
    import traceback
    st.code(traceback.format_exc())
    
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

try:
    perfil_completo = buscar_perfil(nome)
    if not perfil_completo:
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
personalidade = perfil_completo.get("personalidade", {})
humor = personalidade.get("humor", 5)
emojis = personalidade.get("emojis", 5)
formalidade = personalidade.get("formalidade", 5)
detalhismo = personalidade.get("detalhismo", 5)

hora = datetime.now().hour
saud = "Bom dia" if hora < 12 else "Boa tarde" if hora < 20 else "Boa noite"

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

if humor >= 7:
    categoria = "humor_alto_formal" if formalidade >= 6 else "humor_alto_informal"
elif humor >= 4:
    categoria = "humor_medio_formal" if formalidade >= 6 else "humor_medio_informal"
else:
    categoria = "humor_baixo_formal" if formalidade >= 6 else "humor_baixo_informal"

saudacao_inicial = random.choice(saudacoes[categoria])

st.title("🎆 Assistente da Festa 2025/2026")
st.markdown(f"_{saudacao_inicial}_")

# =====================================================
# 🤖 SISTEMA DE RESPOSTA (SIMPLIFICADO v4.13)
# =====================================================
def gerar_resposta(pergunta: str, perfil_completo: dict) -> str:
    """
    Gera resposta baseada em regras ou LLM
    
    v4.13: Removida TODA a lógica de quintas duplicada.
           O llm_groq.py v4.12 já faz tudo!
    """
    
    # Extrair nome do perfil
    nome = perfil_completo.get("nome", "amigo")
    
    pergunta_l = pergunta.lower().strip()
    
    # 🔑 Passar histórico completo como contexto
    contexto_conversa = st.session_state.historico if "historico" in st.session_state else []
    contexto_base = get_contexto_base()
    
    # ====================================================================
    # PRIORIDADE 0: SAUDAÇÕES E MENSAGENS CASUAIS
    # ====================================================================
    
    def remover_acentos(texto):
        """Remove acentos de um texto"""
        return ''.join(
            c for c in unicodedata.normalize('NFD', texto.lower())
            if unicodedata.category(c) != 'Mn'
        )
    
    try:
        pergunta_norm = remover_acentos(pergunta)
    except:
        pergunta_norm = pergunta_l
    
    # Detectar hora para saudação apropriada
    try:
        hora_atual = datetime.now().hour
        if hora_atual < 12:
            saudacao_uso = "Bom dia"
        elif hora_atual < 20:
            saudacao_uso = "Boa tarde"
        else:
            saudacao_uso = "Boa noite"
    except:
        saudacao_uso = "Olá"
    
    # Saudações simples
    palavras_saudacao = ["ola", "oi", "hey", "hi", "hello", "eai", "e ai"]
    frases_saudacao = ["bom dia", "boa tarde", "boa noite"]
    
    eh_saudacao = False
    if any(palavra == pergunta_norm.strip() for palavra in palavras_saudacao):
        eh_saudacao = True
    if any(frase in pergunta_norm for frase in frases_saudacao):
        eh_saudacao = True
    
    if eh_saudacao:
        return f"{saudacao_uso}, {nome}! 👋 Como posso ajudar com a organização da festa?"
    
    # Agradecimentos
    palavras_obrigado = ["obrigado", "obrigada", "thanks", "obg", "valeu", "thank you"]
    if any(palavra in pergunta_norm for palavra in palavras_obrigado):
        return "De nada! 😊 Estou aqui para ajudar!"
    
    # Como está / tudo bem
    if any(frase in pergunta_norm for frase in ["tudo bem", "como esta", "como estas", "how are you"]):
        return "Tudo ótimo por aqui! 🎉 E contigo? Precisas de ajuda com a festa?"
    
    # ====================================================================
    # PRIORIDADE 1: Usa módulo organizacao.py para perguntas frequentes
    # ====================================================================
    resposta_org = responder_pergunta_organizacao(pergunta)
    if resposta_org:
        return resposta_org
    
    # ====================================================================
    # PRIORIDADE 2: CONFIRMAÇÕES
    # ====================================================================
    
    if any(palavra in pergunta_l for palavra in ["confirmo", "vou", "eu vou", "conta comigo", "posso confirmar"]):
        intencao = detectar_intencao_confirmacao(pergunta)
        
        if intencao["tipo"] == "familia":
            familia_id = perfil_completo.get("familia_id")
            resultado = confirmar_familia_completa(familia_id, nome)
            
            if resultado["sucesso"]:
                return f"🎉 **Confirmado!** Toda a família vai:\n" + "\n".join([f"✅ {n}" for n in resultado["confirmados"]])
            else:
                return "❌ Erro ao confirmar família. Tenta novamente!"
        
        elif intencao["tipo"] == "individual":
            resultado = confirmar_pessoa(nome, confirmado_por=nome)
            
            if resultado["sucesso"]:
                resposta = f"🎉 **{resultado['mensagem']}**"
                
                if resultado["familia_sugerida"]:
                    resposta += f"\n\n👨‍👩‍👧‍👦 Mais alguém da família vai?\n"
                    resposta += "\n".join([f"• {n}" for n in resultado["familia_sugerida"]])
                    resposta += "\n\nDiz 'confirmo todos' para confirmar a família completa!"
                
                return resposta
            else:
                return f"❌ {resultado['mensagem']}"
    
    
        # ====================================================================
    # PRIORIDADE 2.1: VERIFICAR SE ALGUÉM VAI / CONFIRMOU
    # ====================================================================
    from modules.confirmacoes import verificar_confirmacao_pessoa

    # Regex para capturar nomes (evita conflito com 'quinta')
    match_nome = re.search(r"\b[A-ZÁÉÍÓÚÂÊÎÔÛÃÕ][a-záéíóúâêîôûãõç]+\b", pergunta)
    tem_quinta = any(p in pergunta_l for p in ["quinta", "quintas", "sitio", "local", "reserva"])

    if not tem_quinta and any(p in pergunta_l for p in ["vai", "vem", "comparece", "presente", "confirmou"]) and match_nome:
        nome_mencionado = match_nome.group(0)
        return verificar_confirmacao_pessoa(nome_mencionado)
            
                
                
                # ====================================================================
    # PRIORIDADE 3: LLM (FAZ TUDO O RESTO!)
    # ====================================================================
    # 
    # 🎯 v4.13 MUDANÇA CRÍTICA:
    # ───────────────────────────
    # REMOVIDA toda a lógica de quintas hard-coded!
    # 
    # ANTES (v4.12): app.py tinha ~200 linhas de lógica para:
    #   - Listar quintas
    #   - Contar respostas
    #   - Mostrar websites
    #   - Etc...
    # 
    # DEPOIS (v4.13): O llm_groq.py v4.12 JÁ FAZ TUDO!
    #   - Detecção inteligente (51 keywords)
    #   - Exclusões (26 keywords)
    #   - Contexto de conversa
    #   - Fuzzy matching
    #   - etc...
    # 
    # RESULTADO: Código mais limpo, sem duplicação, sem bugs!
    # ====================================================================
    
    # Passa TUDO para o LLM
    resposta_llm = gerar_resposta_llm(
        pergunta=pergunta,
        perfil_completo=perfil_completo,
        contexto_base=contexto_base,
        contexto_conversa=contexto_conversa  # ← Histórico completo
    )
    
    # Guardar na memória
    guardar_mensagem(
        perfil_completo["nome"], 
        pergunta, 
        resposta_llm, 
        contexto="geral", 
        perfil=perfil_completo
    )
    
    return resposta_llm

# =====================================================
# 💬 INTERFACE DE CHAT
# =====================================================

# Inicializa session state
if "mensagens" not in st.session_state:
    st.session_state.mensagens = []

if "historico" not in st.session_state:
    st.session_state.historico = []

# Mostra histórico de mensagens
for mensagem in st.session_state.mensagens:
    with st.chat_message(mensagem["role"]):
        st.markdown(mensagem["content"])

# Input do utilizador
if prompt := st.chat_input("Escreve a tua mensagem..."):
    # Mostra mensagem do user
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Guarda no histórico
    st.session_state.mensagens.append({"role": "user", "content": prompt})
    st.session_state.historico.append({"role": "user", "content": prompt})
    
    # Gera resposta
    resposta = gerar_resposta(prompt, perfil_completo)
    
    # Mostra resposta do assistente
    with st.chat_message("assistant"):
        st.markdown(resposta)
    
    # Guarda resposta no histórico
    st.session_state.mensagens.append({"role": "assistant", "content": resposta})
    st.session_state.historico.append({"role": "assistant", "content": resposta})