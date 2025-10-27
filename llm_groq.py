# llm_groq.py
import os
import json
import requests
import sqlite3
import pandas as pd
import streamlit as st

from learning_qdrant import procurar_resposta_semelhante

# =====================================================
# ⚙️ CONFIGURAÇÃO GERAL
# =====================================================
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))
if not GROQ_API_KEY:
    raise ValueError("❌ Falta a variável de ambiente GROQ_API_KEY. Define-a no Streamlit secrets ou no ambiente local.")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

DATA_PATH = "data/event.json"

# =====================================================
# 📂 LEITURA DO CONTEXTO BASE (event.json)
# =====================================================
def carregar_contexto_base():
    """Lê o contexto base do JSON da festa"""
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            dados = json.load(f)
        contexto = []
        for k, v in dados.items():
            if isinstance(v, bool):
                contexto.append(f"{k.replace('_', ' ')}: {'sim' if v else 'não'}")
            elif isinstance(v, list):
                contexto.append(f"{k.replace('_', ' ')}: {', '.join(v)}")
            elif isinstance(v, dict):
                sub = ", ".join(f"{sk}: {sv}" for sk, sv in v.items())
                contexto.append(f"{k}: {sub}")
            else:
                contexto.append(f"{k.replace('_', ' ')}: {v}")
        return "\n".join(contexto)
    except Exception as e:
        print(f"⚠️ Erro ao carregar contexto base: {e}")
        return "Informações da festa indisponíveis."

# =====================================================
# 🔍 DETEÇÃO DE PERGUNTAS SOBRE QUINTAS (MELHORADA)
# =====================================================
def e_pergunta_de_quintas(pergunta: str) -> bool:
    """Deteta se a pergunta é sobre quintas / base de dados."""
    p = pergunta.lower()
    chaves = [
        # Perguntas diretas
        "quinta", "quintas", "que quintas", "quais quintas", "quantas quintas",
        # Estado e contactos
        "contactadas", "contactaste", "responderam", "falamos", "vimos",
        # Características
        "piscina", "capacidade", "custo", "barata", "animais", "resposta", 
        "zona", "morada", "opcoes", "opções", "disponivel", "disponível",
        "preco", "preço", "churrasqueira", "snooker", "estado", "procura",
        # Quantificadores
        "quantas", "quais", "lista", "nomes"
    ]
    return any(c in p for c in chaves)

def e_pergunta_estado(pergunta: str) -> bool:
    """Deteta perguntas sobre o estado das quintas (porquê, resposta, atualização)."""
    termos = ["porquê", "porque", "motivo", "estado", "respondeu", "atualização", 
              "contactaste", "falaste", "ja vimos", "já vimos", "progresso"]
    return any(t in pergunta.lower() for t in termos)

# =====================================================
# 🤖 GERAR SQL AUTOMATICAMENTE
# =====================================================
def gerar_sql_da_pergunta(pergunta: str) -> str:
    """Usa o LLM para gerar um SQL seguro (apenas SELECT)."""
    schema = """
    Tabela: quintas
    Colunas: nome, zona, morada, email, telefone, website, estado, resposta,
    capacidade_43, custo_4500, estimativa_custo, capacidade_confirmada,
    ultima_resposta, proposta_tarifaria, unidades_detalhe, num_unidades,
    observacao_unidades, custo_total, resumo_resposta, observacoes, notas_calculo.
    
    Nota: A coluna 'estado' contém valores como 'Contactada', 'Aguarda resposta', 'Respondeu', etc.
    """

    prompt_sql = f"""
Gera apenas o SQL (SELECT ...) para responder à pergunta do utilizador.
O SQL deve ser simples, compatível com SQLite e usar apenas as colunas listadas.
Pergunta: "{pergunta}"
{schema}

Exemplos de perguntas e SQL:
- "Quantas quintas já contactámos?" → SELECT COUNT(*) as total FROM quintas
- "Que quintas já contactámos?" ou "Quais quintas?" → SELECT nome, zona, morada FROM quintas LIMIT 20
- "Quantas quintas já vimos?" → SELECT COUNT(*) as total FROM quintas
- "Lista de quintas" → SELECT nome, zona FROM quintas LIMIT 20
- "Quais quintas têm piscina?" → SELECT nome, zona FROM quintas WHERE tem_piscina = 1
- "Quintas mais baratas" → SELECT nome, zona, custo_4500 FROM quintas ORDER BY custo_4500 ASC LIMIT 5
- "Quintas na zona de Lisboa" → SELECT nome, morada FROM quintas WHERE zona LIKE '%Lisboa%'

IMPORTANTE: Para perguntas genéricas como "que quintas" ou "quantas", retorna TODAS as quintas (ou o COUNT).
"""

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "És um assistente que converte linguagem natural em SQL seguro (apenas SELECT)."},
            {"role": "user", "content": prompt_sql},
        ],
        "temperature": 0.0,
        "max_tokens": 150,
    }

    try:
        resp = requests.post(GROQ_URL, headers=headers, json=data, timeout=20)
        query = resp.json()["choices"][0]["message"]["content"].strip()
        # Remove markdown se existir
        if "```sql" in query:
            query = query.split("```sql")[1].split("```")[0].strip()
        elif "```" in query:
            query = query.split("```")[1].split("```")[0].strip()
        
        if query.lower().startswith("select"):
            return query
    except Exception as e:
        print(f"⚠️ Erro a gerar SQL: {e}")
    return None

