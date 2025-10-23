# llm_groq.py
import os
import json
import requests

# =====================================================
# ⚙️ CONFIGURAÇÃO GERAL
# =====================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("❌ Falta a variável de ambiente GROQ_API_KEY.")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"  # modelo gratuito e rápido

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
            else:
                contexto.append(f"{k.replace('_', ' ')}: {v}")
        return "\n".join(contexto)
    except Exception as e:
        print(f"⚠️ Erro ao carregar contexto base: {e}")
        return "Informações da festa indisponíveis."

# =====================================================
# 🤖 GERAÇÃO DE RESPOSTAS NATURAIS
# =====================================================
import requests
import streamlit as st
import os

GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

def gerar_resposta_llm(pergunta, perfil=None, contexto_base=None):
    """
    Gera uma resposta contextual, divertida e factual sobre a festa.
    Usa o modelo LLaMA 3.1 via Groq API.
    """
    perfil = perfil or {}
    nome = perfil.get("nome", "Utilizador")
    personalidade = perfil.get("personalidade", "neutro")

    # ✅ Verifica chave da API
    if not GROQ_API_KEY:
        raise ValueError("❌ Falta a variável de ambiente GROQ_API_KEY. Define-a no Streamlit secrets ou no ambiente local.")

    # ✅ Garante que temos um dicionário para o contexto
    if contexto_base is None:
        contexto_base = {}

    # ✅ Extrai coordenadas
    coords = contexto_base.get("coordenadas", {})
    latitude = coords.get("latitude", "desconhecida")
    longitude = coords.get("longitude", "desconhecida")

    # ✅ Formata o contexto legível
    if isinstance(contexto_base, dict):
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
    else:
        contexto_texto = str(contexto_base)

    # ✅ Prompt completo
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

