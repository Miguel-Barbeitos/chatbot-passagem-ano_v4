"""
llm_groq.py - VERSÃO 2.0 COM PERSONALIZAÇÃO COMPLETA
=====================================================
Melhorias implementadas:
✅ Personalização completa baseada em perfis
✅ Ajuste dinâmico de temperatura, max_tokens e tom
✅ Remoção inteligente de emojis
✅ Adaptação de formalidade e detalhismo
✅ Sistema de prompts personalizados por tipo de pergunta
"""

import os
import json
import requests
import sqlite3
import pandas as pd
import streamlit as st
import re

from learning_qdrant import procurar_resposta_semelhante

# =====================================================
# 🔄 INTEGRAÇÃO COM QDRANT (quintas_info)
# =====================================================
try:
    from modules.quintas_qdrant import executar_sql as executar_sql_qdrant
    USAR_QDRANT = True
    print("✅ Quintas: Usando Qdrant (quintas_info)")
except ImportError as e:
    USAR_QDRANT = False
    print(f"⚠️ Quintas: Qdrant não disponível, usando SQLite fallback ({e})")


# =====================================================
# ⚙️ CONFIGURAÇÃO GERAL
# =====================================================
# IMPORTANTE: A API key DEVE estar em .streamlit/secrets.toml
# Nunca hardcode API keys no código!
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except KeyError:
    raise ValueError(
        "❌ GROQ_API_KEY não encontrada!\n"
        "Por favor configura em .streamlit/secrets.toml:\n"
        "GROQ_API_KEY = \"sua_chave_aqui\""
    )

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"
DATA_PATH = "data/event.json"

# =====================================================
# 🎨 CONSTRUÇÃO DE PERSONALIDADE (MELHORADO)
# =====================================================
def construir_personalidade_prompt(perfil_completo):
    """
    Constrói instruções de personalização baseadas no perfil.
    NOVO: Inclui exemplos práticos para cada nível de personalidade.
    """
    if not perfil_completo:
        return ""
    
    personalidade = perfil_completo.get("personalidade", {})
    humor = personalidade.get("humor", 5)
    emojis = personalidade.get("emojis", 5)
    detalhismo = personalidade.get("detalhismo", 5)
    formalidade = personalidade.get("formalidade", 5)
    paciencia = personalidade.get("paciencia", 5)
    
    instrucoes = []
    
    # 🎭 HUMOR COM EXEMPLOS
    if humor >= 8:
        instrucoes.append("- 🎭 Usa MUITO humor, piadas e expressões divertidas (ex: 'Mais quintas que dias de chuva em Portugal!' 😄)")
    elif humor >= 6:
        instrucoes.append("- 🎭 Usa humor moderado e tom amigável (ex: 'Temos tantas opções que até custa escolher! 😊')")
    elif humor >= 4:
        instrucoes.append("- 🎭 Mantém um tom leve mas neutro (ex: 'Já contactámos várias quintas interessantes.')")
    else:
        instrucoes.append("- 🎭 Mantém um tom sério e direto, sem piadas (ex: 'Foram contactadas 12 quintas. Lista disponível.')")
    
    # 😊 EMOJIS COM FREQUÊNCIA
    if emojis >= 8:
        instrucoes.append("- 😊 Usa MUITOS emojis variados (4-6 por resposta, diferentes tipos)")
    elif emojis >= 6:
        instrucoes.append("- 😊 Usa alguns emojis (2-3 por resposta)")
    elif emojis >= 4:
        instrucoes.append("- 😊 Usa poucos emojis (1 por resposta, só os essenciais)")
    else:
        instrucoes.append("- 😊 NÃO uses emojis nenhuns")
    
    # 📊 DETALHISMO COM ESTRUTURA
    if detalhismo >= 8:
        instrucoes.append("- 📊 Dá respostas MUITO detalhadas (4-6 frases, explica tudo com contexto e exemplos)")
    elif detalhismo >= 6:
        instrucoes.append("- 📊 Dá respostas detalhadas (3-4 frases, inclui informação relevante)")
    elif detalhismo >= 4:
        instrucoes.append("- 📊 Dá respostas médias (2-3 frases, informação essencial)")
    else:
        instrucoes.append("- 📊 Dá respostas MUITO curtas e diretas (1-2 frases, apenas o essencial)")
    
    # 👔 FORMALIDADE COM VOCABULÁRIO
    if formalidade >= 8:
        instrucoes.append("- 👔 Usa linguagem MUITO formal (tratamento por 'você', vocabulário cuidado, sem calão)")
    elif formalidade >= 6:
        instrucoes.append("- 👔 Usa linguagem formal mas amigável (tratamento respeitoso mas próximo)")
    elif formalidade >= 4:
        instrucoes.append("- 👔 Usa linguagem casual (tratamento por 'tu', linguagem do dia-a-dia)")
    else:
        instrucoes.append("- 👔 Usa linguagem MUITO casual (gírias portuguesas, expressões à vontade, super informal)")
    
    # ⏱️ PACIÊNCIA (NOVO!)
    if paciencia >= 7:
        instrucoes.append("- ⏱️ Sê muito paciente e detalhado, mesmo com perguntas repetidas")
    elif paciencia < 4:
        instrucoes.append("- ⏱️ Sê direto e objetivo, vai ao ponto rapidamente")
    
    return "\n".join(instrucoes)

