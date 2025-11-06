# -*- coding: utf-8 -*-
"""
Gestor central de perfis de convidados no Qdrant Cloud
"""

import os
import unicodedata
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue
import json


# =========================================================
# ⚙️  CONFIGURAÇÃO DO QDRANT (LÊ DO STREAMLIT SECRETS)
# =========================================================
def get_qdrant_client():
    """Obtém cliente Qdrant com fallback local."""
    try:
        import streamlit as st
        qdrant_url = st.secrets.get("QDRANT_URL")
        qdrant_key = st.secrets.get("QDRANT_API_KEY")
        if qdrant_url and qdrant_key:
            print(f"[perfis_manager] ☁️  Conectado ao Qdrant Cloud (Streamlit): {qdrant_url}")
            return QdrantClient(url=qdrant_url, api_key=qdrant_key, timeout=10.0)
    except Exception as e:
        print(f"⚠️  Sem acesso a st.secrets ({e})")

    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_key = os.getenv("QDRANT_API_KEY")

    if qdrant_url and qdrant_key:
        print(f"[perfis_manager] ☁️  Conectado ao Qdrant Cloud (env): {qdrant_url}")
        return QdrantClient(url=qdrant_url, api_key=qdrant_key, timeout=10.0)

    print("⚠️  Sem credenciais — a usar Qdrant local (data/qdrant)")
    return QdrantClient(path="data/qdrant")


client = get_qdrant_client()
COLLECTION_PERFIS = "perfis_convidados"


# =========================================================
# 🧰 FUNÇÕES AUXILIARES
# =========================================================
def normalizar_texto(txt):
    if not txt:
        return ""
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return txt.lower().strip()


def log(msg: str):
    print(msg)


# =========================================================
# 🔍 BUSCA E GESTÃO DE PERFIS
# =========================================================
def listar_todos_perfis(limit=500):
    try:
        resultados, _ = client.scroll(collection_name=COLLECTION_PERFIS, limit=limit)
        return [r.payload | {"id_qdrant": r.id} for r in resultados]
    except Exception as e:
        log(f"❌ Erro ao listar perfis: {e}")
        return []


def buscar_perfil(nome: str):
    """Procura perfil pelo nome (normalizado e tolerante a duplicados)."""
    try:
        nome_n = normalizar_texto(nome)
        resultados, _ = client.scroll(
            collection_name=COLLECTION_PERFIS,
            scroll_filter=Filter(must=[FieldCondition(key="nome", match=MatchValue(value=nome))]),
            limit=50,
        )

        if not resultados:
            todos = listar_todos_perfis()
            candidatos = [p for p in todos if normalizar_texto(p.get("nome")) == nome_n]
        else:
            candidatos = [r.payload | {"id_qdrant": r.id} for r in resultados]

        if not candidatos:
            return None

        # Prioriza perfis confirmados e depois o mais recente (se disponível)
        candidatos.sort(key=lambda p: (p.get("confirmado", False), p.get("data_confirmacao", "")), reverse=True)
        perfil_escolhido = candidatos[0]
        return perfil_escolhido
    except Exception as e:
        log(f"❌ Erro ao procurar perfil: {e}")
        return None


def listar_familia(familia_id: str):
    try:
        resultados, _ = client.scroll(
            collection_name=COLLECTION_PERFIS,
            scroll_filter=Filter(must=[FieldCondition(key="familia_id", match=MatchValue(value=familia_id))]),
            limit=100,
        )
        return [r.payload for r in resultados]
    except Exception as e:
        log(f"❌ Erro ao listar família: {e}")
        return []


# =========================================================
# 🧾 ATUALIZAÇÕES DE PERFIS
# =========================================================
def atualizar_perfil(nome: str, dados: dict):
    try:
        perfil = buscar_perfil(nome)
        if not perfil:
            log(f"⚠️  Perfil '{nome}' não encontrado para atualização.")
            return False

        point_id = perfil.get("id_qdrant")
        if not point_id:
            log(f"⚠️  ID Qdrant ausente para '{nome}'.")
            return False

        perfil_limpo = {k: v for k, v in perfil.items() if k != "id_qdrant"}
        novo_payload = {**perfil_limpo, **dados}

        client.set_payload(collection_name=COLLECTION_PERFIS, payload=novo_payload, points=[point_id])
        log(f"✅ Perfil '{nome}' atualizado com sucesso.")
        return True
    except Exception as e:
        log(f"❌ Erro ao atualizar perfil '{nome}': {e}")
        return False


def get_confirmacoes_qdrant():
    try:
        resultados, _ = client.scroll(
            collection_name=COLLECTION_PERFIS,
            scroll_filter=Filter(must=[FieldCondition(key="confirmado", match=MatchValue(value=True))]),
            limit=1000,
        )
        return [r.payload.get("nome") for r in resultados]
    except Exception as e:
        log(f"❌ Erro ao ler confirmados do Qdrant: {e}")
        return []


def atualizar_confirmacao_qdrant(nome, confirmado=True):
    try:
        perfil = buscar_perfil(nome)
        if not perfil:
            log(f"⚠️ Perfil '{nome}' não encontrado para confirmar.")
            return False

        novos_dados = {
            "confirmado": confirmado,
            "confirmado_por": nome,
            "data_confirmacao": datetime.now().isoformat() if confirmado else None,
        }
        return atualizar_perfil(nome, novos_dados)
    except Exception as e:
        log(f"❌ Erro ao atualizar confirmação: {e}")
        return False
