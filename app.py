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

msg_saudacao = random.choice(saudacoes[categoria])

if detalhismo >= 7:
    msg_saudacao += "\n\nPodes perguntar-me sobre quintas, confirmações, detalhes da festa ou o que precisares!"

if emojis < 3:
    msg_saudacao = re.sub(r'[😀-🙏🌀-🗿🚀-🛿👋🎉🎆🎊]', '', msg_saudacao).strip()
elif emojis < 5:
    msg_saudacao = msg_saudacao.replace("🎆", "").replace("🎊", "").replace("🚀", "")

st.success(msg_saudacao)

# =====================================================
# 🧠 MOTOR DE RESPOSTA
# =====================================================
def gerar_resposta(pergunta: str, perfil_completo: dict):
    """Gera resposta personalizada baseada na pergunta"""
    
    pergunta_l = normalizar(pergunta)
    contexto_base = get_contexto_base(raw=True)
    contexto_anterior = ""
    
    # Obtém contexto de mensagens anteriores
    if "historico" in st.session_state and len(st.session_state.historico) > 0:
        ultimas = [msg for msg in st.session_state.historico[-4:] if msg["role"] == "assistant"]
        if ultimas:
            contexto_anterior = ultimas[-1]["content"].replace("**Assistente:** ", "")
    
    # ====================================================================
    # DETECÇÃO DE PERGUNTAS ESPECÍFICAS (antes do LLM)
    # ====================================================================
    
    # 0. Saudações básicas
    if pergunta_l in ["ola", "olá", "oi", "hey", "boas", "boa tarde", "bom dia", "boa noite"]:
        return f"Olá! 👋 Como posso ajudar com a festa da passagem de ano?\n\nPergunta-me sobre:\n• Quintas disponíveis\n• Datas e orçamento\n• Quem já confirmou\n• Ou o que quiseres saber!"
    
    # 0.1 Respostas de continuação (sim, não, ok, etc.)
    if pergunta_l in ["sim", "yes", "ok", "claro", "quero", "gostaria", "pode ser"]:
        # Verifica última pergunta
        if "historico" in st.session_state and st.session_state.historico:
            ultima_msg = st.session_state.historico[-1].get("content", "")
            
            # Se última pergunta foi sobre ver quintas
            if "queres saber mais" in ultima_msg.lower() or "ver a lista" in ultima_msg.lower():
                try:
                    from modules.quintas_qdrant import listar_quintas
                    quintas = listar_quintas()
                    
                    if quintas:
                        resposta = f"**Quintas contactadas ({len(quintas)}):**\n\n"
                        
                        for i, quinta in enumerate(quintas[:10], 1):
                            nome = quinta.get('nome', 'N/A')
                            zona = quinta.get('zona', 'N/A')
                            resposta += f"{i}. **{nome}** ({zona})\n"
                        
                        if len(quintas) > 10:
                            resposta += f"\n...e mais {len(quintas) - 10} quintas!"
                        
                        resposta += "\n\n💡 Pergunta sobre uma específica (ex: 'website da primeira')"
                        
                        st.session_state.ultima_lista_quintas = [q['nome'] for q in quintas[:10]]
                        
                        return resposta
                except Exception as e:
                    print(f"Erro: {e}")
                    pass
        
        # Fallback genérico para "sim"
        return "Ótimo! 😊 Sobre o que queres saber especificamente?\n\n• Lista de quintas?\n• Datas e preços?\n• Confirmações?"
    
    # 0.2 Resposta direta às opções do menu
    if "lista de quintas" in pergunta_l or pergunta_l == "lista":
        try:
            from modules.quintas_qdrant import listar_quintas
            quintas = listar_quintas()
            
            if quintas:
                resposta = f"**Quintas contactadas ({len(quintas)}):**\n\n"
                
                for i, quinta in enumerate(quintas[:10], 1):
                    nome = quinta.get('nome', 'N/A')
                    zona = quinta.get('zona', 'N/A')
                    resposta += f"{i}. **{nome}** ({zona})\n"
                
                if len(quintas) > 10:
                    resposta += f"\n...e mais {len(quintas) - 10} quintas!"
                
                resposta += "\n\n💡 Pergunta: 'website da primeira', 'morada da 5', etc."
                
                st.session_state.ultima_lista_quintas = [q['nome'] for q in quintas[:10]]
                
                return resposta
        except Exception as e:
            print(f"Erro: {e}")
            return "Erro ao carregar quintas! 😕"
    
    if "datas e precos" in pergunta_l or "datas e preco" in pergunta_l or pergunta_l in ["datas", "precos", "preço", "orcamento", "orçamento"]:
        return "📅 **Datas:** 30 de Dezembro de 2025 a 4 de Janeiro de 2026\n\n💰 **Orçamento:** 250-300€ por pessoa\n\n5 noites de festa incluindo alojamento e refeições! 🎉"
    
    # 1. Perguntas sobre quinta reservada
    if any(palavra in pergunta_l for palavra in ["ja temos", "temos alguma", "ha alguma", "quinta reservada", "local reservado"]):
        return """🏡 **Sim!** 

Temos o **Monte da Galega** pré-reservado como plano B, mas ainda estamos a avaliar outras opções para garantir que escolhemos o melhor local para a festa! 🎉

Já contactámos **35 quintas**. Queres saber mais sobre elas?"""
    
    # 2. Lista de quintas
    if any(palavra in pergunta_l for palavra in ["quais quintas", "que quintas", "lista de quintas", "quintas contactadas", "lista quintas", "ver quintas", "mostrar quintas"]):
        try:
            from modules.quintas_qdrant import listar_quintas
            quintas = listar_quintas()
            
            if quintas:
                resposta = f"**Quintas contactadas ({len(quintas)}):**\n\n"
                
                for i, quinta in enumerate(quintas[:10], 1):  # Primeiras 10
                    nome = quinta.get('nome', 'N/A')
                    zona = quinta.get('zona', 'N/A')
                    resposta += f"{i}. **{nome}** ({zona})\n"
                
                if len(quintas) > 10:
                    resposta += f"\n...e mais {len(quintas) - 10} quintas!"
                
                resposta += "\n\n💡 Pergunta sobre uma específica (ex: 'website da primeira') ou por zona (ex: 'quintas em Cáceres')"
                
                # Guarda lista no session state
                st.session_state.ultima_lista_quintas = [q['nome'] for q in quintas[:10]]
                
                return resposta
            else:
                return "Ainda não temos quintas registadas. 😕"
        except Exception as e:
            print(f"Erro ao listar quintas: {e}")
            return "Erro ao carregar quintas. Tenta novamente!"
    
    # 3. Quantas quintas responderam (ANTES de "quantas quintas" geral)
    if any(palavra in pergunta_l for palavra in ["quantas responderam", "quantas quintas responderam", "quintas que responderam", "respostas de quintas"]):
        try:
            from modules.quintas_qdrant import listar_quintas
            quintas = listar_quintas()
            
            # Conta quintas com resposta (tem email ou status)
            com_resposta = [q for q in quintas if q.get('respondeu') or q.get('email_resposta') or q.get('status') in ['respondeu', 'interessado', 'disponivel']]
            
            total = len(quintas)
            responderam = len(com_resposta)
            percentagem = (responderam / total * 100) if total > 0 else 0
            
            resposta = f"📧 **Respostas:** {responderam} de {total} quintas ({percentagem:.0f}%)\n\n"
            
            if responderam > 0:
                resposta += "✅ **Quintas que responderam:**\n"
                for q in com_resposta[:5]:  # Primeiras 5
                    nome = q.get('nome', 'N/A')
                    resposta += f"• {nome}\n"
                
                if responderam > 5:
                    resposta += f"\n...e mais {responderam - 5}!"
            else:
                resposta += "Ainda nenhuma quinta respondeu. 😔"
            
            return resposta
        except Exception as e:
            print(f"Erro ao contar respostas: {e}")
            return "Ainda estamos a processar as respostas dos emails! 📧"
    
    # 3.9 Quantas quintas (geral - contactadas)
    if any(palavra in pergunta_l for palavra in ["quantas quintas", "numero de quintas", "total de quintas"]):
        try:
            from modules.quintas_qdrant import listar_quintas
            quintas = listar_quintas()
            return f"Já contactámos **{len(quintas)} quintas**! 🎉\n\nQueres ver a lista? Pergunta 'quais quintas?'"
        except:
            return "Já contactámos **35 quintas**! 🎉"
    
    # 3.5 Quantas pessoas confirmaram / Total confirmados
    if any(palavra in pergunta_l for palavra in ["quantas pessoas", "quantos confirmaram", "total de confirmados", "numero de confirmados"]):
        try:
            confirmados_data = get_confirmados()
            confirmados = confirmados_data.get('confirmados', [])
            total = len(confirmados)
            
            if total > 0:
                return f"**{total} pessoas** já confirmaram! 🎉\n\nQueres ver quem são? Pergunta 'quem vai?'"
            else:
                return "Ainda **ninguém** confirmou. 😔\n\nSê o primeiro! Diz 'confirmo' ou 'vou'!"
        except:
            return "Ainda estamos a recolher confirmações! 📝"
    
    # 4. Informações do evento
    if any(palavra in pergunta_l for palavra in ["quando e", "que dias", "datas", "data da festa"]):
        return "📅 **Datas:** 30 de Dezembro de 2025 a 4 de Janeiro de 2026\n\n5 noites de festa! 🎉"
    
    if any(palavra in pergunta_l for palavra in ["qual a cor", "cor do ano", "tema"]):
        return "🎨 **Cor deste ano:** Amarelo! ☀️"
    
    if any(palavra in pergunta_l for palavra in ["orcamento", "orçamento", "quanto custa", "preco", "preço"]):
        return "💰 **Orçamento:** 250-300€ por pessoa\n\nInclui alojamento, refeições e festa! 🎉"
    
    # 5. Quem vai / Confirmações
    if any(palavra in pergunta_l for palavra in ["quem vai", "quem confirmou", "lista de confirmados", "ver confirmados"]) or pergunta_l in ["confirmacoes", "confirmações"]:
        try:
            confirmados_data = get_confirmados()
            
            print(f"🔍 Debug confirmações: {confirmados_data}")  # Debug
            
            # Tenta diferentes estruturas de dados
            if isinstance(confirmados_data, dict):
                confirmados = confirmados_data.get('confirmados', [])
            elif isinstance(confirmados_data, list):
                confirmados = confirmados_data
            else:
                confirmados = []
            
            print(f"✅ Confirmados processados: {confirmados}")  # Debug
            
            if confirmados and len(confirmados) > 0:
                resposta = f"**Confirmados ({len(confirmados)}):**\n\n"
                for nome_c in confirmados:
                    resposta += f"✅ {nome_c}\n"
                return resposta
            else:
                return "Ainda ninguém confirmou. 😔\n\nSê o primeiro! Diz 'confirmo' ou 'vou'!"
        except Exception as e:
            print(f"❌ Erro ao buscar confirmações: {e}")
            import traceback
            traceback.print_exc()
            return "Erro ao carregar confirmações. Tenta novamente! 😕"
    
    # 6. X vai? (verificar pessoa específica)
    match_vai = re.search(r'(?:o|a)?\s*(\w+)\s+vai', pergunta_l)
    if match_vai:
        nome_busca = match_vai.group(1)
        try:
            confirmados_data = get_confirmados()
            confirmados = confirmados_data.get('confirmados', [])
            
            # Normaliza e procura
            confirmado = any(nome_busca.lower() in c.lower() for c in confirmados)
            
            if confirmado:
                return f"✅ **Sim!** {nome_busca.title()} já confirmou presença! 🎉"
            else:
                return f"❌ **Ainda não.** {nome_busca.title()} ainda não confirmou."
        except:
            pass
    
    # ====================================================================
    # Se não matchou nenhuma pergunta específica, usa LLM
    # ====================================================================
    
    # Detecção de nome de quinta na pergunta
    quinta_na_pergunta = re.search(
        r'(C\.R\.|Casa|Monte|Herdade|Quinta)\s+([A-Z][^\?]+?)(?:\s+é|\s+fica|\s+tem|\?|$)', 
        pergunta, 
        re.IGNORECASE
    )
    
    if quinta_na_pergunta:
        nome_detectado = quinta_na_pergunta.group(0).strip().rstrip('?').strip()
        nome_detectado = re.sub(r'\s+(é|fica|tem|onde|como|quando).*$', '', nome_detectado, flags=re.IGNORECASE).strip()
        st.session_state.ultima_quinta_mencionada = nome_detectado
        print(f"🔍 Quinta detectada na pergunta: {nome_detectado}")
    
    # Verifica se tem nome de quinta
    tem_nome_quinta = (
        re.search(r'[A-Z][a-z]+\s+[A-Z]', pergunta) or
        re.search(r'C\.R\.|quinta|casa|monte|herdade', pergunta_l) or
        any(len(palavra) > 3 and palavra[0].isupper() for palavra in pergunta.split())
    )
    
    # Perguntas específicas sobre quintas (website, morada, etc.)
    if any(p in pergunta_l for p in ["website", "link", "site", "endereco", "endereço", "morada", "contacto", "email", "telefone", "onde e", "onde fica"]) and tem_nome_quinta:
        resposta_llm = gerar_resposta_llm(
            pergunta=pergunta,
            perfil_completo=perfil_completo,
            contexto_base=contexto_base,
            contexto_conversa=contexto_anterior
        )
        guardar_mensagem(perfil_completo["nome"], pergunta, resposta_llm, contexto="quintas", perfil=perfil_completo)
        return resposta_llm
    
    # Resposta genérica por LLM
    resposta_llm = gerar_resposta_llm(
        pergunta=pergunta,
        perfil_completo=perfil_completo,
        contexto_base=contexto_base,
        contexto_conversa=contexto_anterior
    )
    guardar_mensagem(perfil_completo["nome"], pergunta, resposta_llm, contexto="geral", perfil=perfil_completo)
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