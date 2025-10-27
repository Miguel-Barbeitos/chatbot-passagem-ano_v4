# llm_groq.py
import os
import json
import requests
import sqlite3
import pandas as pd
import streamlit as st
import re

from learning_qdrant import procurar_resposta_semelhante

# =====================================================
# ⚙️ CONFIGURAÇÃO GERAL
# =====================================================
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))
if not GROQ_API_KEY:
    raise ValueError("❌ Falta a variável de ambiente GROQ_API_KEY.")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"
DATA_PATH = "data/event.json"

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
# 🤖 GERAR SQL
# =====================================================
def gerar_sql_da_pergunta(pergunta: str) -> str:
    """Usa o LLM para gerar um SQL seguro (apenas SELECT)."""
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
    """Executa um SELECT no SQLite."""
    try:
        conn = sqlite3.connect("data/quintas.db")
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"⚠️ Erro ao executar SQL: {e}")
        return []

# =====================================================
# 💬 GERAR RESPOSTA NATURAL
# =====================================================
def gerar_resposta_dados_llm(pergunta, dados):
    """Transforma dados SQL em texto natural."""
    json_data = json.dumps(dados, ensure_ascii=False, indent=2)
    
    prompt = f"""
Transforma estes dados JSON numa resposta breve e natural.

REGRAS:
- USA APENAS OS DADOS FORNECIDOS
- Responde em Português de Portugal
- Máximo 3 frases
- Se não houver info, diz claramente

Pergunta: "{pergunta}"
Dados: {json_data}
"""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Transforma dados em respostas naturais. NUNCA inventes informação."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 200
    }
    try:
        resp = requests.post(GROQ_URL, headers=headers, json=data, timeout=20)
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"⚠️ Erro: {e}")
        return "Não consegui interpretar os dados 😅"

# =====================================================
# 📍 CÁLCULO DE DISTÂNCIAS
# =====================================================
def estimar_distancia_por_zona(zona: str) -> dict:
    """Estima distância aproximada de Lisboa baseada na zona."""
    # Distâncias aproximadas de Lisboa (em km e tempo)
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
        
        # Norte de Portugal
        "porto": {"km": 315, "tempo": "3h", "pais": "Portugal"},
        "viana do castelo": {"km": 390, "tempo": "4h", "pais": "Portugal"},
        "valença": {"km": 440, "tempo": "4h30", "pais": "Portugal"},
        "esposende": {"km": 360, "tempo": "3h40", "pais": "Portugal"},
        "vila praia de âncora": {"km": 420, "tempo": "4h20", "pais": "Portugal"},
        
        # Espanha
        "cáceres": {"km": 300, "tempo": "3h", "pais": "Espanha"},
        "badajoz": {"km": 230, "tempo": "2h30", "pais": "Espanha"},
        "salamanca": {"km": 390, "tempo": "4h", "pais": "Espanha"},
        "coruña": {"km": 600, "tempo": "6h", "pais": "Espanha (Galiza)"},
        "santiago": {"km": 610, "tempo": "6h", "pais": "Espanha (Galiza)"},
        "pontevedra": {"km": 570, "tempo": "5h30", "pais": "Espanha (Galiza)"},
        "lugo": {"km": 650, "tempo": "6h30", "pais": "Espanha (Galiza)"},
    }
    
    zona_norm = normalizar_zona(zona)
    
    # Procura correspondência exata ou parcial
    for chave, dados in distancias.items():
        if zona_norm in chave or chave in zona_norm:
            return dados
    
    # Se não encontrar, tenta pelo país na zona
    if "es)" in zona.lower() or "espanha" in zona.lower() or "españa" in zona.lower():
        return {"km": 300, "tempo": "~3h", "pais": "Espanha (estimativa)"}
    
    return None