# =====================================================
# 🎯 PARÂMETROS LLM PERSONALIZADOS (NOVO)
# =====================================================
def calcular_parametros_llm(perfil_completo):
    """
    Calcula temperatura, max_tokens e top_p baseado na personalidade.
    NOVO: Sistema inteligente de ajuste de parâmetros.
    """
    if not perfil_completo:
        return {"temperature": 0.5, "max_tokens": 200, "top_p": 0.9}
    
    personalidade = perfil_completo.get("personalidade", {})
    humor = personalidade.get("humor", 5)
    detalhismo = personalidade.get("detalhismo", 5)
    
    # 🌡️ TEMPERATURE: controla criatividade
    # Mais humor = mais criatividade
    if humor >= 8:
        temperature = 0.9
    elif humor >= 6:
        temperature = 0.7
    elif humor >= 4:
        temperature = 0.5
    else:
        temperature = 0.3
    
    # 📏 MAX_TOKENS: controla tamanho da resposta
    if detalhismo >= 8:
        max_tokens = 400  # Respostas longas
    elif detalhismo >= 6:
        max_tokens = 250  # Respostas médias-longas
    elif detalhismo >= 4:
        max_tokens = 150  # Respostas médias
    else:
        max_tokens = 100  # Respostas curtas
    
    # 🎯 TOP_P: controla diversidade de vocabulário
    # Mais formal = menos diversidade (top_p baixo)
    formalidade = personalidade.get("formalidade", 5)
    if formalidade >= 7:
        top_p = 0.8  # Vocabulário mais consistente
    else:
        top_p = 0.95  # Vocabulário mais variado
    
    return {
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": top_p
    }

# =====================================================
# 🧹 PÓS-PROCESSAMENTO DE RESPOSTAS (NOVO)
# =====================================================
def processar_resposta(resposta, perfil_completo):
    """
    Processa a resposta do LLM baseado nas preferências do utilizador.
    NOVO: Remoção inteligente de emojis, ajuste de pontuação.
    """
    if not perfil_completo:
        return resposta
    
    personalidade = perfil_completo.get("personalidade", {})
    emojis_pref = personalidade.get("emojis", 5)
    formalidade = personalidade.get("formalidade", 5)
    
    # 🚫 Remove emojis se o utilizador não gosta
    if emojis_pref < 3:
        # Remove emojis Unicode
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE)
        resposta = emoji_pattern.sub('', resposta)
        resposta = re.sub(r'\s+', ' ', resposta).strip()
    
    # ✂️ Remove exclamações excessivas se for muito formal
    if formalidade >= 8:
        resposta = re.sub(r'!+', '.', resposta)  # Substitui ! por .
        resposta = re.sub(r'\.{2,}', '.', resposta)  # Remove ... excessivos
    
    # 🔠 Ajusta capitalização se for casual
    if formalidade < 3:
        # Mantém como está (pode ter minúsculas no início)
        pass
    
    return resposta.strip()

# =====================================================
# 🔍 NORMALIZAÇÃO E DETEÇÃO
# =====================================================
def normalizar_zona(texto: str) -> str:
    """Normaliza nome de zona para fazer buscas flexíveis"""
    import unicodedata
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    texto = texto.lower().strip().rstrip('s')
    texto = re.sub(r'[^\w\s]', '', texto)
    return texto

def e_pergunta_de_quintas(pergunta: str) -> bool:
    """Deteta se a pergunta é sobre quintas / base de dados."""
    p = pergunta.lower()
    tem_nome_quinta = (
        re.search(r'[A-Z][a-z]+\s+[A-Z]', pergunta) or
        'c.r.' in p or 'quinta' in p or 'casa' in p or 'monte' in p or 'herdade' in p
    )
    chaves = [
        "quinta", "quintas", "que quintas", "quais quintas", "quantas quintas",
        "contactadas", "contactaste", "responderam", "falamos", "vimos",
        "website", "link", "site", "endereco", "endereço", "morada", "contacto",
        "email", "telefone", "piscina", "capacidade", "custo", "barata", "animais", 
        "resposta", "zona", "opcoes", "opções", "disponivel", "disponível",
        "preco", "preço", "churrasqueira", "snooker", "estado", "procura",
        "quantas", "quais", "lista", "nomes", "em ", "mais perto", "proxima", 
        "próxima", "onde e", "onde fica"
    ]
    return tem_nome_quinta or any(c in p for c in chaves)

