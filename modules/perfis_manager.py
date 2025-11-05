# -*- coding: utf-8 -*-
"""
Gestão de perfis e confirmações no Qdrant Cloud
Versão corrigida e centralizada — compatível com Streamlit + execução local
"""
import os
import unicodedata
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct, Filter, FieldCondition, MatchValue, MatchText
)


# ============================================================
# 🔧 CONFIGURAÇÃO BASE
# ============================================================

COLLECTION_PERFIS = "perfis_convidados"


def log(msg):
    """Logger simples"""
    print(f"[perfis_manager] {msg}")


# ============================================================
# 🔌 CONEXÃO AO QDRANT
# ============================================================

def get_qdrant_client():
    """Cria cliente Qdrant — usa secrets (Streamlit) ou variáveis de ambiente."""
    try:
        import streamlit as st
        qdrant_url = st.secrets.get("QDRANT_URL")
        qdrant_key = st.secrets.get("QDRANT_API_KEY")
        if qdrant_url and qdrant_key:
            log(f"☁️  Conectado ao Qdrant Cloud (Streamlit): {qdrant_url}")
            return QdrantClient(url=qdrant_url, api_key=qdrant_key, timeout=10.0)
    except Exception:
        pass

    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_key = os.getenv("QDRANT_API_KEY")

    if not qdrant_url or not qdrant_key:
        raise RuntimeError("❌ Qdrant Cloud não configurado. Define QDRANT_URL e QDRANT_API_KEY.")

    log(f"☁️  Conectado ao Qdrant Cloud (env): {qdrant_url}")
    return QdrantClient(url=qdrant_url, api_key=qdrant_key, timeout=10.0)


client = get_qdrant_client()


# ============================================================
# 🧠 FUNÇÕES DE APOIO
# ============================================================

def normalizar_texto(texto: str) -> str:
    """Remove acentos e converte para minúsculas"""
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c)).lower().strip()


# ============================================================
# 👤 PERFIS — BUSCA E LISTAGEM
# ============================================================

def listar_todos_perfis():
    """Obtém todos os perfis da coleção"""
    try:
        resultados, _ = client.scroll(collection_name=COLLECTION_PERFIS, limit=500)
        return [r.payload for r in resultados]
    except Exception as e:
        log(f"❌ Erro ao listar perfis: {e}")
        return []


def buscar_perfil(nome: str):
    """Procura um perfil pelo nome (busca normalizada)"""
    nome_norm = normalizar_texto(nome)
    try:
        resultados, _ = client.scroll(collection_name=COLLECTION_PERFIS, limit=500)
        for r in resultados:
            if normalizar_texto(r.payload.get("nome", "")) == nome_norm:
                return {**r.payload, "id_qdrant": r.id}
    except Exception as e:
        log(f"❌ Erro ao procurar perfil: {e}")
    return None


# ============================================================
# 🏡 FAMÍLIAS
# ============================================================

def listar_familia(familia_id: str):
    """Lista todos os membros de uma família"""
    try:
        filtro = Filter(
            must=[FieldCondition(key="familia_id", match=MatchValue(value=familia_id))]
        )
        resultados, _ = client.scroll(collection_name=COLLECTION_PERFIS, scroll_filter=filtro, limit=100)
        return [r.payload for r in resultados]
    except Exception as e:
        log(f"❌ Erro ao listar família {familia_id}: {e}")
        return []


# ============================================================
# ✏️ ATUALIZAÇÕES DE PERFIS
# ============================================================

def atualizar_perfil(nome: str, dados: dict):
    """Atualiza dados de um perfil existente"""
    try:
        perfil = buscar_perfil(nome)
        if not perfil:
            log(f"⚠️  Perfil '{nome}' não encontrado para atualização.")
            return False

        point_id = perfil.get("id_qdrant")
        if not point_id:
            log(f"⚠️  ID Qdrant ausente para '{nome}'.")
            return False

        novo_payload = {**perfil, **dados}
        client.upsert(
            collection_name=COLLECTION_PERFIS,
            points=[PointStruct(id=point_id, vector=None, payload=novo_payload)],
        )
        log(f"✅ Perfil '{nome}' atualizado com sucesso.")
        return True

    except Exception as e:
        log(f"❌ Erro ao atualizar perfil '{nome}': {e}")
        return False


# ============================================================
# ✅ CONFIRMAÇÕES
# ============================================================

def get_confirmados():
    """Obtém todos os convidados confirmados"""
    try:
        filtro = Filter(
            must=[FieldCondition(key="confirmado", match=MatchValue(value=True))]
        )
        resultados, _ = client.scroll(collection_name=COLLECTION_PERFIS, scroll_filter=filtro, limit=500)
        return [r.payload for r in resultados]
    except Exception as e:
        log(f"❌ Erro ao ler confirmados do Qdrant: {e}")
        return []


def atualizar_confirmacao_qdrant(nome: str, confirmado: bool, confirmado_por=None):
    """Atualiza o estado de confirmação de uma pessoa"""
    try:
        perfil = buscar_perfil(nome)
        if not perfil:
            log(f"⚠️  Perfil '{nome}' não encontrado para confirmação.")
            return False

        perfil["confirmado"] = confirmado
        perfil["confirmado_por"] = confirmado_por
        perfil["data_confirmacao"] = datetime.now().isoformat() if confirmado else None

        point_id = perfil.get("id_qdrant")
        if not point_id:
            log(f"⚠️  ID Qdrant ausente para '{nome}'.")
            return False

        client.upsert(
            collection_name=COLLECTION_PERFIS,
            points=[PointStruct(id=point_id, vector=None, payload=perfil)],
        )

        estado = "✅ Confirmado" if confirmado else "❌ Removido"
        log(f"{estado}: {nome}")
        return True
    except Exception as e:
        log(f"❌ Erro ao atualizar confirmação no Qdrant: {e}")
        return False


def get_estatisticas():
    """Gera estatísticas básicas de confirmações"""
    try:
        confirmados = get_confirmados()
        familias = {}
        for p in confirmados:
            fam = p.get("familia_id", "desconhecida")
            familias.setdefault(fam, []).append(p["nome"])

        return {
            "total_confirmados": len(confirmados),
            "familias": len(familias),
            "ultima_atualizacao": datetime.now().isoformat(),
        }
    except Exception as e:
        log(f"❌ Erro ao gerar estatísticas: {e}")
        return {}


# ============================================================
# 🧪 TESTE LOCAL
# ============================================================

if __name__ == "__main__":
    log("🔧 Teste rápido do gestor de perfis...")
    print("\nTodos os perfis (limite 5):")
    for p in listar_todos_perfis()[:5]:
        print(" •", p.get("nome"))

    print("\nConfirmando Barbeitos...")
    atualizar_confirmacao_qdrant("Barbeitos", True, confirmado_por="Miguel")

    print("\nConfirmados:")
    for p in get_confirmados():
        print(" •", p.get("nome"))

    print("\nEstatísticas:")
    print(get_estatisticas())