# =====================================================
# 🧠 EXECUTAR SQL NO SQLITE
# =====================================================
def executar_sql(query: str):
    """Executa um SELECT no SQLite e devolve os resultados como lista de dicionários."""
    try:
        conn = sqlite3.connect("data/quintas.db")
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"⚠️ Erro ao executar SQL: {e}")
        return []

# =====================================================
# 💬 GERAR RESPOSTA NATURAL A PARTIR DOS DADOS
# =====================================================
def gerar_resposta_dados_llm(pergunta, dados):
    """Usa o LLM para transformar os resultados do SQL em texto natural."""
    json_data = json.dumps(dados, ensure_ascii=False, indent=2)
    
    prompt = f"""
Transforma estes dados JSON numa resposta breve e natural à pergunta "{pergunta}".

⚠️ REGRAS CRÍTICAS:
- USA APENAS OS DADOS FORNECIDOS - NUNCA inventes informação
- Se os dados estiverem vazios ou incompletos, diz isso claramente
- Responde em Português de Portugal, num tom simpático e direto
- Máximo 3 frases
- Se forem muitos resultados, menciona os 3-4 mais relevantes
- Inclui detalhes importantes (zona, preço, capacidade) quando relevante
- Lembra que ainda não há quinta fechada, mas já há várias opções
- Se perguntarem por características que não existem nos dados (como "Porto"), menciona que não há ou que são poucas

Dados fornecidos:
{json_data}

IMPORTANTE: Se os dados não tiverem a informação pedida, diz "Não encontrei essa informação específica" em vez de inventar.
"""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "És um assistente que transforma dados estruturados em respostas naturais. NUNCA inventes informação que não está nos dados fornecidos."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,  # Reduzido para ser mais factual
        "max_tokens": 200,
    }
    try:
        resp = requests.post(GROQ_URL, headers=headers, json=data, timeout=20)
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"⚠️ Erro a gerar resposta natural: {e}")
        return "Não consegui interpretar os dados agora 😅"

