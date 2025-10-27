# llm_groq.py
import os
import json
import requests
import sqlite3
import pandas as pd
import streamlit as st

from learning_qdrant import procurar_resposta_semelhante, guardar_nota_quinta

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
# 🔍 DETEÇÃO DE PERGUNTAS SOBRE QUINTAS
# =====================================================
def e_pergunta_de_quintas(pergunta: str) -> bool:
    """Deteta se a pergunta é sobre quintas / base de dados."""
    p = pergunta.lower()
    chaves = [
        "quinta", "quintas", "contactadas", "contactaste", "responderam",
        "piscina", "capacidade", "custo", "barata", "animais", "resposta", "zona", "morada"
    ]
    return any(c in p for c in chaves)

# =====================================================
# 🤖 GERAR SQL AUTOMATICAMENTE
# =====================================================
def e_pergunta_estado(pergunta: str) -> bool:
    termos = ["porquê", "porque", "motivo", "estado", "respondeu", "atualização"]
    return any(t in pergunta.lower() for t in termos)

def gerar_sql_da_pergunta(pergunta: str) -> str:
    """Usa o LLM para gerar um SQL seguro (apenas SELECT)."""
    schema = """
    Tabela: quintas
    Colunas: nome, zona, morada, email, telefone, website, estado, resposta,
    capacidade_43, custo_4500, estimativa_custo, capacidade_confirmada,
    ultima_resposta, proposta_tarifaria, unidades_detalhe, num_unidades,
    observacao_unidades, custo_total, resumo_resposta, observacoes, notas_calculo.
    """

    prompt_sql = f"""
Gera apenas o SQL (SELECT ...) para responder à pergunta do utilizador.
O SQL deve ser simples, compatível com SQLite e usar apenas as colunas listadas.
Pergunta: "{pergunta}"
{schema}
"""

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "És um assistente que converte linguagem natural em SQL seguro (apenas SELECT)."},
            {"role": "user", "content": prompt_sql},
        ],
        "temperature": 0.0,
        "max_tokens": 120,
    }

    try:
        resp = requests.post(GROQ_URL, headers=headers, json=data, timeout=20)
        query = resp.json()["choices"][0]["message"]["content"].strip()
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
    json_data = json.dumps(dados, ensure_ascii=False)
    prompt = f"""
Transforma estes dados JSON numa resposta breve e natural à pergunta "{pergunta}".
Responde em Português de Portugal, num tom simpático e direto, em no máximo 2 frases.
Dados:
{json_data}
"""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.6,
        "max_tokens": 150,
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

if e_pergunta_de_quintas(pergunta):
    if e_pergunta_estado(pergunta):
        # Pergunta de contexto (porquê, estado, resposta)
        nota = procurar_resposta_semelhante(pergunta, contexto="quintas")
        if nota:
            return nota
        else:
            return "Ainda não há resposta confirmada dessa quinta 😉"
    else:
    """
    Gera uma resposta contextual:
    - sobre a festa (usa event.json)
    - ou sobre as quintas (usa SQLite)
    """
    perfil = perfil or {}
    nome = perfil.get("nome", "Utilizador")
    personalidade = perfil.get("personalidade", "neutro")

    # ✅ 1 — Consultas sobre quintas (base SQLite)
    if e_pergunta_de_quintas(pergunta):
        sql = gerar_sql_da_pergunta(pergunta)
        if sql:
            dados = executar_sql(sql)
            if dados:
                return gerar_resposta_dados_llm(pergunta, dados)
            else:
                return "Não encontrei nenhuma quinta que corresponda a isso 😅"
        else:
            return "Não consegui interpretar bem a tua pergunta sobre as quintas 😅"

    # ✅ 2 — Caso contrário, responde sobre a festa
    if not contexto_base:
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                contexto_base = json.load(f)
        except Exception:
            contexto_base = {}

    coords = contexto_base.get("coordenadas", {})
    latitude = coords.get("latitude", "desconhecida")
    longitude = coords.get("longitude", "desconhecida")

    contexto_texto = (
        f"📍 Local: {contexto_base.get('nome_local', 'local desconhecido')}\n"
        f"🏠 Morada: {contexto_base.get('morada', 'morada não disponível')}\n"
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

🧍 Perfil do utilizador:
- Nome: {nome}
- Personalidade: {personalidade}

💬 Pergunta do utilizador:
{pergunta}

🎙️ Instruções:
- Usa sempre os dados reais do JSON e nunca inventes.
- Se perguntarem sobre o local, morada, mapa ou coordenadas, usa a informação do contexto.
- Se perguntarem sobre animais, piscina, churrasqueira, snooker, vinho ou comida, responde com base no JSON.
- Se perguntarem algo pessoal ou fora do tema (ex: "estás a brincar", "bom dia", etc.), responde com humor leve, sem repetir a morada.
- Mantém sempre o Português de Portugal e a segunda pessoa do singular.
- Evita respostas longas (máximo 2 frases curtas).
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
