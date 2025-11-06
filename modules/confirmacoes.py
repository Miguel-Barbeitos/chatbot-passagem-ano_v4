# -*- coding: utf-8 -*-
"""
Sistema de Confirmacoes integrado com Qdrant Cloud
"""

import unicodedata
from datetime import datetime
from modules import perfis_manager as pm


def normalizar_nome(nome: str) -> str:
    if not isinstance(nome, str):
        return ""
    import unicodedata
    nome = unicodedata.normalize('NFKD', nome)
    nome = ''.join(c for c in nome if not unicodedata.combining(c))
    return nome.lower().strip()


# ======================================================
# ✅ Confirmações e relações
# ======================================================
def verificar_confirmacao_pessoa(nome: str):
    """Verifica se uma pessoa ou familiares estão confirmados."""
    try:
        perfil = pm.buscar_perfil(nome)
        if not perfil:
            return f"❌ Não encontrei ninguém chamado '{nome}' na lista de convidados."

        nome_real = perfil.get("nome")
        relacoes = perfil.get("relacoes", {})
        confirmados = pm.get_confirmacoes_qdrant()

        # 1️⃣ Confirmação individual
        if perfil.get("confirmado"):
            resposta = f"✅ {nome_real} já confirmou presença!"
        else:
            resposta = f"🙃 {nome_real} ainda não confirmou presença."

        # 2️⃣ Relações (ex: filhos, cônjuge)
        if relacoes:
            filhos = relacoes.get("filhos", [])
            conjuge = relacoes.get("conjuge")
            extras = []

            if filhos:
                filhos_confirmados = [f for f in filhos if f in confirmados]
                if filhos_confirmados:
                    extras.append(f"👧 Filhos confirmados: {', '.join(filhos_confirmados)}")
                else:
                    extras.append("👧 Nenhum filho confirmado ainda.")

            if conjuge:
                if conjuge in confirmados:
                    extras.append(f"❤️ {conjuge} também confirmou.")
                else:
                    extras.append(f"❤️ {conjuge} ainda não confirmou.")

            if extras:
                resposta += "\n" + "\n".join(extras)

        return resposta
    except Exception as e:
        print(f"❌ Erro ao verificar confirmação: {e}")
        return f"⚠️ Erro ao verificar confirmação de {nome}."