# =====================================================
# 🎆 GERAÇÃO DE RESPOSTAS
# =====================================================
def gerar_resposta_llm(pergunta, perfil=None, contexto_base=None, contexto_conversa="", ultima_quinta=None):
    """Gera resposta sobre festa ou quintas."""
    perfil = perfil or {}
    nome = perfil.get("nome", "Utilizador")
    p = pergunta.lower()
    
    # Se há contexto da conversa anterior, usa para melhorar a compreensão
    if contexto_conversa:
        # Verifica se a resposta anterior mencionou quintas e a pergunta atual é vaga
        if "quinta" in contexto_conversa.lower() or "contacta" in contexto_conversa.lower():
            if p in ["diz-me", "mostra", "quais", "lista", "as quintas", "essas"]:
                # Reformula a pergunta com contexto
                pergunta = "que quintas já contactámos"
                p = pergunta.lower()
                print(f"🔄 Contexto aplicado: '{pergunta}'")

    # ✅ CONSULTAS SOBRE QUINTAS
    if e_pergunta_de_quintas(pergunta):
        if e_pergunta_estado(pergunta):
            nota = procurar_resposta_semelhante(pergunta, contexto="quintas")
            if nota:
                return nota
            sql = "SELECT COUNT(*) as total FROM quintas WHERE resposta IS NOT NULL"
            dados = executar_sql(sql)
            if dados and dados[0].get('total'):
                return "Já contactámos várias quintas mas ainda estamos a aguardar respostas! 📞"
            return "Ainda não há quinta fechada, mas já contactámos várias!"
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
                            return f"**{nome_quinta}** fica em Lisboa! 🏙️"
                        else:
                            resposta = f"**{nome_quinta}** ({zona_quinta}) fica a aproximadamente:\n\n"
                            resposta += f"📏 **{km} km** de Lisboa\n"
                            resposta += f"🚗 Cerca de **{tempo}** de carro"
                            if pais and pais != "Portugal":
                                resposta += f"\n🌍 Localização: {pais}"
                            return resposta
                    else:
                        return f"Não tenho info exata da distância de {nome_quinta} ({zona_quinta}) 😅\n\nMas podes ver no Google Maps!"
                else:
                    return "De que quinta queres saber a distância? 😊"
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
                            return f"Encontrei {len(dados)} quintas:\n{nomes}\n\nQual delas?"
                        
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
                        
                        return "\n".join(info)
                    return f"Não encontrei '{nome_busca}' 😅"
            
            # QUANTAS QUINTAS
            if "quantas" in p and "zona" not in p and "responderam" not in p:
                sql = "SELECT COUNT(*) as total FROM quintas"
                dados = executar_sql(sql)
                if dados:
                    return f"Já contactámos {dados[0]['total']} quintas 📊"
            
            # RESPONDERAM
            if "responderam" in p or "respondeu" in p:
                sql = "SELECT COUNT(*) as total FROM quintas WHERE resposta IS NOT NULL AND resposta != ''"
                dados = executar_sql(sql)
                if dados and dados[0]['total'] > 0:
                    sql2 = "SELECT nome, zona FROM quintas WHERE resposta IS NOT NULL LIMIT 5"
                    quintas = executar_sql(sql2)
                    nomes = "\n".join([f"• {q['nome']}" for q in quintas])
                    return f"Sim! {dados[0]['total']} quintas responderam:\n{nomes}"
                return "Ainda não tivemos respostas 😅"
            
            # CAPACIDADE
            if "capacidade" in p or "pessoas" in p:
                sql = "SELECT COUNT(*) as total FROM quintas WHERE capacidade_43 LIKE '%sim%'"
                dados = executar_sql(sql)
                if dados and dados[0]['total'] > 0:
                    return f"Temos {dados[0]['total']} quintas com capacidade para 43 pessoas!"
                return "Ainda não temos confirmação de capacidade 😅"
            
            # QUE QUINTAS / LISTA
            if "que quintas" in p or "lista" in p or "ja vimos" in p:
                sql = "SELECT nome, zona FROM quintas LIMIT 8"
                dados = executar_sql(sql)
                if dados:
                    nomes = "\n".join([f"• {d['nome']} ({d['zona']})" for d in dados])
                    sql2 = "SELECT COUNT(*) as total FROM quintas"
                    total = executar_sql(sql2)
                    t = total[0]['total'] if total else len(dados)
                    return f"Já contactámos {t} quintas:\n{nomes}\n{'...e mais!' if t > 8 else ''}"
            
            # ZONAS
            if "zona" in p and "que" in p:
                sql = "SELECT zona, COUNT(*) as total FROM quintas WHERE zona IS NOT NULL GROUP BY zona ORDER BY total DESC LIMIT 10"
                dados = executar_sql(sql)
                if dados:
                    zonas = ", ".join([f"{d['zona']} ({d['total']})" for d in dados])
                    return f"Zonas: {zonas}"
            
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
                        return f"Quintas em {dados[0]['zona']} ({len(dados)}):\n{nomes}"
                    return f"Não encontrei quintas em '{zona_busca}' 😅"
            
            # FALLBACK SQL
            sql = gerar_sql_da_pergunta(pergunta)
            if sql:
                dados = executar_sql(sql)
                if dados:
                    return gerar_resposta_dados_llm(pergunta, dados)
            return "Não consegui interpretar 😅"

    # ✅ FESTA (ou perguntas fora do contexto)
    if not contexto_base:
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                contexto_base = json.load(f)
        except:
            contexto_base = {}

    # Se não for sobre quintas, usa o LLM para responder com personalidade
    if not contexto_base.get("nome_local"):
        # Verifica se é pergunta casual/pessoal
        perguntas_casuais = ["porque", "porquê", "como", "quando", "será", "achas", "pensas", "dirias"]
        if any(p in pergunta.lower() for p in perguntas_casuais):
            prompt = f"""
És um assistente simpático e divertido da festa de passagem de ano.
Responde de forma breve (1-2 frases), com humor leve e português de Portugal.

Se a pergunta for pessoal ou fora do tema da festa, responde com humor mas mantém o foco na festa.

Pergunta: {pergunta}

Lembra-te:
- Mantém o humor leve
- Redireciona para a festa se apropriado
- Máximo 2 frases
"""
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            data = {
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": "És um assistente divertido de festas que responde com humor português."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.8,
                "max_tokens": 100
            }
            try:
                resp = requests.post(GROQ_URL, headers=headers, json=data, timeout=20)
                return resp.json()["choices"][0]["message"]["content"].strip()
            except:
                pass
        
        return "Ainda estamos a organizar os detalhes 🎆 Pergunta-me sobre as quintas!"

    return "Estamos a organizar a festa! Pergunta-me sobre as quintas 😊"