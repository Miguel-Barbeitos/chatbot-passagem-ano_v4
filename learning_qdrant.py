import os
import json
import random
import hashlib
import numpy as np
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer, util

# =====================================================
# ⚙️ CONFIGURAÇÃO GERAL
# =====================================================
COLLECTION_NAME = "chatbot_festa"
BASE_DIR = os.path.dirname(__file__)
QDRANT_PATH = os.path.join(BASE_DIR, "qdrant_data")
DATA_PATH = os.path.join(BASE_DIR, "data", "event.json")

print(f"📂 Qdrant ativo em: {QDRANT_PATH}")
print(f"📄 Ficheiro de contexto: {DATA_PATH}")

# =====================================================
# 🧠 MODELO DE EMBEDDINGS
# =====================================================
print("🧠 A inicializar modelo de embeddings...")
model = SentenceTransformer("intfloat/multilingual-e5-base")
print("✅ Modelo carregado com sucesso.")

# =====================================================
# 💾 CONEXÃO AO QDRANT
# =====================================================
def inicializar_qdrant():
    """Inicializa Qdrant local, criando coleção se necessário"""
    if not os.path.exists(QDRANT_PATH):
        os.makedirs(QDRANT_PATH, exist_ok=True)

    client = QdrantClient(path=QDRANT_PATH)
    collections = [c.name for c in client.get_collections().collections]

    if COLLECTION_NAME not in collections:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE)
        )
        print("✨ Coleção Qdrant criada.")
    else:
        print("🔗 Coleção Qdrant conectada.")
    return client

client = inicializar_qdrant()
print(f"🚀 Qdrant ativo (Streamlit): {os.path.abspath(QDRANT_PATH)}")

# =====================================================
# 📂 CONTEXTO BASE (event.json)
# =====================================================
def get_contexto_base():
    """Carrega e devolve o contexto base da festa"""
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            dados = json.load(f)
        texto = []
        for k, v in dados.items():
            if isinstance(v, bool):
                texto.append(f"{k.replace('_', ' ')}: {'sim' if v else 'não'}")
            elif isinstance(v, list):
                texto.append(f"{k.replace('_', ' ')}: {', '.join(v)}")
            else:
                texto.append(f"{k.replace('_', ' ')}: {v}")
        return "\n".join(texto)
    except Exception as e:
        print(f"⚠️ Erro ao ler contexto base: {e}")
        return "Informações da festa indisponíveis."

# =====================================================
# 💾 GUARDAR MENSAGEM
# =====================================================
def guardar_mensagem(user, pergunta, resposta, contexto="geral", perfil=None):
    """Guarda interação geral no Qdrant"""
    try:
        vector = model.encode(pergunta).tolist()
        payload = {
            "user": user,
            "pergunta": pergunta,
            "resposta": resposta,
            "contexto": contexto,
            "perfil": perfil.get("personalidade", "desconhecida") if perfil else "desconhecido",
        }
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=random.randint(0, 1_000_000_000),
                    vector=vector,
                    payload=payload,
                )
            ],
        )
        print(f"💾 Mensagem guardada para {user} ({contexto})")
    except Exception as e:
        print(f"❌ Erro ao guardar mensagem: {e}")


# =====================================================
# 🧠 DETEÇÃO SIMPLES DE INTENÇÃO
# =====================================================
def identificar_intencao(pergunta: str) -> str:
    """
    Deteta a intenção principal da pergunta com base em palavras-chave simples.
    (Versão leve para uso no app.py)
    """
    p = pergunta.lower()

    if any(t in p for t in ["olá", "ola", "bom dia", "boa tarde", "boa noite"]):
        return "saudacao"
    if any(t in p for t in ["quem vai", "confirmou", "confirmacoes", "quantas pessoas"]):
        return "confirmacoes"
    if any(t in p for t in ["onde", "local", "sitio", "morada"]):
        return "local"
    if any(t in p for t in ["hora", "quando", "que horas", "começa"]):
        return "hora"
    if any(t in p for t in ["wifi", "internet", "rede"]):
        return "wifi"
    if any(t in p for t in ["roupa", "dress", "vestir", "codigo", "cor"]):
        return "roupa"
    if any(t in p for t in ["levar", "trazer", "preciso levar"]):
        return "logistica"
    if any(t in p for t in ["futebol", "benfica", "porto", "sporting", "jogo"]):
        return "futebol"
    if any(t in p for t in ["piada", "anedota", "brincadeira"]):
        return "piadas"
    if any(t in p for t in ["comida", "jantar", "menu", "sobremesa"]):
        return "comida"
    if any(t in p for t in ["bebida", "cerveja", "vinho", "champanhe", "cocktail"]):
        return "bebida"

    return "geral"


# =====================================================
# ✅ CONFIRMAÇÕES
# =====================================================
def guardar_confirmacao(nome: str):
    """
    Guarda a confirmação de presença no Qdrant sem duplicar.
    """
    try:
        # Verificar se já existe confirmação
        existentes, _ = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="contexto", match=models.MatchValue(value="confirmacoes")
                    ),
                    models.FieldCondition(
                        key="user", match=models.MatchValue(value=nome)
                    ),
                ]
            ),
            limit=1,
        )

        if existentes:
            print(f"ℹ️ {nome} já estava confirmado.")
            return

        # Inserir nova confirmação
        vector = np.zeros(768).tolist()
        payload = {
            "user": nome,
            "resposta": f"{nome} confirmou presença 🎉",
            "contexto": "confirmacoes",
        }

        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=random.randint(0, 1_000_000_000),
                    vector=vector,
                    payload=payload,
                )
            ],
        )

        print(f"✅ {nome} registado como confirmado no Qdrant.")
    except Exception as e:
        print(f"⚠️ Erro ao guardar confirmação: {e}")

