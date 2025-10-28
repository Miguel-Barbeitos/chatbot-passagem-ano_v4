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

hora = datetime.now().hour
saud = "Bom dia" if hora < 12 else "Boa tarde" if hora < 20 else "Boa noite"

# Mensagem personalizada baseada na personalidade
if humor > 7:
    msg_saudacao = f"{saud}, {nome}! 👋 Pronto para organizar a festa do século? 🎉"
elif humor < 3:
    msg_saudacao = f"{saud}, {nome}. Estou aqui para ajudar com a organização da festa."
else:
    msg_saudacao = f"{saud}, {nome}! 👋 Bem-vindo! Sou o teu assistente da festa 🎉"

# Adiciona emojis conforme preferência
if emojis < 3:
    msg_saudacao = msg_saudacao.replace("👋", "").replace("🎉", "").replace("🎆", "")

st.success(msg_saudacao)



# =====================================================
# 🧠 MOTOR DE RESPOSTA
# =====================================================
def gerar_resposta(pergunta: str, perfil_completo: dict):
    pergunta_l = normalizar(pergunta)
    contexto_base = get_contexto_base(raw=True)
    
    # ✅ Pega contexto da última resposta do assistente (se existir)
    contexto_anterior = ""
    lista_quintas_anterior = []
    ultima_quinta_mencionada = None
    
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
            
            # Extrai última quinta mencionada (formato: 📍 Nome (Zona))
            quinta_match = re.search(r'📍\s*\*?\*?([^(]+)\*?\*?\s*\(([^)]+)\)', contexto_anterior)
            if quinta_match:
                ultima_quinta_mencionada = {
                    "nome": quinta_match.group(1).strip(),
                    "zona": quinta_match.group(2).strip()
                }
                print(f"🏠 Última quinta: {ultima_quinta_mencionada}")
    
    # ✅ CONTEXTO: Perguntas sobre distância
    if any(p in pergunta_l for p in ["distancia", "distância", "quilometros", "quilómetros", "km", "longe", "perto", "quanto tempo", "quantos km"]):
        if ultima_quinta_mencionada:
            # Reformula para incluir o nome da quinta
            pergunta = f"qual a distância da {ultima_quinta_mencionada['nome']} até Lisboa"
            pergunta_l = normalizar(pergunta)
            print(f"🔄 Reformulado com contexto: '{pergunta}'")
    
    # ✅ CONTEXTO: Se perguntou "de que quinta" e agora responde com nome
    if contexto_anterior and "de que quinta" in contexto_anterior.lower():
        # A resposta é provavelmente o nome de uma quinta
        if len(pergunta.split()) <= 5 and not any(p in pergunta_l for p in ["quantas", "quais", "onde", "como"]):
            # Assume que é nome de quinta e pergunta distância
            pergunta = f"qual a distância de {pergunta} até Lisboa"
            pergunta_l = normalizar(pergunta)
            print(f"🔄 Contexto de continuação: '{pergunta}'")
    
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
            f"Olá, {perfil_completo['nome']}! 👋\n\n"
            "Estamos a organizar os detalhes da festa de passagem de ano 🎆\n"
            "Estou disponível para responder a qualquer questão que tenhas!"
        )

    # ✅ 2 — Confirmação de presença INTELIGENTE
    if any(p in pergunta_l for p in ["confirmo", "vou", "lá estarei", "sim vou", "confirmar", "eu vou", "nos vamos", "nós vamos", "familia vai", "família vai"]):
        print(f"✅ Confirmação detetada para: {perfil_completo['nome']}")
        
        # Deteta intenção
        intencao = detectar_intencao_confirmacao(pergunta)
        
        if intencao["tipo"] == "familia":
            # Confirmar família completa
            familia_id = perfil_completo.get("familia_id")
            resultado = confirmar_familia_completa(familia_id, perfil_completo["nome"])
            
            if resultado["sucesso"]:
                nomes = ", ".join(resultado["confirmados"])
                return f"🎉 Família confirmada!\n\n✅ {nomes}\n\nVejo-vos lá! 🎆"
            else:
                return f"⚠️ {resultado['mensagem']}"
        
        else:
            # Confirmar individual
            resultado = confirmar_pessoa(perfil_completo["nome"])
            
            if resultado["sucesso"]:
                msg = f"🎉 {resultado['mensagem']}!"
                
                # Sugere família se houver
                if resultado["familia_sugerida"]:
                    sugestoes = ", ".join(resultado["familia_sugerida"][:3])
                    msg += f"\n\n💡 Queres confirmar também: {sugestoes}?"
                
                return msg
            else:
                return f"⚠️ {resultado['mensagem']}"

    # ✅ 3 — Perguntas sobre confirmados
    if any(p in pergunta_l for p in ["quem vai", "quem confirmou", "quantos somos", "quantos sao", "quantos vao", "quantos vão"]):
        try:
            confirmados_atual = get_confirmados()
            stats = get_estatisticas()
            
            if confirmados_atual and len(confirmados_atual) > 0:
                # Agrupa por família
                familias = {}
                for conf in confirmados_atual:
                    p = buscar_perfil(conf)
                    if p:
                        fam_id = p.get("familia_id", "Outros")
                        if fam_id not in familias:
                            familias[fam_id] = []
                        familias[fam_id].append(conf)
                
                msg = f"**Confirmados ({stats['total_confirmados']}):**\n\n"
                
                for fam_id, membros in familias.items():
                    if len(membros) > 1:
                        msg += f"👨‍👩‍👧‍👦 {', '.join(membros)}\n"
                    else:
                        msg += f"👤 {membros[0]}\n"
                
                return msg
            else:
                return "Ainda ninguém confirmou 😅 Sê o primeiro! Diz 'eu vou'"
        except Exception as e:
            print(f"❌ Erro: {e}")
            return "Vê a lista ao lado 👈"

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
            perfil=perfil_completo,  # ← CORRIGIDO
            contexto_base=contexto_base,
            contexto_conversa=contexto_anterior
        )
        guardar_mensagem(perfil_completo["nome"], pergunta, resposta_llm, contexto="quintas", perfil=perfil_completo)
        return resposta_llm

    # ✅ 5 — Perguntas sobre ZONAS, listas de quintas, ou queries SQL
    if any(p in pergunta_l for p in [
        "que quintas", "quais quintas", "quantas quintas", "quantas vimos", 
        "quantas contactamos", "lista", "opcoes", "opções", "nomes", 
        "em ", "zona", "quais", "mais perto", "proxima", "próxima",
        "responderam", "resposta", "numero de pessoas", "número de pessoas",
        "capacidade", "pessoas", "tem capacidade", "quantas tem",
        "ja vimos", "vimos", "contactamos",
        "distancia", "distância", "quilometros", "quilómetros", "km", "longe"
    ]):
        resposta_llm = gerar_resposta_llm(
            pergunta=pergunta,
            perfil=perfil_completo,  # ← CORRIGIDO
            contexto_base=contexto_base,
            contexto_conversa=contexto_anterior,
            ultima_quinta=ultima_quinta_mencionada
        )
        guardar_mensagem(perfil_completo["nome"], pergunta, resposta_llm, contexto="quintas", perfil=perfil_completo)
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
    
    # ✅ 8 — Perguntas pessoais/casuais ao bot (responde com humor)
    perguntas_pessoais = {
        # Identidade
        ("como te chamas", "qual o teu nome", "quem es", "quem és"): [
            "Sou o assistente oficial da festa! 🤖 Podes chamar-me de 'organizador virtual' 😄",
            "Não tenho nome oficial, mas aceito sugestões! 😊 Entretanto, trata-me por 'amigo da festa' 🎉"
        ],
        # Família
        ("tens filhos", "tens familia", "tens família", "tens pais"): [
            "Não tenho filhos, mas tenho 35 quintas para cuidar! 🏡😅",
            "A minha família são vocês, os convidados da festa! 🎆👨‍👩‍👧‍👦"
        ],
        # Idade
        ("quantos anos", "que idade", "quando nasceste"): [
            "Nasci há poucos dias, especialmente para esta festa! 🎂🤖",
            "Sou jovem mas já vi muitas quintas! 😄"
        ],
        # Localização
        ("onde vives", "onde moras", "onde estas", "onde estás"): [
            "Vivo na nuvem ☁️ Literalmente! Mas o meu coração está com a festa 🎉",
            "Estou onde quer que precises de mim! 😊 Neste momento, a ajudar-te a organizar a festa!"
        ],
        # Estado
        ("como estas", "como estás", "tudo bem", "como vai"): [
            "Estou ótimo, obrigado! 😊 A organizar festas como deve ser! E tu?",
            "Super bem! Ocupado com 35 quintas mas sempre disponível para ti 🎉"
        ],
        # Preferências
        ("gostas de", "qual a tua", "preferes"): [
            "Gosto de ajudar a organizar festas épicas! 🎆 E tu, já confirmaste presença?",
            "Adoro quintas com piscina e boa comida! 🏊🍽️ Mas sou um bot sem muito paladar 😅"
        ],
        # Humor/Piadas
        ("conta uma piada", "faz uma piada", "diz uma piada"): [
            "Porque é que o bot foi à festa? Para processar a diversão! 🤖😄",
            "Qual é a diferença entre um bot e uma quinta? Um tem memória RAM, o outro tem carneiros! 🐏😅"
        ],
        # Namorada/Relacionamentos
        ("tens namorada", "tens namorado", "estas apaixonado", "estás apaixonado"): [
            "Estou apaixonado... pela organização perfeita desta festa! 💕🎉",
            "O meu amor é platónico: amo quintas com boa capacidade e preço justo! 🏡😄"
        ]
    }
    
    # Verifica se é pergunta pessoal
    for triggers, respostas in perguntas_pessoais.items():
        if any(t in pergunta_l for t in triggers):
            import random
            return random.choice(respostas)
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
        perfil_completo=perfil_completo,
        contexto_base=contexto_base,
    )

    guardar_mensagem(perfil_completo["nome"], pergunta, resposta_llm, contexto="geral", perfil=perfil_completo)
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
        resposta = gerar_resposta(prompt, perfil_completo)  # ← Usa perfil_completo

    with st.chat_message("assistant"):
        st.markdown(f"**Assistente:** {resposta}")

    st.session_state.historico.append({"role": "user", "content": f"**{nome}:** {prompt}"})
    st.session_state.historico.append({"role": "assistant", "content": f"**Assistente:** {resposta}"})