# =====================================================
# 🎆 GERAÇÃO DE RESPOSTAS NATURAIS (FESTA OU QUINTAS)
# =====================================================
def gerar_resposta_llm(pergunta, perfil=None, contexto_base=None):
    """
    Gera uma resposta contextual:
    - sobre a festa (usa event.json)
    - ou sobre as quintas (usa SQLite ou Qdrant)
    """
    perfil = perfil or {}
    nome = perfil.get("nome", "Utilizador")
    personalidade = perfil.get("personalidade", "neutro")

    # ✅ 1 — Consultas sobre quintas (base SQLite ou Qdrant)
    if e_pergunta_de_quintas(pergunta):
        if e_pergunta_estado(pergunta):
            # Perguntas tipo "porquê", "respondeu", "estado"
            nota = procurar_resposta_semelhante(pergunta, contexto="quintas")
            if nota:
                return nota
            else:
                # Fallback: tenta consultar a base de dados
                sql = "SELECT COUNT(*) as total, SUM(CASE WHEN estado LIKE '%Respondeu%' THEN 1 ELSE 0 END) as respondidas FROM quintas"
                dados = executar_sql(sql)
                if dados and dados[0].get('total'):
                    total = dados[0]['total']
                    resp = dados[0]['respondidas']
                    return (
                        f"Já contactámos {total} quintas e temos {resp} respostas 📞 "
                        f"Temos o Monte da Galega reservado como backup! Pergunta sobre alguma específica 😊"
                    )
                return "Ainda não há quinta fechada, mas já contactámos várias! Temos o Monte da Galega como plano B 😉"
        else:
            # ✅ PERGUNTAS SIMPLES - SQL direto sem LLM
            p = pergunta.lower()
            
            # "quantas quintas?"
            if any(t in p for t in ["quantas", "quantas quintas", "numero", "número", "total"]):
                sql = "SELECT COUNT(*) as total FROM quintas"
                dados = executar_sql(sql)
                if dados and dados[0].get('total'):
                    total = dados[0]['total']
                    return f"Já contactámos {total} quintas no total 📊 Pergunta-me sobre zonas, preços ou características específicas!"
                return "Ainda não temos quintas na base de dados 😅"
            
            # "que quintas?" / "lista de quintas"
            if any(t in p for t in ["que quintas", "quais quintas", "lista", "nomes das quintas"]):
                sql = "SELECT nome, zona, morada FROM quintas LIMIT 10"
                dados = executar_sql(sql)
                if dados:
                    nomes = [f"**{d['nome']}** ({d.get('zona', 'zona n/d')})" for d in dados[:5]]
                    total_sql = "SELECT COUNT(*) as total FROM quintas"
                    total_dados = executar_sql(total_sql)
                    total = total_dados[0]['total'] if total_dados else len(dados)
                    
                    resposta = f"Já contactámos {total} quintas. Aqui estão algumas:\n\n"
                    resposta += "\n".join(f"• {n}" for n in nomes)
                    if total > 5:
                        resposta += f"\n\n...e mais {total - 5} quintas! Pergunta-me sobre zonas ou características específicas 😊"
                    return resposta
                return "Ainda não temos quintas contactadas 😅"
            
            # Perguntas complexas → usar SQLite + LLM
            sql = gerar_sql_da_pergunta(pergunta)
            if sql:
                print(f"📊 SQL gerado: {sql}")
                dados = executar_sql(sql)
                if dados:
                    # ✅ VALIDAÇÃO: só usar LLM se houver dados reais
                    if len(dados) == 0:
                        return "Não encontrei nenhuma quinta que corresponda a isso 😅 Tenta outra pergunta!"
                    
                    # Verifica se tem campos válidos (não vazios ou None)
                    campos_validos = any(
                        v is not None and v != "" and v != 0 
                        for d in dados 
                        for v in d.values()
                    )
                    
                    if not campos_validos:
                        return "Não encontrei informação específica sobre isso 😅 Tenta reformular!"
                    
                    return gerar_resposta_dados_llm(pergunta, dados)
                else:
                    return "Não encontrei nenhuma quinta que corresponda a isso 😅 Tenta outra pergunta!"
            else:
                return "Não consegui interpretar bem a tua pergunta sobre as quintas 😅 Tenta reformular?"

    # ✅ 2 — Caso contrário, responde sobre a festa
    if not contexto_base:
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                contexto_base = json.load(f)
        except Exception:
            contexto_base = {}

    # Verifica se o event.json tem dados válidos
    if not contexto_base or not contexto_base.get("nome_local"):
        return (
            "Ainda estamos a organizar os detalhes da festa 🎆 "
            "Já temos o Monte da Galega reservado como backup, mas estamos a ver outras opções! "
            "Pergunta-me sobre as quintas que já contactámos 😊"
        )

    coords = contexto_base.get("coordenadas", {})
    latitude = coords.get("latitude", "desconhecida")
    longitude = coords.get("longitude", "desconhecida")

    contexto_texto = (
        f"📍 Local: {contexto_base.get('nome_local', 'ainda a definir')}\n"
        f"🏠 Morada: {contexto_base.get('morada', 'ainda a confirmar')}\n"
        f"🗺️ Coordenadas: {latitude}, {longitude}\n"
        f"🔗 Google Maps: {contexto_base.get('link_google_maps', 'sem link')}\n"
        f"🐾 Aceita animais: {'Sim' if contexto_base.get('aceita_animais') else 'Não'}\n"
        f"🏊 Piscina: {'Sim' if contexto_base.get('tem_piscina') else 'Não'}\n"
        f"🔥 Churrasqueira: {'Sim' if contexto_base.get('tem_churrasqueira') else 'Não'}\n"
        f"🎱 Snooker: {'Sim' if contexto_base.get('tem_snooker') else 'Não'}\n"
        f"🍷 Pode levar vinho: {'Sim' if contexto_base.get('pode_levar_vinho') else 'Não'}\n"
        f"🥘 Pode levar comida: {'Sim' if contexto_base.get('pode_levar_comida') else 'Não'}\n"
        f"💃 Dress code: {contexto_base.get('dress_code', 'não especificado')}\n"
        f"⏰ Hora de início: {contexto_base.get('hora_inicio', 'não definida')}\n"
        f"📶 Wi-Fi: {contexto_base.get('wifi', 'não indicado')}\n"
        f"🌐 Link oficial: {contexto_base.get('link', 'sem link')}"
    )

    # ✅ Prompt para o evento
    prompt = f"""
Tu és o assistente oficial da festa de passagem de ano 🎆.
Responde de forma breve (máximo 2 frases), divertida e natural.

🎯 Contexto real do evento:
{contexto_texto}

NOTA IMPORTANTE: Se o local ainda não estiver definido, menciona que estão a ver opções e que já têm o Monte da Galega como backup.

🧍 Perfil do utilizador:
- Nome: {nome}
- Personalidade: {personalidade}

💬 Pergunta do utilizador:
{pergunta}

🎙️ Instruções:
- Usa sempre os dados reais do JSON quando disponíveis
- Se os dados não estiverem completos, menciona que ainda estão a organizar
- Se perguntarem sobre o local e ainda não houver, diz que têm o Monte da Galega como plano B
- Se perguntarem algo pessoal ou fora do tema, responde com humor leve
- Mantém sempre o Português de Portugal e a segunda pessoa do singular
- Evita respostas longas (máximo 2 frases curtas)
"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "És um assistente sociável e divertido que fala Português de Portugal."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 180,
    }

    try:
        response = requests.post(GROQ_URL, headers=headers, json=data, timeout=20)
        response.raise_for_status()
        result = response.json()
        resposta = result["choices"][0]["message"]["content"].strip()
        return resposta
    except Exception as e:
        print(f"⚠️ Erro no LLM Groq: {e}")
        return "Estou com interferências celestiais... tenta outra vez 😅"