def get_confirmacoes():
    """
    Lê as confirmações atuais diretamente do Qdrant.
    """
    try:
        pontos, _ = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="contexto", match=models.MatchValue(value="confirmacoes")
                    )
                ]
            ),
            limit=200,
        )

        confirmados = []
        for p in pontos:
            nome = p.payload.get("user")
            if nome and nome not in confirmados:
                confirmados.append(nome)

        print(f"📋 Confirmados no Qdrant: {confirmados}")
        return sorted(confirmados)
    except Exception as e:
        print(f"⚠️ Erro ao obter confirmações: {e}")
        return []

def limpar_duplicados_antigos():
    """Remove confirmações duplicadas no Qdrant (mantém apenas 1 por utilizador)."""
    try:
        print("🔍 A verificar duplicados de confirmações...")
        resultados = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[models.FieldCondition(key="contexto", match=models.MatchValue(value="confirmacoes"))]
            ),
            limit=500,
        )

        vistos = {}
        apagar_ids = []

        # Percorre todos os registos
        for ponto in resultados[0]:
            if not ponto.payload or "user" not in ponto.payload:
                continue
            user = ponto.payload["user"]

            if user in vistos:
                apagar_ids.append(ponto.id)  # duplicado → marca para apagar
            else:
                vistos[user] = ponto.id  # mantém o primeiro

        if not apagar_ids:
            print("✅ Nenhum duplicado encontrado.")
            return

        # Apaga os duplicados detetados
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=models.PointIdsList(points=apagar_ids),
        )

        print(f"🧹 {len(apagar_ids)} duplicados removidos com sucesso.")
        print(f"✅ Utilizadores únicos agora: {list(vistos.keys())}")

    except Exception as e:
        print(f"⚠️ Erro ao limpar duplicados: {e}")   

def exportar_confirmacoes_json(caminho=None):
    """Exporta todas as confirmações atuais do Qdrant para um ficheiro JSON."""
    try:
        # Caminho por defeito → dentro da pasta data/
        if caminho is None:
            os.makedirs("data", exist_ok=True)
            caminho = os.path.join("data", "confirmados.json")

        confirmados = get_confirmacoes()

        if not confirmados:
            print("⚠️ Nenhum confirmado encontrado — nada para exportar.")
            return

        dados = {
            "total_confirmados": len(confirmados),
            "confirmados": confirmados
        }

        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)

        print(f"💾 Exportação concluída: {caminho}")
        print(f"✅ {len(confirmados)} nomes guardados com sucesso.")

    except Exception as e:
        print(f"⚠️ Erro ao exportar confirmações: {e}")

def importar_confirmacoes_json(caminho=None):
    """Importa confirmações do ficheiro data/confirmados.json para o Qdrant."""
    try:
        # Caminho por defeito
        if caminho is None:
            caminho = os.path.join("data", "confirmados.json")

        # Verifica se o ficheiro existe
        if not os.path.exists(caminho):
            print(f"⚠️ Ficheiro não encontrado: {caminho}")
            return

        # Carrega o ficheiro JSON
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)

        confirmados = dados.get("confirmados", [])
        if not confirmados:
            print("⚠️ Nenhum nome encontrado no ficheiro — nada para importar.")
            return

        # Confirmações já existentes no Qdrant (para evitar duplicados)
        existentes = set(get_confirmacoes())

        novos = [n for n in confirmados if n not in existentes]
        if not novos:
            print("ℹ️ Todos os nomes já estavam registados — nada para adicionar.")
            return

        # Inserção dos novos nomes
        for nome in novos:
            vector = np.zeros(768).tolist()
            payload = {"user": nome, "resposta": f"{nome} confirmou presença 🎉", "contexto": "confirmacoes"}
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=[models.PointStruct(id=random.randint(0, 1_000_000_000), vector=vector, payload=payload)],
            )

        print(f"✅ {len(novos)} novas confirmações importadas com sucesso:")
        for n in novos:
            print(f"   → {n}")

    except Exception as e:
        print(f"❌ Erro ao importar confirmações: {e}")

# =====================================================
# 🔍 BUSCA SEMÂNTICA
# =====================================================
def procurar_resposta_semelhante(pergunta, contexto=None, limite_conf=0.6, top_k=3):
    """Procura uma resposta relevante no histórico"""
    try:
        vector = model.encode(pergunta).tolist()
        filtro = None
        if contexto:
            filtro = models.Filter(
                must=[models.FieldCondition(key="contexto", match=models.MatchValue(value=contexto))]
            )

        resultado = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=vector,
            query_filter=filtro,
            limit=top_k,
        )

        if resultado and resultado[0].score >= limite_conf:
            return resultado[0].payload.get("resposta")
    except Exception as e:
        print(f"❌ Erro ao procurar resposta: {e}")
    return None
 


# =====================================================
# 🧹 LIMPAR COLEÇÃO (APENAS USO MANUAL)
# =====================================================
def limpar_qdrant():
    """Apaga toda a coleção do Qdrant e recria-a (apenas usar manualmente)."""
    from qdrant_client import models

    try:
        client.delete_collection(COLLECTION_NAME)
        print("🧹 Coleção Qdrant apagada.")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE)
        )
        print("✨ Nova coleção criada.")
    except Exception as e:
        print(f"Erro ao limpar Qdrant: {e}")
