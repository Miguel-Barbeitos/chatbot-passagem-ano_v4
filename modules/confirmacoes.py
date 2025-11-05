# -*- coding: utf-8 -*-
"""
Sistema de Confirmações centralizado no Qdrant
Migração completa do JSON local para Qdrant
"""

import unicodedata
import re
from datetime import datetime
from modules.perfis_manager import (
    get_confirmacoes_qdrant,
    atualizar_confirmacao_qdrant,
    buscar_perfil,
    listar_familia
)

# ============================================================
# 🔧 FUNÇÕES AUXILIARES
# ============================================================

def normalizar_nome(nome):
    """Normaliza nome para comparação (remove acentos, minúsculas)"""
    if not isinstance(nome, str):
        return ""
    nome = unicodedata.normalize('NFKD', nome)
    nome = ''.join(c for c in nome if not unicodedata.combining(c))
    return nome.lower().strip()


# ============================================================
# ✅ FUNÇÕES PRINCIPAIS DE CONFIRMAÇÃO
# ============================================================

def confirmar_pessoa(nome, confirmado_por=None, acompanhantes=None):
    """
    Confirma uma pessoa e grava diretamente no Qdrant
    """
    try:
        perfil = buscar_perfil(nome)

        # Se não encontrou, tenta com nome normalizado
        if not perfil:
            nome_norm = normalizar_nome(nome)
            candidatos = get_confirmacoes_qdrant()
            for p in candidatos:
                if normalizar_nome(p.get("nome", "")) == nome_norm:
                    perfil = p
                    break

        if not perfil:
            return {
                "sucesso": False,
                "mensagem": f"'{nome}' não está na lista de convidados.",
                "familia_sugerida": []
            }

        nome_real = perfil["nome"]

        # Atualiza no Qdrant
        atualizar_confirmacao_qdrant(
            nome_real,
            confirmado=True,
            acompanhantes=acompanhantes or []
        )

        # Sugere outros membros da família
        familia_id = perfil.get("familia_id")
        familia_sugerida = []
        if familia_id:
            familia = listar_familia(familia_id)
            familia_sugerida = [
                p["nome"]
                for p in familia
                if p["nome"] != nome_real and not p.get("confirmado")
            ]

        return {
            "sucesso": True,
            "mensagem": f"✅ {nome_real} confirmado no Qdrant",
            "familia_sugerida": familia_sugerida
        }

    except Exception as e:
        print(f"[ERRO] confirmar_pessoa: {e}")
        return {"sucesso": False, "mensagem": "Erro ao confirmar", "familia_sugerida": []}


def confirmar_familia_completa(familia_id, confirmado_por=None):
    """Confirma todos os membros de uma família"""
    try:
        familia = listar_familia(familia_id)
        if not familia:
            return {"sucesso": False, "mensagem": "Família não encontrada", "confirmados": []}

        confirmados = []
        for membro in familia:
            res = confirmar_pessoa(membro["nome"], confirmado_por)
            if res["sucesso"]:
                confirmados.append(membro["nome"])

        return {
            "sucesso": True,
            "mensagem": f"Família confirmada: {', '.join(confirmados)}",
            "confirmados": confirmados
        }

    except Exception as e:
        print(f"[ERRO] confirmar_familia_completa: {e}")
        return {"sucesso": False, "mensagem": "Erro ao confirmar família", "confirmados": []}


def remover_confirmacao(nome):
    """Remove confirmação no Qdrant"""
    try:
        perfil = buscar_perfil(nome)
        if not perfil:
            return {"sucesso": False, "mensagem": f"{nome} não encontrado no Qdrant"}

        atualizar_confirmacao_qdrant(nome, confirmado=False)
        return {"sucesso": True, "mensagem": f"{nome} removido da lista de confirmados"}

    except Exception as e:
        print(f"[ERRO] remover_confirmacao: {e}")
        return {"sucesso": False, "mensagem": "Erro ao remover confirmação"}


# ============================================================
# 📊 FUNÇÕES DE CONSULTA
# ============================================================

def get_confirmados():
    """Lista de confirmados diretamente do Qdrant"""
    try:
        confirmados = get_confirmacoes_qdrant()
        return sorted([p["nome"] for p in confirmados])
    except Exception as e:
        print(f"[ERRO] get_confirmados: {e}")
        return []


def get_estatisticas():
    """Estatísticas de confirmações (Qdrant central)"""
    try:
        confirmados = get_confirmacoes_qdrant()
        total_confirmados = len(confirmados)
        total_pessoas = sum(1 + len(c.get("acompanhantes", [])) for c in confirmados)
        total_convidados = 35  # pode vir de evento.json

        return {
            "total_confirmados": total_confirmados,
            "total_pessoas": total_pessoas,
            "total_convidados": total_convidados,
            "taxa_confirmacao": round((total_confirmados / total_convidados * 100), 1)
            if total_convidados else 0
        }
    except Exception as e:
        print(f"[ERRO] get_estatisticas: {e}")
        return {"total_confirmados": 0, "total_pessoas": 0, "taxa_confirmacao": 0}


# ============================================================
# 🧠 DETEÇÃO DE INTENÇÃO DE CONFIRMAÇÃO
# ============================================================

def detectar_intencao_confirmacao(texto):
    """Analisa texto e tenta inferir intenção de confirmação"""
    texto_lower = texto.lower()

    if any(p in texto_lower for p in ["nós", "familia", "todos", "toda a familia"]):
        return {"tipo": "familia", "explicito": True, "nomes_mencionados": []}

    if any(p in texto_lower for p in ["miudos", "filhos", "crianças"]):
        return {"tipo": "filhos", "explicito": True, "nomes_mencionados": []}

    if any(p in texto_lower for p in ["só eu", "apenas eu", "eu sozinho"]):
        return {"tipo": "individual", "explicito": True, "nomes_mencionados": []}

    possiveis_nomes = re.findall(r'\b[A-ZÁÉÍÓÚÂÊÎÔÛÃÕ][a-záéíóúâêîôûãõç]+\b', texto)
    if possiveis_nomes:
        return {"tipo": "especificos", "explicito": True, "nomes_mencionados": possiveis_nomes}

    if any(p in texto_lower for p in ["eu vou", "confirmo", "vou"]):
        return {"tipo": "individual", "explicito": False, "nomes_mencionados": []}

    return {"tipo": "desconhecido", "explicito": False, "nomes_mencionados": []}
def verificar_confirmacao_pessoa(nome):
    """Verifica se uma pessoa está confirmada no Qdrant"""
    from modules.perfis_manager import buscar_perfil
    try:
        perfil = buscar_perfil(nome)
        if not perfil:
            return f"❓ Não encontrei ninguém chamado {nome} na lista de convidados."

        if perfil.get("confirmado"):
            return f"✅ Sim, {perfil['nome']} já confirmou presença!"
        else:
            return f"❌ {perfil['nome']} ainda não confirmou."
    except Exception as e:
        print(f"[ERRO] verificar_confirmacao_pessoa: {e}")
        return "⚠️ Erro ao verificar confirmação."

# ============================================================
# 🔍 TESTE LOCAL
# ============================================================

if __name__ == "__main__":
    print("🔧 Teste rápido ao sistema de confirmações (Qdrant central)\n")

    print("Confirmando Isabel...")
    r = confirmar_pessoa("Isabel")
    print(r["mensagem"])

    print("\nLista de confirmados:")
    for nome in get_confirmados():
        print(" -", nome)

    print("\nEstatísticas:")
    print(get_estatisticas())