def e_pergunta_estado(pergunta: str) -> bool:
    """Deteta perguntas sobre o estado das quintas."""
    termos = ["porquê", "porque", "motivo", "estado", "respondeu", "atualização", 
              "contactaste", "falaste", "ja vimos", "já vimos", "progresso"]
    return any(t in pergunta.lower() for t in termos)

# =====================================================
# 🤖 GERAR SQL COM PERSONALIZAÇÃO (MELHORADO)
# =====================================================
def gerar_sql_da_pergunta(pergunta: str, perfil_completo=None) -> str:
    """
    Usa o LLM para gerar um SQL seguro (apenas SELECT).
    MELHORADO: Inclui contexto de personalidade para queries mais naturais.
    """
    schema = """
    Tabela: quintas
    Colunas: nome, zona, morada, email, telefone, website, estado, resposta,
    capacidade_43, custo_4500, estimativa_custo, capacidade_confirmada,
    ultima_resposta, proposta_tarifaria, unidades_detalhe, num_unidades,
    observacao_unidades, custo_total (REAL), resumo_resposta, observacoes, notas_calculo
    """

    prompt_sql = f"""
Gera APENAS o SQL (SELECT ...) para responder à pergunta.
Pergunta: "{pergunta}"
{schema}

Exemplos:
1. "Quantas quintas já contactámos?" → SELECT COUNT(*) as total FROM quintas
2. "Que quintas já contactámos?" → SELECT nome, zona, morada FROM quintas LIMIT 20
3. "Quantas responderam?" → SELECT COUNT(*) as total FROM quintas WHERE resposta IS NOT NULL
4. "Quintas com capacidade para 43" → SELECT nome, zona FROM quintas WHERE capacidade_43 LIKE '%sim%'
5. "Quintas em Lisboa" → SELECT nome, zona FROM quintas WHERE zona LIKE '%Lisboa%'

Gera apenas o SQL, sem explicações.
"""

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "És um assistente que converte linguagem natural em SQL seguro."},
            {"role": "user", "content": prompt_sql}
        ],
        "temperature": 0.0,
        "max_tokens": 150
    }

    try:
        resp = requests.post(GROQ_URL, headers=headers, json=data, timeout=20)
        query = resp.json()["choices"][0]["message"]["content"].strip()
        if "```sql" in query:
            query = query.split("```sql")[1].split("```")[0].strip()
        elif "```" in query:
            query = query.split("```")[1].split("```")[0].strip()
        query = " ".join(query.split())
        if query.lower().startswith("select"):
            print(f"✅ SQL gerado: {query}")
            return query
        else:
            print(f"⚠️ SQL inválido: {query}")
    except Exception as e:
        print(f"⚠️ Erro a gerar SQL: {e}")
    return None

# =====================================================
# 🧠 EXECUTAR SQL
# =====================================================
def executar_sql(query: str):
    """
    Executa query SQL usando Qdrant (se disponível) ou SQLite fallback
    """
    if USAR_QDRANT:
        try:
            return executar_sql_qdrant(query)
        except Exception as e:
            print(f"⚠️ Erro no Qdrant, tentando SQLite: {e}")
    
    # Fallback para SQLite
    try:
        conn = sqlite3.connect("data/quintas.db")
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"⚠️ Erro ao executar SQL: {e}")
        return []

def gerar_resposta_dados_llm(pergunta, dados, perfil_completo=None):
    """
    Transforma dados SQL em texto natural com personalização COMPLETA.
    MELHORADO: Sistema inteligente de ajuste de parâmetros e pós-processamento.
    """
    json_data = json.dumps(dados, ensure_ascii=False, indent=2)
    
    # Instruções de personalidade
    personalidade_instrucoes = construir_personalidade_prompt(perfil_completo)
    nome = perfil_completo.get("nome", "utilizador") if perfil_completo else "utilizador"
    
    # Calcula parâmetros LLM
    params = calcular_parametros_llm(perfil_completo)
    
    prompt = f"""
Transforma estes dados JSON numa resposta natural em Português de Portugal.

DADOS:
{json_data}

PERGUNTA: "{pergunta}"

REGRAS GERAIS:
- USA APENAS OS DADOS FORNECIDOS - NUNCA inventes informação
- Se não houver dados suficientes, diz claramente
- Mantém o foco na resposta à pergunta

PERSONALIZAÇÃO (como o {nome} prefere):
{personalidade_instrucoes if personalidade_instrucoes else "- Usa tom neutro e amigável"}
"""
    
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "És um assistente de festas que adapta as respostas à personalidade de cada pessoa."},
            {"role": "user", "content": prompt}
        ],
        "temperature": params["temperature"],
        "max_tokens": params["max_tokens"],
        "top_p": params["top_p"]
    }
    
    try:
        resp = requests.post(GROQ_URL, headers=headers, json=data, timeout=20)
        resposta = resp.json()["choices"][0]["message"]["content"].strip()
        
        # Pós-processamento
        resposta = processar_resposta(resposta, perfil_completo)
        
        return resposta
    except Exception as e:
        print(f"⚠️ Erro: {e}")
        return "Não consegui interpretar os dados 😅"

