# -*- coding: utf-8 -*-
"""
Módulo de geração de respostas LLM (Groq + Qdrant)
Integra-se com perfis e aprendizagem personalizada.
"""

import os
import random
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
import streamlit as st
from learning_qdrant import get_model  # ✅ import do modelo correto


# ============================================================
# 🔑 CONFIGURAÇÃO DE ACESSO AO QDRANT
# ============================================================

def get_qdrant_client():
    """Inicializa o cliente Qdrant com credenciais de Streamlit ou ambiente."""
    try:
        qdrant_url = st.secrets.get("QDRANT_URL")
        qdrant_key = st.secrets.get("QDRANT_API_KEY")
        if qdrant_url and qdrant_key:
            client = QdrantClient(url=qdrant_url, api_key=qdrant_key, timeout=10.0)
            print(f"☁️  Conectado ao Qdrant Cloud: {qdrant_url}")
            return client
    except Exception:
        pass

    # fallback
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_key = os.getenv("QDRANT_API_KEY")
    client = QdrantClient(url=qdrant_url, api_key=qdrant_key, timeout=10.0)
    print(f"☁️  Conectado (fallback): {qdrant_url}")
    return client


# ============================================================
# 🤖 FUNÇÃO PRINCIPAL
# ============================================================

def gerar_resposta_llm(
    pergunta: str,
    perfil_completo: dict = None,
    contexto_base: str = "",
    contexto_conversa: str = "",
    ultima_quinta: str = None,
):
    """
    Gera uma resposta personalizada baseada no perfil do utilizador.
    Protege contra perfil_completo == None.
    """

    perfil = perfil_completo or {}
    nome = perfil.get("nome", "Utilizador")
    p = pergunta.lower().strip()

    # ============================================================
    # 🎭 PERSONALIZAÇÃO DO ESTILO DE RESPOSTA
    # ============================================================

    personalidade = perfil.get("personalidade", {})
    humor = personalidade.get("humor", 5)
    formalidade = personalidade.get("formalidade", 5)
    detalhismo = personalidade.get("detalhismo", 5)
    emojis = personalidade.get("emojis", 4)
    paciencia = personalidade.get("paciencia", 5)

    emoji_map = {1: "", 3: "🙂", 5: "😊", 7: "😄", 9: "🤩"}
    emoji = emoji_map.get(emojis, "🙂")

    # ============================================================
    # 🔍 DETEÇÃO DE INTENÇÃO SIMPLES
    # ============================================================

    if "olá" in p or "ola" in p:
        return f"Olá {nome}! 👋 Como estás?"

    if "obrigado" in p:
        return f"De nada, {nome}! {emoji}"

    if any(x in p for x in ["piada", "anedota", "conta-me algo engraçado"]):
        piadas = [
            "Sabes por que o computador foi ao médico? Porque estava com um vírus! 🤒",
            "O que é um vegetariano que come carne por engano? Um erro biológico! 😂",
            "Como se chama um boi a dormir? Bulldormir! 😴",
        ]
        return random.choice(piadas)

    if any(x in p for x in ["data", "hoje", "dia"]):
        hoje = datetime.now().strftime("%d/%m/%Y")
        return f"Hoje é {hoje}. Faltam poucos dias para a festa! 🎉"

    if "tempo" in p and "festa" in p:
        return "Ainda não sabemos a previsão meteorológica para o dia, mas espero sol e boa disposição! ☀️"

    # ============================================================
    # 💡 CONTEXTO DE QUINTAS
    # ============================================================

    if any(x in p for x in ["quinta", "local", "reserva"]):
        return (
            "Temos várias quintas contactadas e algumas disponíveis! 🌿\n"
            "Podes perguntar, por exemplo:\n"
            "• 'Quais as quintas contactadas?'\n"
            "• 'Já temos quinta confirmada?'\n"
            "• 'Mostra todas as quintas disponíveis.'"
        )

    # ============================================================
    # 🎯 CONTEXTO DE CONFIRMAÇÕES
    # ============================================================

    if any(x in p for x in ["quem vai", "quem confirmou", "quem já respondeu"]):
        try:
            from modules.confirmacoes import get_confirmados
            confirmados = get_confirmados()
            if confirmados:
                lista = ", ".join(confirmados[:10])
                extra = f" ... e mais {len(confirmados) - 10}" if len(confirmados) > 10 else ""
                return f"🎉 Até agora confirmaram: {lista}{extra}."
            else:
                return "😅 Ainda ninguém confirmou presença."
        except Exception as e:
            print(f"Erro ao aceder confirmações: {e}")
            return "Não consegui verificar as confirmações agora."

    # ============================================================
    # 🧠 CONTEXTO DE APRENDIZAGEM VIA QDRANT
    # ============================================================

    try:
        client = get_qdrant_client()
        collection = "chatbot_festa"

        # Gerar embedding real de 768 dimensões
        model = get_model()
        vector = model.encode(pergunta).tolist()
        if len(vector) != 768:
            print(f"⚠️ Corrigindo vetor incorreto (dim {len(vector)}) → 768")
            vector = (vector + [0.0] * 768)[:768]

        resultados, _ = client.scroll(collection_name=collection, limit=1)
        memoria = resultados[0].payload.get("memoria", "") if resultados else ""

        contexto = f"{contexto_base}\n{contexto_conversa}\n{memoria}"

        resposta = f"{emoji} {random.choice(['Boa pergunta!', 'Interessante!', 'Vamos ver...'])} "

        if detalhismo > 6:
            resposta += f"Não tenho dados diretos sobre '{pergunta}', mas posso tentar aprender mais se quiseres. 😉"
        else:
            resposta += f"Ainda não sei a resposta exata, mas posso investigar!"

        # ✅ Upsert com vetor de 768 dimensões correto
        client.upsert(
            collection_name=collection,
            points=[
                PointStruct(
                    id=random.randint(1000, 9999),
                    vector=vector,
                    payload={
                        "pergunta": pergunta,
                        "resposta": resposta,
                        "data": datetime.now().isoformat(),
                        "utilizador": nome,
                    },
                )
            ],
        )

        return resposta

    except Exception as e:
        print(f"⚠️ Falha Qdrant: {e}")
        pass

    # ============================================================
    # 🗣️ FALLBACK FINAL
    # ============================================================

    respostas_genericas = [
        f"Hmm... não tenho essa informação, {nome}. {emoji}",
        f"Boa pergunta, {nome}! Ainda estou a aprender sobre isso. 😉",
        f"Não tenho a certeza, mas posso tentar descobrir! 🔍",
        f"Desculpa, {nome}, não encontrei nada sobre isso agora. 🤔",
    ]
    return random.choice(respostas_genericas)
