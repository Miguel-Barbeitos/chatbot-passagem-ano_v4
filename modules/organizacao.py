"""
🎉 Módulo de Organização da Passagem de Ano
Centraliza informações sobre: evento, quintas, confirmações e respostas por email.
"""

import os
import json
import sqlite3
import re
from datetime import datetime
from pathlib import Path

# Caminhos
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
EVENT_JSON = DATA_DIR / "event.json"
CONFIRMADOS_JSON = DATA_DIR / "confirmados.json"
QUINTAS_DB = DATA_DIR / "quintas.db"

# =====================================================
# 📅 INFORMAÇÕES DO EVENTO
# =====================================================

def get_evento():
    """Carrega informações do evento"""
    try:
        with open(EVENT_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Erro ao ler event.json: {e}")
        return {
            "nome": "Passagem de Ano 2024/2025",
            "data_inicio": "2025-12-30",
            "data_fim": "2026-01-04",
            "cor": "Amarelo",
            "orcamento_pessoa": 300,
            "total_convidados": 35
        }

def get_datas_evento():
    """Retorna datas formatadas"""
    evento = get_evento()
    di = datetime.strptime(evento["data_inicio"], "%Y-%m-%d")
    df = datetime.strptime(evento["data_fim"], "%Y-%m-%d")
    return {
        "inicio": di.strftime("%d/%m/%Y"),
        "fim": df.strftime("%d/%m/%Y"),
        "duracao_dias": (df - di).days
    }

# =====================================================
# 👥 CONFIRMAÇÕES
# =====================================================

def get_confirmacoes():
    try:
        with open(CONFIRMADOS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"confirmados": []}

def get_stats_confirmacoes():
    confirmacoes = get_confirmacoes()
    evento = get_evento()
    total = len(confirmacoes.get("confirmados", []))
    total_convidados = evento.get("total_convidados", 35)
    taxa = round(total / total_convidados * 100, 1) if total_convidados else 0
    return {
        "total_confirmados": total,
        "total_convidados": total_convidados,
        "taxa_confirmacao": taxa
    }

# =====================================================
# 🏡 QUINTAS E RESPOSTAS
# =====================================================

def extrair_nome_quinta(pergunta: str) -> str | None:
    """Extrai o nome provável de uma quinta da pergunta"""
    match = re.search(
        r"(quinta|hotel|herdade|pousada|estalagem|centro)\s+[a-zà-ÿ\s\(\)]+",
        pergunta, re.IGNORECASE
    )
    if match:
        return match.group(0).strip().title()
    return None

def responder_pergunta_organizacao(pergunta: str):
    """
    Responde perguntas sobre quintas, emails e organização.
    """
    p = pergunta.lower().strip()

    # ===== NOVO: Pergunta sobre resposta de uma quinta =====
    if any(k in p for k in ["resposta da", "respondeu", "email da", "email de", "o que disse", "qual foi a resposta"]):
        nome_quinta = extrair_nome_quinta(pergunta)
        if not nome_quinta:
            return "🤔 Podes indicar o nome da quinta?"

        try:
            from modules.quintas_qdrant import procurar_quinta_por_nome
            info = procurar_quinta_por_nome(nome_quinta)
        except Exception as e:
            print(f"❌ Erro ao aceder ao Qdrant: {e}")
            info = None

        if not info:
            return f"🤔 Não encontrei nenhuma quinta chamada **{nome_quinta}**."

        resposta_email = (
            info.get("email_resposta")
            or info.get("resposta_original")
            or info.get("ultima_resposta")
            or info.get("detalhes")
            or info.get("resposta")
        )

        if not resposta_email:
            return f"📭 Ainda não há resposta de email registada para **{info.get('nome', nome_quinta)}**."

        if len(resposta_email) > 600:
            resposta_email = resposta_email[:600] + "..."

        estado = info.get("estado", "—")
        local = info.get("local", "")
        nome = info.get("nome", nome_quinta)

        return (
            f"📨 **{nome}** ({local}) respondeu por email:\n\n"
            f"🗣️ _{resposta_email}_\n\n"
            f"📊 Estado: **{estado}**"
        )

    # ===== Outras perguntas (já existentes) =====
    if any(f in p for f in ["já temos", "temos quinta", "há quinta"]):
        from modules.quintas_qdrant import listar_quintas
        stats = {"total_contactadas": len(listar_quintas())}
        return f"✅ Sim! Já temos quintas contactadas ({stats['total_contactadas']} no total)."

    if "quintas" in p and "contactadas" in p:
        try:
            from modules.quintas_qdrant import listar_quintas
            quintas = listar_quintas()
            resposta = "📋 Quintas contactadas:\n"
            for q in quintas[:10]:
                resposta += f"• {q.get('nome')} — {q.get('resposta','Sem resposta')}\n"
            return resposta
        except Exception as e:
            return f"⚠️ Erro ao listar quintas: {e}"

    if "quantos" in p and "confirmados" in p:
        stats = get_stats_confirmacoes()
        return (
            f"👥 {stats['total_confirmados']} confirmados de {stats['total_convidados']} convidados.\n"
            f"📊 Taxa de confirmação: {stats['taxa_confirmacao']}%"
        )

    # Fallback
    return None

# =====================================================
# 🧪 TESTE LOCAL
# =====================================================

if __name__ == "__main__":
    print("🧪 Teste: resposta de quinta específica\n")
    print(responder_pergunta_organizacao("Qual foi a resposta da Centro Escutista de Apúlia (Esposende)?"))
