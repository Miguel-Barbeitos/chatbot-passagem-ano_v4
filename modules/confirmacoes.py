# -*- coding: utf-8 -*-
"""
Sistema de Confirmacoes integrado com Qdrant Cloud
Autor: Miguel + GPT
"""

import unicodedata
import re
from datetime import datetime
from qdrant_client.models import Filter, FieldCondition, MatchValue, PointStruct

from modules.perfis_manager import (
    client,
    COLLECTION_PERFIS,
    buscar_perfil,
    listar_familia,
)

# ======================================================
# 🔧 Funções auxiliares
# ======================================================

def normalizar_nome(nome: str) -> str:
    """Remove acentos e põe tudo em minúsculas para comparação."""
    if not isinstance(nome, str):
        return ""
    nome = unicodedata.normalize('NFKD', nome)
    nome = ''.join(c for c in nome if not unicodedata.combining(c))
    return nome.lower().strip()


# ======================================================
# 🔍 Ler e guardar confirmacoes diretamente no Qdrant
# ======================================================

def get_confirmados():
    """Retorna lista de nomes confirmados a partir do Qdrant."""
    try:
        resultados, _ = client.scroll(
            collection_name=COLLECTION_PERFIS,
            scroll_filter=Filter(
                must=[FieldCondition(key="confirmado", match=MatchValue(value=True))]
            ),
            limit=500
        )
        confirmados = [r.payload.get("nome") for r in resultados if r.payload.get("confirmado")]
        return sorted(confirmados)
    except Exception as e:
        print(f"❌ Erro ao ler confirmados do Qdrant: {e}")
        return []


def get_estatisticas():
    """Gera estatísticas de confirmações (total, famílias completas, etc)."""
    try:
        confirmados = get_confirmados()
        total_confirmados = len(confirmados)
        familias = {}

        # Agrupar por família
        resultados, _ = client.scroll(collection_name=COLLECTION_PERFIS, limit=500)
        for r in resultados:
            familia_id = r.payload.get("familia_id")
            nome = r.payload.get("nome")
            if not familia_id:
                continue
            if familia_id not in familias:
                familias[familia_id] = {"total": 0, "confirmados": 0}
            familias[familia_id]["total"] += 1
            if nome in confirmados:
                familias[familia_id]["confirmados"] += 1

        familias_completas = [f for f, v in familias.items() if v["confirmados"] == v["total"]]
        familias_parciais = [f for f, v in familias.items() if 0 < v["confirmados"] < v["total"]]

        return {
            "total_confirmados": total_confirmados,
            "familias_completas": len(familias_completas),
            "familias_parciais": len(familias_parciais),
            "ultima_atualizacao": datetime.now().isoformat(),
        }

    except Exception as e:
        print(f"❌ Erro ao gerar estatísticas: {e}")
        return {}


# ======================================================
# ✅ Confirmações
# ======================================================

def confirmar_pessoa(nome: str, confirmado_por=None):
    """Confirma um convidado individual."""
    try:
        perfil = buscar_perfil(nome)
        if not perfil:
            return {
                "sucesso": False,
                "mensagem": f"'{nome}' não está na lista de convidados.",
                "familia_sugerida": []
            }

        nome_real = perfil.get("nome")
        familia_id = perfil.get("familia_id")

        # Já confirmado?
        if perfil.get("confirmado"):
            return {
                "sucesso": True,
                "mensagem": f"{nome_real} já está confirmado.",
                "familia_sugerida": []
            }

        # Atualiza no Qdrant
        client.upsert(
            collection_name=COLLECTION_PERFIS,
            points=[
                PointStruct(
                    id=perfil["id"],
                    vector=perfil.get("vector"),
                    payload={
                        **perfil,
                        "confirmado": True,
                        "confirmado_por": confirmado_por or nome_real,
                        "data_confirmacao": datetime.now().isoformat(),
                    }
                )
            ]
        )

        # Obter membros da família não confirmados
        familia = listar_familia(familia_id)
        confirmados = get_confirmados()
        familia_nao_confirmada = [
            p["nome"] for p in familia
            if p["nome"] != nome_real and p["nome"] not in confirmados
        ]

        return {
            "sucesso": True,
            "mensagem": f"🎉 {nome_real} confirmado com sucesso!",
            "familia_sugerida": familia_nao_confirmada
        }

    except Exception as e:
        print(f"❌ Erro ao confirmar pessoa: {e}")
        return {"sucesso": False, "mensagem": "Erro ao confirmar", "familia_sugerida": []}


def remover_confirmacao(nome: str):
    """Remove confirmação de um convidado."""
    try:
        perfil = buscar_perfil(nome)
        if not perfil:
            return {"sucesso": False, "mensagem": f"{nome} não encontrado."}

        client.upsert(
            collection_name=COLLECTION_PERFIS,
            points=[
                PointStruct(
                    id=perfil["id"],
                    vector=perfil.get("vector"),
                    payload={
                        **perfil,
                        "confirmado": False,
                        "confirmado_por": None,
                        "data_confirmacao": None
                    }
                )
            ]
        )

        return {"sucesso": True, "mensagem": f"{nome} removido da lista de confirmados."}
    except Exception as e:
        print(f"❌ Erro ao remover confirmação: {e}")
        return {"sucesso": False, "mensagem": "Erro ao remover confirmação."}


# ======================================================
# 🤖 Deteção de intenção
# ======================================================

def detectar_intencao_confirmacao(texto: str):
    """Analisa texto e deteta se o utilizador quer confirmar."""
    texto_lower = texto.lower()

    if any(p in texto_lower for p in ["nós", "familia", "todos", "toda a familia"]):
        return {"tipo": "familia", "explicito": True, "nomes_mencionados": []}

    if any(p in texto_lower for p in ["miudos", "filhos", "crianças"]):
        return {"tipo": "filhos", "explicito": True, "nomes_mencionados": []}

    if any(p in texto_lower for p in ["só eu", "apenas eu", "eu sozinho"]):
        return {"tipo": "individual", "explicito": True, "nomes_mencionados": []}

    possiveis_nomes = re.findall(r'\b[A-Z][a-z]+\b', texto)
    if possiveis_nomes:
        return {"tipo": "especificos", "explicito": True, "nomes_mencionados": possiveis_nomes}

    if any(p in texto_lower for p in ["eu vou", "confirmo", "vou"]):
        return {"tipo": "individual", "explicito": False, "nomes_mencionados": []}

    return {"tipo": "desconhecido", "explicito": False, "nomes_mencionados": []}


# ======================================================
# 🔎 Execução direta para teste
# ======================================================

if __name__ == "__main__":
    print("🔧 Teste rápido ao sistema de confirmações (Qdrant)...")
    print("Confirmando Barbeitos...")
    resultado = confirmar_pessoa("Barbeitos")
    print(resultado)

    print("\nConfirmados atuais:")
    print(get_confirmados())

    print("\nEstatísticas:")
    print(get_estatisticas())
