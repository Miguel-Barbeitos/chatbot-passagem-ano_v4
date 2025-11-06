# -*- coding: utf-8 -*-
"""
Sistema de Confirmacoes integrado com Qdrant Cloud
Autor: Miguel + GPT
"""

import unicodedata
import re
from datetime import datetime
from modules import perfis_manager as pm

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
# 🧠 Interpretação semântica simples
# ======================================================

def interpretar_relacao_frase(frase: str):
    """
    Identifica frases do tipo:
    - 'A Isabel vai levar as filhas?'
    - 'O Jorge vem com a mulher?'
    - 'A Inês traz os irmãos?'
    Retorna {'pessoa': 'Isabel', 'relacao': 'filhos'} ou None.
    """
    texto = frase.lower()

    # Extrair possível nome próprio simples
    match_nome = re.search(r"(?:a|o)\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)", frase)
    nome = match_nome.group(1) if match_nome else None

    if not nome:
        return None

    if "filh" in texto:
        relacao = "filhos"
    elif "mulher" in texto or "esposa" in texto or "marido" in texto or "cônjuge" in texto:
        relacao = "conjuge"
    elif "irma" in texto or "irmão" in texto or "irmã" in texto:
        relacao = "irmaos"
    else:
        relacao = None

    if relacao:
        return {"pessoa": nome.capitalize(), "relacao": relacao}
    return None

# ======================================================
# 🔍 Ler e guardar confirmações diretamente no Qdrant
# ======================================================

def get_confirmados():
    """Retorna lista de nomes confirmados a partir do Qdrant."""
    try:
        return sorted(pm.get_confirmacoes_qdrant())
    except Exception as e:
        print(f"❌ Erro ao ler confirmados do Qdrant: {e}")
        return []

def get_estatisticas():
    """Gera estatísticas de confirmações (total, famílias completas, etc)."""
    try:
        confirmados = get_confirmados()
        total_confirmados = len(confirmados)
        familias = {}

        todos = pm.listar_todos_perfis()
        for p in todos:
            familia_id = p.get("familia_id")
            nome = p.get("nome")
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
    """Confirma um convidado individual ou a família inteira se indicado."""
    try:
        # Deteção automática de intenção familiar
        if isinstance(nome, str) and any(p in nome.lower() for p in ["família", "familia", "todos", "nós", "nos"]):
            return confirmar_familia_completa(confirmado_por or "Desconhecido")

        perfil = pm.buscar_perfil(nome)
        if not perfil:
            return {"sucesso": False, "mensagem": f"'{nome}' não está na lista de convidados.", "familia_sugerida": []}

        nome_real = perfil.get("nome")
        familia_id = perfil.get("familia_id")

        # Já confirmado?
        if perfil.get("confirmado"):
            return {"sucesso": True, "mensagem": f"{nome_real} já está confirmado.", "familia_sugerida": []}

        novos_dados = {
            "confirmado": True,
            "confirmado_por": confirmado_por or nome_real,
            "data_confirmacao": datetime.now().isoformat(),
        }

        atualizado = pm.atualizar_perfil(nome_real, novos_dados)
        if not atualizado:
            return {"sucesso": False, "mensagem": f"Erro ao confirmar {nome_real}", "familia_sugerida": []}

        familia = pm.listar_familia(familia_id)
        confirmados = pm.get_confirmacoes_qdrant()
        familia_nao_confirmada = [p["nome"] for p in familia if p["nome"] != nome_real and p["nome"] not in confirmados]

        return {
            "sucesso": True,
            "mensagem": f"🎉 {nome_real} confirmado com sucesso!",
            "familia_sugerida": familia_nao_confirmada,
        }

    except Exception as e:
        print(f"❌ Erro ao confirmar pessoa: {e}")
        return {"sucesso": False, "mensagem": f"Erro ao confirmar: {e}", "familia_sugerida": []}

def confirmar_familia_completa(nome_representante: str):
    """Confirma todos os membros da família do representante."""
    try:
        perfil = pm.buscar_perfil(nome_representante)
        if not perfil:
            return {"sucesso": False, "mensagem": f"Não encontrei '{nome_representante}'."}

        familia_id = perfil.get("familia_id")
        if not familia_id:
            return {"sucesso": False, "mensagem": f"{nome_representante} não pertence a uma família registada."}

        membros = pm.listar_familia(familia_id)
        confirmados = []
        erros = []

        for membro in membros:
            nome_m = membro.get("nome")
            ok = pm.atualizar_confirmacao_qdrant(nome_m, confirmado=True)
            if ok:
                confirmados.append(nome_m)
            else:
                erros.append(nome_m)

        msg = f"🎉 Família '{familia_id}' confirmada: " + ", ".join(confirmados)
        if erros:
            msg += f"\n⚠️ Falha ao confirmar: {', '.join(erros)}"

        return {"sucesso": True, "mensagem": msg, "confirmados": confirmados}

    except Exception as e:
        print(f"❌ Erro ao confirmar família: {e}")
        return {"sucesso": False, "mensagem": f"Erro ao confirmar família: {e}", "confirmados": []}

# ======================================================
# 🔍 Verificar confirmação individual
# ======================================================

def verificar_confirmacao_pessoa(pergunta: str):
    """
    Verifica se uma pessoa específica está confirmada no Qdrant.
    Agora também entende frases como:
    - 'A Isabel vai levar as filhas?'
    - 'O Jorge vem com a mulher?'
    """
    try:
        contexto = interpretar_relacao_frase(pergunta)

        # Caso simples (sem intenção relacional)
        if not contexto:
            perfil = pm.buscar_perfil(pergunta)
            if not perfil:
                return f"❌ Não encontrei ninguém chamado '{pergunta}' na lista de convidados."
            if perfil.get("confirmado"):
                return f"✅ {perfil.get('nome')} já confirmou presença!"
            else:
                return f"🙃 {perfil.get('nome')} ainda não confirmou presença."

        # Caso com relação (filhos, cônjuge, etc.)
        nome = contexto["pessoa"]
        relacao = contexto["relacao"]

        perfil = pm.buscar_perfil(nome)
        if not perfil:
            return f"❌ Não encontrei ninguém chamado '{nome}' na lista de convidados."

        relacoes = perfil.get("relacoes", {})
        relacionados = relacoes.get(relacao, [])

        if not relacionados:
            return f"🙃 {nome} não indicou se vem acompanhado/a dos {relacao}."

        confirmados = pm.get_confirmacoes_qdrant()
        confirmados_relacionados = [r for r in relacionados if r in confirmados]

        if confirmados_relacionados:
            return f"👨‍👩‍👧 Sim, {nome} vem com {', '.join(confirmados_relacionados)}!"
        else:
            return f"❌ {nome} ainda não confirmou se vem com os {relacao}."

    except Exception as e:
        print(f"❌ Erro ao verificar confirmação: {e}")
        return f"⚠️ Erro ao verificar confirmação ({pergunta})."

# ======================================================
# 🔎 Execução direta para teste
# ======================================================

if __name__ == "__main__":
    print("🔧 Teste rápido ao sistema de confirmações (Qdrant)...")
    print(verificar_confirmacao_pessoa("A Isabel vai levar as filhas?"))
    print(verificar_confirmacao_pessoa("O Jorge vem com a mulher?"))
