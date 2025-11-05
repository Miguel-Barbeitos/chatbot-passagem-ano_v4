# -*- coding: utf-8 -*-
"""
Gestor de perfis e confirmações centralizado no Qdrant Cloud
"""

import os
import json
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.http import models
import streamlit as st

# ============================================================
# 🔧 CONFIGURAÇÃO DO QDRANT CLOUD
# ============================================================

def inicializar_qdrant():
    """Inicializa o cliente Qdrant com prioridade: Streamlit Secrets → Env Vars → Local"""
    try:
        QDRANT_URL = st.secrets["QDRANT_URL"]
        QDRANT_API_KEY = st.secrets["QDRANT_API_KEY"]
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        print(f"☁️  Conectado ao Qdrant Cloud: {QDRANT_URL}")
        return client
    except Exception:
        # fallback: variáveis de ambiente
        QDRANT_URL = os.getenv("QDRANT_URL")
        QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
        if QDRANT_URL and QDRANT_API_KEY:
            client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
            print(f"☁️  Conectado ao Qdrant Cloud (env): {QDRANT_URL}")
            return client
        else:
            # fallback local apenas em dev
            print("⚠️  Sem credenciais — a usar Qdrant local (data/qdrant)")
            return QdrantClient(path="data/qdrant")

client = inicializar_qdrant()
COLLECTION_PERFIS = "perfis_convidados"

# ============================================================
# 📋 FUNÇÕES BASE
# ============================================================

def listar_todos_perfis():
    """Obtém todos os perfis da coleção perfis_convidados"""
    try:
        resultados, _ = client.scroll(collection_name=COLLECTION_PERFIS, limit=500)
        return [r.payload for r in resultados]
    except Exception as e:
        print(f"❌ Erro ao listar perfis: {e}")
        return []

def buscar_perfil(nome):
    """Procura um perfil pelo nome"""
    try:
        resultados, _ = client.scroll(
            collection_name=COLLECTION_PERFIS,
            scroll_filter={"must": [{"key": "nome", "match": {"value": nome}}]},
            limit=1
        )
        if resultados:
            return resultados[0].payload
        return None
    except Exception as e:
        print(f"❌ Erro ao procurar perfil: {e}")
        return None

def listar_familia(familia_id):
    """Lista todos os membros de uma família"""
    try:
        resultados, _ = client.scroll(
            collection_name=COLLECTION_PERFIS,
            scroll_filter={"must": [{"key": "familia_id", "match": {"value": familia_id}}]},
            limit=50
        )
        return [r.payload for r in resultados]
    except Exception as e:
        print(f"❌ Erro ao listar família: {e}")
        return []

def atualizar_perfil(nome, payload):
    """Atualiza os dados de um perfil no Qdrant"""
    try:
        pontos, _ = client.scroll(
            collection_name=COLLECTION_PERFIS,
            scroll_filter={"must": [{"key": "nome", "match": {"value": nome}}]},
            limit=1
        )

        if pontos:
            point_id = pontos[0][0].id
            client.set_payload(collection_name=COLLECTION_PERFIS, payload=payload, points=[point_id])
            print(f"✅ Perfil '{nome}' atualizado no Qdrant Cloud.")
            return True

        print(f"⚠️ Perfil '{nome}' não encontrado para atualização.")
        return False
    except Exception as e:
        print(f"❌ Erro ao atualizar perfil: {e}")
        return False

# ============================================================
# ✅ FUNÇÕES DE CONFIRMAÇÕES (Qdrant central)
# ============================================================

def get_confirmacoes_qdrant():
    """Lê confirmações diretamente da coleção perfis_convidados"""
    try:
        res = client.scroll(
            collection_name=COLLECTION_PERFIS,
            scroll_filter={"must": [{"key": "confirmado", "match": {"value": True}}]},
            limit=200
        )
        return [hit.payload for hit in res[0]] if res and res[0] else []
    except Exception as e:
        print(f"❌ Erro ao ler confirmações: {e}")
        return []

def atualizar_confirmacao_qdrant(nome, confirmado=True, acompanhantes=None):
    """Atualiza o campo 'confirmado' no Qdrant Cloud"""
    try:
        if acompanhantes is None:
            acompanhantes = []

        pontos, _ = client.scroll(
            collection_name=COLLECTION_PERFIS,
            scroll_filter={"must": [{"key": "nome", "match": {"value": nome}}]},
            limit=1
        )

        if pontos and pontos:
            point_id = pontos[0][0].id
            client.set_payload(
                collection_name=COLLECTION_PERFIS,
                payload={
                    "confirmado": confirmado,
                    "acompanhantes": acompanhantes,
                    "data_confirmacao": datetime.now().isoformat() if confirmado else None
                },
                points=[point_id],
            )
            print(f"✅ Atualizado '{nome}' no Qdrant Cloud → confirmado={confirmado}")
            return True

        print(f"⚠️ Perfil '{nome}' não encontrado para atualização")
        return False

    except Exception as e:
        print(f"❌ Erro ao atualizar confirmação: {e}")
        return False

# ============================================================
# 🧪 TESTE LOCAL
# ============================================================

if __name__ == "__main__":
    print("🔧 Teste rápido ao gestor de perfis (Qdrant Cloud)\n")

    todos = listar_todos_perfis()
    print(f"Total de perfis: {len(todos)}")

    exemplo = todos[0]["nome"] if todos else "João Paulo"
    perfil = buscar_perfil(exemplo)
    print(f"Perfil exemplo: {perfil}")

    confirmados = get_confirmacoes_qdrant()
    print(f"Confirmados no Qdrant: {len(confirmados)}")