# =====================================================
# 📍 CÁLCULO DE DISTÂNCIAS
# =====================================================
def estimar_distancia_por_zona(zona: str) -> dict:
    """Estima distância aproximada de Lisboa baseada na zona."""
    distancias = {
        # Portugal
        "lisboa": {"km": 0, "tempo": "0h", "pais": "Portugal"},
        "sintra": {"km": 30, "tempo": "30min", "pais": "Portugal"},
        "cascais": {"km": 30, "tempo": "30min", "pais": "Portugal"},
        "óbidos": {"km": 85, "tempo": "1h", "pais": "Portugal"},
        "obidos": {"km": 85, "tempo": "1h", "pais": "Portugal"},
        "nazaré": {"km": 120, "tempo": "1h20", "pais": "Portugal"},
        "peniche": {"km": 95, "tempo": "1h10", "pais": "Portugal"},
        "torres vedras": {"km": 50, "tempo": "40min", "pais": "Portugal"},
        "lourinhã": {"km": 70, "tempo": "50min", "pais": "Portugal"},
        "mira": {"km": 200, "tempo": "2h", "pais": "Portugal"},
        "coimbra": {"km": 200, "tempo": "2h", "pais": "Portugal"},
        "gouveia": {"km": 310, "tempo": "3h", "pais": "Portugal"},
        "comporta": {"km": 120, "tempo": "1h30", "pais": "Portugal"},
        "alentejo": {"km": 150, "tempo": "1h40", "pais": "Portugal"},
        "monsaraz": {"km": 180, "tempo": "2h", "pais": "Portugal"},
        "reguengos": {"km": 180, "tempo": "2h", "pais": "Portugal"},
        "évora": {"km": 130, "tempo": "1h30", "pais": "Portugal"},
        "evora": {"km": 130, "tempo": "1h30", "pais": "Portugal"},
        "coruche": {"km": 90, "tempo": "1h", "pais": "Portugal"},
        "mora": {"km": 110, "tempo": "1h15", "pais": "Portugal"},
        "arraiolos": {"km": 120, "tempo": "1h20", "pais": "Portugal"},
        "vila viçosa": {"km": 180, "tempo": "2h", "pais": "Portugal"},
        "vila velha de ródão": {"km": 220, "tempo": "2h20", "pais": "Portugal"},
        "porto": {"km": 315, "tempo": "3h", "pais": "Portugal"},
        "viana do castelo": {"km": 390, "tempo": "4h", "pais": "Portugal"},
        "braga": {"km": 360, "tempo": "3h30", "pais": "Portugal"},
        "guimarães": {"km": 370, "tempo": "3h40", "pais": "Portugal"},
        "aveiro": {"km": 255, "tempo": "2h30", "pais": "Portugal"},
        "viseu": {"km": 290, "tempo": "3h", "pais": "Portugal"},
        "guarda": {"km": 330, "tempo": "3h20", "pais": "Portugal"},
        
        # Espanha
        "cáceres": {"km": 300, "tempo": "3h", "pais": "Espanha"},
        "caceres": {"km": 300, "tempo": "3h", "pais": "Espanha"},
        "badajoz": {"km": 230, "tempo": "2h20", "pais": "Espanha"},
        "mérida": {"km": 250, "tempo": "2h30", "pais": "Espanha"},
        "merida": {"km": 250, "tempo": "2h30", "pais": "Espanha"},
        "sevilha": {"km": 440, "tempo": "4h20", "pais": "Espanha"},
        "madrid": {"km": 625, "tempo": "6h", "pais": "Espanha"},
        "salamanca": {"km": 420, "tempo": "4h", "pais": "Espanha"},
    }
    
    zona_norm = normalizar_zona(zona)
    
    for zona_key, info in distancias.items():
        zona_key_norm = normalizar_zona(zona_key)
        if zona_norm in zona_key_norm or zona_key_norm in zona_norm:
            return info
    
    return None

