# llm_groq.py
import os
import json
import requests

# =====================================================
# ⚙️ CONFIGURAÇÃO GERAL
# =====================================================
oGROQ_API_KEY = os.getenv("GROQ_API_KEY")
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
def gerar_resposta_llm(pergunta, perfil=None, confirmados=None, contexto_base=None):
    """
    Gera uma resposta contextual, divertida e factual sobre a festa.
    Usa o modelo LLaMA 3.1 via Groq API.
    """
    perfil = perfil or {}
    confirmados = confirmados or []
    nome = perfil.get("nome", "Utilizador")
    personalidade = perfil.get("personalidade", "neutro")

    if not GROQ_API_KEY:
        raise ValueError("❌ Falta a variável de ambiente GROQ_API_KEY. Define-a antes de correr o app.")

    if not contexto_base:
        contexto_base = carregar_contexto_base()

    prompt = f"""
Tu és o assistente oficial da festa de passagem de ano no {contexto_base}.
Responde de forma breve (máximo 2 frases), divertida e direta.
A tua missão é **manter sempre o foco na festa de passagem de ano**, 
mesmo que o utilizador fale de outros temas. 
Usa sempre as informações reais abaixo sobre o evento, e **nunca inventes** nada.

🎯 Contexto base da festa (informações verdadeiras do JSON):
{contexto_base}

✅ Confirmados até agora:
{', '.join(confirmados) if confirmados else 'Ainda ninguém confirmou.'}

🧍 Perfil do utilizador:
- Nome: {nome}
- Personalidade: {personalidade}

💬 Pergunta do utilizador:
{pergunta}

🎙️ Instruções:
- Se a pergunta estiver relacionada com a festa, responde com base no contexto acima.
- Se a pergunta for sobre confirmações, **usa EXATAMENTE a lista de confirmados acima**
- Se a pergunta for sobre outro tema, responde brevemente e redireciona de forma natural para a festa.
- Se o utilizador disser que confirma, mostra entusiasmo e diz que foi adicionado à lista.
- Mantém o tom coerente com a personalidade (ex: se for sarcástico, usa ironia leve).
- Se não souberes algo, diz de forma divertida ("ainda não me contaram isso, mas posso perguntar 😄").
- Responde sempre em Português de Portugal.
- Usa a segunda pessoa do singular.
- Evita respostas longas (máximo 2 frases curtas).
"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "És um assistente sociável e divertido que fala em Português de Portugal."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.8,
        "max_tokens": 200,
    }

    try:
        response = requests.post(GROQ_URL, headers=headers, json=data, timeout=20)
        response.raise_for_status()
        result = response.json()
        resposta = result["choices"][0]["message"]["content"].strip()
        return resposta
    except Exception as e:
        print(f"⚠️ Erro no LLM Groq: {e}")
        return "Estou com interferências celestiais... tenta outra vez 🙏😅"