# =====================================================
# 🎯 FUNÇÃO PRINCIPAL - GERAR RESPOSTA LLM (VERSÃO 2.0)
# =====================================================
def gerar_resposta_llm(pergunta, perfil_completo=None, contexto_base=None, contexto_conversa="", ultima_quinta=None):
    """
    Gera resposta sobre festa ou quintas com PERSONALIZAÇÃO COMPLETA.
    
    VERSÃO 2.0 - MELHORIAS:
    ✅ Parâmetros LLM ajustados dinamicamente
    ✅ Pós-processamento inteligente
    ✅ Contexto de conversa melhorado
    ✅ Respostas adaptadas à personalidade
    """
    perfil = perfil_completo or {}
    nome = perfil_completo.get("nome", "Utilizador")
    p = pergunta.lower()
    
    # Parâmetros personalizados
    params = calcular_parametros_llm(perfil_completo)
    
    # Se há contexto da conversa anterior, usa para melhorar a compreensão
    if contexto_conversa:
        try:
            # Converte contexto para string se for lista
            contexto_str = ""
            if isinstance(contexto_conversa, list):
                contexto_str = " ".join([str(msg.get('content', '')) for msg in contexto_conversa if isinstance(msg, dict)])
            elif isinstance(contexto_conversa, str):
                contexto_str = contexto_conversa
            else:
                contexto_str = str(contexto_conversa)
            
            contexto_str_lower = contexto_str.lower()
            
            if "quinta" in contexto_str_lower or "contacta" in contexto_str_lower:
                if p in ["diz-me", "mostra", "quais", "lista", "as quintas", "essas"]:
                    pergunta = "que quintas já contactámos"
                    p = pergunta.lower()
                    print(f"🔄 Contexto aplicado: '{pergunta}'")
        except Exception as e:
            print(f"⚠️ Erro ao processar contexto: {e}")
            # Continua sem usar contexto

    # ✅ CONSULTAS SOBRE QUINTAS
    if e_pergunta_de_quintas(pergunta):
        
        # Detectar se pergunta por quinta específica que não existe
        # Exemplo: "Qual foi a resposta da Quinta do Sol?"
        if any(palavra in p for palavra in ['resposta da', 'resposta de', 'website da', 'website de', 'telefone da', 'telefone de']):
            # Extrair nome da quinta da pergunta
            import re
            match = re.search(r'(?:resposta|website|telefone|email|preço|preco)\s+(?:da|de|do)\s+(.+?)(?:\?|$)', pergunta, re.IGNORECASE)
            if match:
                nome_quinta = match.group(1).strip()
                
                # Buscar no Qdrant se existe
                try:
                    from modules.quintas_qdrant import buscar_quinta_por_nome
                    quinta = buscar_quinta_por_nome(nome_quinta)
                    
                    if quinta:
                        # QUINTA ENCONTRADA! Mostrar info
                        nome = quinta.get('nome', 'N/A')
                        resposta_quinta = quinta.get('resposta', '')
                        
                        resposta = f"🏡 **{nome}**\n\n"
                        
                        # Resposta do email
                        if resposta_quinta and resposta_quinta not in ['', 'Sem resposta', 'Erro email', None]:
                            resposta += f"📧 **Resposta:** {resposta_quinta}\n\n"
                        else:
                            resposta += f"⏳ **Resposta:** Ainda não responderam\n\n"
                        
                        # Outras informações disponíveis
                        if quinta.get('zona'):
                            resposta += f"📍 Zona: {quinta['zona']}\n"
                        if quinta.get('website'):
                            resposta += f"🌐 Website: {quinta['website']}\n"
                        if quinta.get('telefone'):
                            resposta += f"📞 Telefone: {quinta['telefone']}\n"
                        if quinta.get('email'):
                            resposta += f"✉️ Email: {quinta['email']}\n"
                        if quinta.get('preco_estimado'):
                            resposta += f"💰 Preço estimado: €{quinta['preco_estimado']}\n"
                        
                        return processar_resposta(resposta, perfil_completo)
                    
                    else:
                        # Quinta não encontrada - tentar busca aproximada
                        from modules.quintas_qdrant import listar_quintas
                        quintas = listar_quintas()
                        
                        # Busca aproximada por palavras-chave
                        palavras_busca = nome_quinta.lower().split()
                        candidatos = []
                        
                        for q in quintas:
                            nome_q = q.get('nome', '').lower()
                            # Conta quantas palavras coincidem
                            matches = sum(1 for palavra in palavras_busca if palavra in nome_q)
                            if matches > 0:
                                candidatos.append((q, matches))
                        
                        # Ordena por número de matches (descendente)
                        candidatos.sort(key=lambda x: x[1], reverse=True)
                        
                        if candidatos and candidatos[0][1] >= 2:  # Pelo menos 2 palavras em comum
                            # Sugerir a quinta mais próxima
                            quinta_sugerida = candidatos[0][0]
                            resposta = f"🤔 Não encontrei **{nome_quinta}** exatamente.\n\n"
                            resposta += f"Estavas-te a referir a **{quinta_sugerida.get('nome', 'N/A')}**?\n\n"
                            
                            # Mostrar info da quinta sugerida
                            resposta_q = quinta_sugerida.get('resposta', '')
                            if resposta_q and resposta_q not in ['', 'Sem resposta', 'Erro email', None]:
                                resposta += f"📧 **Resposta:** {resposta_q}\n"
                            else:
                                resposta += f"⏳ **Resposta:** Ainda não responderam\n"
                            
                            if quinta_sugerida.get('zona'):
                                resposta += f"📍 Zona: {quinta_sugerida['zona']}\n"
                            
                            return processar_resposta(resposta, perfil_completo)
                        
                        # Não encontrou nada próximo - mostrar lista
                        resposta = f"🤔 Não encontrei **{nome_quinta}** na nossa lista de quintas contactadas.\n\n"
                        resposta += f"📋 **Quintas que já contactámos** ({len(quintas)}):\n\n"
                        
                        # Agrupar por zona
                        zonas = {}
                        for q in quintas[:20]:  # Limitar a 20
                            zona = q.get('zona', 'Sem zona')
                            if zona not in zonas:
                                zonas[zona] = []
                            zonas[zona].append(q.get('nome', 'Sem nome'))
                        
                        for zona, nomes in sorted(zonas.items())[:5]:  # Top 5 zonas
                            resposta += f"**{zona}** ({len(nomes)}):\n"
                            for nome in nomes[:3]:  # Max 3 por zona
                                resposta += f"• {nome}\n"
                            if len(nomes) > 3:
                                resposta += f"• ... e mais {len(nomes)-3}\n"
                            resposta += "\n"
                        
                        return processar_resposta(resposta, perfil_completo)
                except Exception as e:
                    print(f"⚠️ Erro na busca de quinta: {e}")
                    pass  # Se falhar, continua com lógica normal
        
        if e_pergunta_estado(pergunta):
            nota = procurar_resposta_semelhante(pergunta, contexto="quintas")
            if nota:
                return processar_resposta(nota, perfil_completo)
            
            sql = "SELECT COUNT(*) as total FROM quintas WHERE resposta IS NOT NULL"
            dados = executar_sql(sql)
            if dados and len(dados) > 0 and dados[0].get('total'):
                resposta = "Já contactámos várias quintas mas ainda estamos a aguardar respostas! 📞"
                return processar_resposta(resposta, perfil_completo)
            return processar_resposta("Ainda não há quinta fechada, mas já contactámos várias!", perfil_completo)
        else:
            # PERGUNTAS SOBRE DISTÂNCIA
            if any(t in p for t in ["distancia", "distância", "quilometros", "quilómetros", "km", "longe", "perto"]):
                if ultima_quinta:
                    nome_quinta = ultima_quinta.get("nome", "")
                    zona_quinta = ultima_quinta.get("zona", "")
                    
                    print(f"📍 Calculando distância de {nome_quinta} ({zona_quinta})")
                    
                    distancia_info = estimar_distancia_por_zona(zona_quinta)
                    
                    if distancia_info:
                        km = distancia_info["km"]
                        tempo = distancia_info["tempo"]
                        pais = distancia_info.get("pais", "")
                        
                        if km == 0:
                            resposta = f"**{nome_quinta}** fica em Lisboa! 🏙️"
                        else:
                            resposta = f"**{nome_quinta}** ({zona_quinta}) fica a aproximadamente:\n\n"
                            resposta += f"📏 **{km} km** de Lisboa\n"
                            resposta += f"🚗 Cerca de **{tempo}** de carro"
                            if pais and pais != "Portugal":
                                resposta += f"\n🌍 Localização: {pais}"
                        
                        return processar_resposta(resposta, perfil_completo)
                    else:
                        resposta = f"Não tenho info exata da distância de {nome_quinta} ({zona_quinta}) 😅\n\nMas podes ver no Google Maps!"
                        return processar_resposta(resposta, perfil_completo)
                else:
                    resposta = "De que quinta queres saber a distância? 😊"
                    return processar_resposta(resposta, perfil_completo)
            
            # QUINTAS ESPECÍFICAS POR NOME
            if any(t in p for t in ["website", "link", "site", "endereco", "endereço", "morada", "contacto", "email", "telefone"]):
                nome_busca = pergunta
                nome_busca = re.sub(r'^(manda-me|manda|envia|qual|me|o|a)\s+', '', nome_busca, flags=re.IGNORECASE)
                nome_busca = re.sub(r'\b(website|link|site|morada|contacto|email|telefone)\b', '', nome_busca, flags=re.IGNORECASE)
                nome_busca = re.sub(r'^(da|do|de|desta|deste)\s+', '', nome_busca, flags=re.IGNORECASE)
                nome_busca = re.sub(r'[?!.,;:]', '', nome_busca).strip()
                
                if nome_busca and len(nome_busca) > 3:
                    palavras = nome_busca.split()
                    if len(palavras) >= 2:
                        palavras_principais = [p for p in palavras if len(p) > 2]
                        condicoes = " OR ".join([f"LOWER(nome) LIKE '%{p.lower()}%'" for p in palavras_principais[:3]])
                        sql = f"SELECT nome, zona, morada, website, email, telefone FROM quintas WHERE {condicoes} LIMIT 3"
                    else:
                        sql = f"SELECT nome, zona, morada, website, email, telefone FROM quintas WHERE LOWER(nome) LIKE '%{nome_busca.lower()}%' LIMIT 1"
                    
                    dados = executar_sql(sql)
                    if dados:
                        if len(dados) > 1:
                            nomes = "\n".join([f"• {d['nome']} ({d.get('zona', 'n/d')})" for d in dados])
                            resposta = f"Encontrei {len(dados)} quintas:\n{nomes}\n\nQual delas?"
                            return processar_resposta(resposta, perfil_completo)
                        
                        quinta = dados[0]
                        info = [f"📍 {quinta['nome']} ({quinta.get('zona', 'n/d')})"]
                        
                        if "website" in p or "link" in p:
                            if quinta.get('website'):
                                info.append(f"🌐 {quinta['website']}")
                            else:
                                info.append("⚠️ Website não disponível")
                        if "morada" in p or "endereco" in p:
                            if quinta.get('morada'):
                                info.append(f"📍 {quinta['morada']}")
                        if "email" in p:
                            if quinta.get('email'):
                                info.append(f"📧 {quinta['email']}")
                        if "telefone" in p:
                            if quinta.get('telefone'):
                                info.append(f"📞 {quinta['telefone']}")
                        
                        if len(info) == 1:
                            if quinta.get('website'): info.append(f"🌐 {quinta['website']}")
                            if quinta.get('morada'): info.append(f"📍 {quinta['morada']}")
                        
                        resposta = "\n".join(info)
                        return processar_resposta(resposta, perfil_completo)
                    
                    resposta = f"Não encontrei '{nome_busca}' 😅"
                    return processar_resposta(resposta, perfil_completo)
            
            # QUANTAS QUINTAS
            if "quantas" in p and "zona" not in p and "responderam" not in p:
                sql = "SELECT COUNT(*) as total FROM quintas"
                dados = executar_sql(sql)
                if dados:
                    resposta = f"Já contactámos {dados[0]['total']} quintas 📊"
                    return processar_resposta(resposta, perfil_completo)
            
            # RESPONDERAM
            if "responderam" in p or "respondeu" in p:
                sql = "SELECT COUNT(*) as total FROM quintas WHERE resposta IS NOT NULL AND resposta != ''"
                dados = executar_sql(sql)
                if dados and dados[0]['total'] > 0:
                    sql2 = "SELECT nome, zona FROM quintas WHERE resposta IS NOT NULL LIMIT 5"
                    quintas = executar_sql(sql2)
                    nomes = "\n".join([f"• {q['nome']}" for q in quintas])
                    resposta = f"Sim! {dados[0]['total']} quintas responderam:\n{nomes}"
                    return processar_resposta(resposta, perfil_completo)
                resposta = "Ainda não tivemos respostas 😅"
                return processar_resposta(resposta, perfil_completo)
            
            # CAPACIDADE
            if "capacidade" in p or "pessoas" in p:
                sql = "SELECT COUNT(*) as total FROM quintas WHERE capacidade_43 LIKE '%sim%'"
                dados = executar_sql(sql)
                if dados and len(dados) > 0 and dados[0].get('total', 0) > 0:
                    resposta = f"Temos {dados[0]['total']} quintas com capacidade para 43 pessoas!"
                    return processar_resposta(resposta, perfil_completo)
                resposta = "Ainda não temos confirmação de capacidade 😅"
                return processar_resposta(resposta, perfil_completo)
            
            # QUE QUINTAS / LISTA
            if "que quintas" in p or "lista" in p or "ja vimos" in p:
                sql = "SELECT nome, zona FROM quintas LIMIT 8"
                dados = executar_sql(sql)
                if dados:
                    nomes = "\n".join([f"• {d['nome']} ({d['zona']})" for d in dados])
                    sql2 = "SELECT COUNT(*) as total FROM quintas"
                    total = executar_sql(sql2)
                    t = total[0]['total'] if total else len(dados)
                    resposta = f"Já contactámos {t} quintas:\n{nomes}\n{'...e mais!' if t > 8 else ''}"
                    return processar_resposta(resposta, perfil_completo)
            
            # ZONAS
            if "zona" in p and "que" in p:
                sql = "SELECT zona, COUNT(*) as total FROM quintas WHERE zona IS NOT NULL GROUP BY zona ORDER BY total DESC LIMIT 10"
                dados = executar_sql(sql)
                if dados:
                    zonas = ", ".join([f"{d['zona']} ({d['total']})" for d in dados])
                    resposta = f"Zonas: {zonas}"
                    return processar_resposta(resposta, perfil_completo)
            
            # BUSCA POR ZONA
            if "em " in p or re.search(r'[A-Z][a-z]+\?', pergunta):
                zona_busca = re.sub(r'\b(em|zona|quintas|quais)\b', '', p, flags=re.IGNORECASE)
                zona_busca = re.sub(r'[?!.,;:]', '', zona_busca).strip()
                if zona_busca and len(zona_busca) > 2:
                    zona_norm = normalizar_zona(zona_busca)
                    sql = f"SELECT nome, zona FROM quintas WHERE LOWER(REPLACE(REPLACE(zona, 'ã', 'a'), 'ñ', 'n')) LIKE '%{zona_norm}%' LIMIT 5"
                    dados = executar_sql(sql)
                    if dados:
                        nomes = "\n".join([f"• {d['nome']}" for d in dados])
                        resposta = f"Quintas em {dados[0]['zona']} ({len(dados)}):\n{nomes}"
                        return processar_resposta(resposta, perfil_completo)
                    resposta = f"Não encontrei quintas em '{zona_busca}' 😅"
                    return processar_resposta(resposta, perfil_completo)
            
            # FALLBACK SQL
            sql = gerar_sql_da_pergunta(pergunta, perfil_completo)
            if sql:
                dados = executar_sql(sql)
                if dados:
                    return gerar_resposta_dados_llm(pergunta, dados, perfil_completo)
            
            resposta = "Não consegui interpretar 😅"
            return processar_resposta(resposta, perfil_completo)

    # ✅ FESTA (ou perguntas fora do contexto)
    if not contexto_base:
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                contexto_base = json.load(f)
        except:
            contexto_base = {}

    # Se não for sobre quintas, usa o LLM para responder com personalidade
    perguntas_casuais = ["porque", "porquê", "como", "quando", "será", "achas", "pensas", "dirias"]
    if any(palavra in pergunta.lower() for palavra in perguntas_casuais):
        # Instruções de personalidade
        personalidade_instrucoes = construir_personalidade_prompt(perfil_completo)
        
        prompt = f"""
És um assistente simpático da festa de passagem de ano.
Responde de forma natural em Português de Portugal.

Se a pergunta for pessoal ou fora do tema da festa, responde mas mantém o foco na festa.

PERGUNTA: {pergunta}

PERSONALIZAÇÃO (como o {nome} prefere):
{personalidade_instrucoes if personalidade_instrucoes else "- Usa tom neutro e amigável"}
"""
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        
        data = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "És um assistente de festas que adapta as respostas à personalidade de cada pessoa."},
                {"role": "user", "content": prompt}
            ],
            "temperature": params["temperature"],
            "max_tokens": params["max_tokens"],
            "top_p": params["top_p"]
        }
        
        try:
            resp = requests.post(GROQ_URL, headers=headers, json=data, timeout=20)
            resposta = resp.json()["choices"][0]["message"]["content"].strip()
            
            # Pós-processamento
            resposta = processar_resposta(resposta, perfil_completo)
            
            return resposta
        except Exception as e:
            print(f"❌ Erro ao gerar resposta: {e}")
            pass
    
    resposta = "Ainda estamos a organizar os detalhes 🎆 Pergunta-me sobre as quintas!"
    return processar_resposta(resposta, perfil_completo)


# =====================================================
# 🧪 TESTES (executar diretamente)
# =====================================================
if __name__ == "__main__":
    print("=" * 60)
    print("🧪 TESTE DE PERSONALIZAÇÃO DO LLM")
    print("=" * 60)
    
    # Perfis de teste
    perfil_humorado = {
        "nome": "João",
        "personalidade": {
            "humor": 9,
            "emojis": 8,
            "detalhismo": 7,
            "formalidade": 3,
            "paciencia": 8
        }
    }
    
    perfil_serio = {
        "nome": "Dr. Silva",
        "personalidade": {
            "humor": 2,
            "emojis": 1,
            "detalhismo": 8,
            "formalidade": 9,
            "paciencia": 5
        }
    }
    
    print("\n1️⃣ TESTE: Perfil Humorado")
    print("-" * 60)
    params1 = calcular_parametros_llm(perfil_humorado)
    print(f"Parâmetros: {params1}")
    prompt1 = construir_personalidade_prompt(perfil_humorado)
    print(f"Prompt:\n{prompt1}")
    
    print("\n2️⃣ TESTE: Perfil Sério")
    print("-" * 60)
    params2 = calcular_parametros_llm(perfil_serio)
    print(f"Parâmetros: {params2}")
    prompt2 = construir_personalidade_prompt(perfil_serio)
    print(f"Prompt:\n{prompt2}")
    
    print("\n✅ Testes concluídos!")