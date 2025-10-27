# llm_groq.py
import os
import json
import requests
import sqlite3
import pandas as pd
import streamlit as st

from services.learning_qdrant import procurar_resposta_semelhante

# =====================================================
# ⚙️ CONFIGURAÇÃO GERAL
# =====================================================
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))
if not GROQ_API_KEY:
    raise ValueError("❌ Falta a variável de ambiente GROQ_API_KEY. Define-a no Streamlit secrets ou no ambiente local.")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

DATA_PATH = "data/event.json"

# =====================================================
# 📂 LEITURA DO CONTEXTO BASE (event.json)
# =====================================================
def carregar_contexto_base():
    """Lê o contexto base do JSON da festa"""
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            dados = json.load(f)
        contexto = []
        for k, v in dados.items():
            if isinstance(v, bool):
                contexto.append(f"{k.replace('_', ' ')}: {'sim' if v else 'não'}")
            elif isinstance(v, list):
                contexto.append(f"{k.replace('_', ' ')}: {', '.join(v)}")
            elif isinstance(v, dict):
                sub = ", ".join(f"{sk}: {sv}" for sk, sv in v.items())
                contexto.append(f"{k}: {sub}")
            else:
                contexto.append(f"{k.replace('_', ' ')}: {v}")
        return "\n".join(contexto)
    except Exception as e:
        print(f"⚠️ Erro ao carregar contexto base: {e}")
        return "Informações da festa indisponíveis."

# =====================================================
# 🔍 DETEÇÃO DE PERGUNTAS SOBRE QUINTAS (MELHORADA)
# =====================================================
def normalizar_zona(texto: str) -> str:
    """Normaliza nome de zona para fazer buscas flexíveis"""
    import unicodedata
    import re
    
    # Remove acentos
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    
    # Lowercase
    texto = texto.lower().strip()
    
    # Remove plural (s final)
    texto = texto.rstrip('s')
    
    # Remove pontuação
    texto = re.sub(r'[^\w\s]', '', texto)
    
    return texto

def e_pergunta_de_quintas(pergunta: str) -> bool:
    """Deteta se a pergunta é sobre quintas / base de dados."""
    p = pergunta.lower()
    chaves = [
        # Perguntas diretas
        "quinta", "quintas", "que quintas", "quais quintas", "quantas quintas",
        # Estado e contactos
        "contactadas", "contactaste", "responderam", "falamos", "vimos",
        # Características
        "piscina", "capacidade", "custo", "barata", "animais", "resposta", 
        "zona", "morada", "opcoes", "opções", "disponivel", "disponível",
        "preco", "preço", "churrasqueira", "snooker", "estado", "procura",
        # Quantificadores
        "quantas", "quais", "lista", "nomes"
    ]
    return any(c in p for c in chaves)

def e_pergunta_estado(pergunta: str) -> bool:
    """Deteta perguntas sobre o estado das quintas (porquê, resposta, atualização)."""
    termos = ["porquê", "porque", "motivo", "estado", "respondeu", "atualização", 
              "contactaste", "falaste", "ja vimos", "já vimos", "progresso"]
    return any(t in pergunta.lower() for t in termos)

# =====================================================
# 🤖 GERAR SQL AUTOMATICAMENTE
# =====================================================
def gerar_sql_da_pergunta(pergunta: str) -> str:
    """Usa o LLM para gerar um SQL seguro (apenas SELECT)."""
    schema = """
    Tabela: quintas
    
    Colunas disponíveis:
    - nome (TEXT): Nome da quinta
    - zona (TEXT): Zona/região (ex: Lisboa, Alentejo, Comporta)
    - morada (TEXT): Morada completa
    - email (TEXT): Email de contacto
    - telefone (TEXT): Número de telefone
    - website (TEXT): Website da quinta (ex: "link", endereço web")
    - estado (TEXT): Estado do contacto (ex: "Contactada", "Aguarda resposta", "Respondeu")
    - resposta (TEXT): Resposta da quinta
    - capacidade_43 (TEXT): Se aceita 43 pessoas
    - custo_4500 (TEXT): Custo para evento
    - estimativa_custo (TEXT): Estimativa de preço
    - capacidade_confirmada (TEXT): Capacidade confirmada
    - ultima_resposta (TEXT): Data da última resposta
    - proposta_tarifaria (TEXT): Proposta de preços
    - unidades_detalhe (TEXT): Detalhes das unidades
    - num_unidades (TEXT): Número de unidades/quartos
    - observacao_unidades (TEXT): Observações sobre unidades
    - custo_total (REAL): Custo total em euros
    - resumo_resposta (TEXT): Resumo da resposta recebida
    - observacoes (TEXT): Observações gerais
    - notas_calculo (TEXT): Notas sobre cálculos de preço
    
    NOTA: Todos os campos são TEXT exceto custo_total que é REAL (numérico).
    """

    prompt_sql = f"""
Gera APENAS o SQL (SELECT ...) para responder à pergunta.
SQL deve ser simples, compatível com SQLite e usar apenas as colunas listadas.

Pergunta: "{pergunta}"

{schema}

Exemplos de perguntas → SQL correto:

1. "Quantas quintas já contactámos?" 
   → SELECT COUNT(*) as total FROM quintas

2. "Que quintas já contactámos?" ou "Lista de quintas"
   → SELECT nome, zona, morada FROM quintas LIMIT 20

3. "Quantas quintas já vimos?"
   → SELECT COUNT(*) as total FROM quintas

4. "Quintas na zona de Lisboa" ou "Quintas em Lisboa"
   → SELECT nome, zona, morada FROM quintas WHERE zona LIKE '%Lisboa%'

5. "Quintas no Porto" ou "Quintas na zona do Porto"
   → SELECT nome, zona, morada FROM quintas WHERE zona LIKE '%Porto%'

6. "Quintas mais baratas" ou "Qual a mais barata"
   → SELECT nome, zona, custo_total FROM quintas WHERE custo_total IS NOT NULL AND custo_total > 0 ORDER BY custo_total ASC LIMIT 5

7. "Quintas que responderam" ou "Quantas responderam"
   → SELECT COUNT(*) as total FROM quintas WHERE estado LIKE '%Respondeu%' OR resposta IS NOT NULL

8. "Qual a capacidade das quintas"
   → SELECT nome, zona, capacidade_43, capacidade_confirmada FROM quintas

9. "Quintas com mais de 40 pessoas" ou "Capacidade para 43"
   → SELECT nome, zona, capacidade_43, capacidade_confirmada FROM quintas WHERE capacidade_43 LIKE '%sim%' OR capacidade_43 LIKE '%Sim%'

REGRAS IMPORTANTES:
- Para pesquisas de texto use LIKE '%texto%' (case insensitive)
- Para contar use COUNT(*) as total
- Para preços use custo_total (REAL) e WHERE custo_total IS NOT NULL
- LIMIT 20 para listas grandes
- Apenas SELECT - nunca UPDATE, DELETE, INSERT ou DROP

Gera apenas o SQL, sem explicações.
"""

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "És um assistente que converte linguagem natural em SQL seguro (apenas SELECT). Responde APENAS com o SQL, sem explicações."},
            {"role": "user", "content": prompt_sql},
        ],
        "temperature": 0.0,
        "max_tokens": 150,
    }

    try:
        resp = requests.post(GROQ_URL, headers=headers, json=data, timeout=20)
        query = resp.json()["choices"][0]["message"]["content"].strip()
        
        # Remove markdown se existir
        if "```sql" in query:
            query = query.split("```sql")[1].split("```")[0].strip()
        elif "```" in query:
            query = query.split("```")[1].split("```")[0].strip()
        
        # Remove quebras de linha extras
        query = " ".join(query.split())
        
        if query.lower().startswith("select"):
            print(f"✅ SQL gerado: {query}")
            return query
        else:
            print(f"⚠️ SQL inválido gerado: {query}")
    except Exception as e:
        print(f"⚠️ Erro a gerar SQL: {e}")
    return None

# =====================================================
# 🧠 EXECUTAR SQL NO SQLITE
# =====================================================
def executar_sql(query: str):
    """Executa um SELECT no SQLite e devolve os resultados como lista de dicionários."""
    try:
        conn = sqlite3.connect("data/quintas.db")
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"⚠️ Erro ao executar SQL: {e}")
        return []

# =====================================================
# 💬 GERAR RESPOSTA NATURAL A PARTIR DOS DADOS
# =====================================================
def gerar_resposta_dados_llm(pergunta, dados):
    """Usa o LLM para transformar os resultados do SQL em texto natural."""
    json_data = json.dumps(dados, ensure_ascii=False, indent=2)
    
    prompt = f"""
Transforma estes dados JSON numa resposta breve e natural à pergunta "{pergunta}".

⚠️ REGRAS CRÍTICAS:
- USA APENAS OS DADOS FORNECIDOS - NUNCA inventes informação
- Se os dados estiverem vazios ou incompletos, diz isso claramente
- Responde em Português de Portugal, num tom simpático e direto
- Máximo 3 frases
- Se forem muitos resultados, menciona os 3-4 mais relevantes
- Inclui detalhes importantes (zona, preço, capacidade) quando relevante
- Lembra que ainda não há quinta fechada, mas já há várias opções
- Se perguntarem por características que não existem nos dados (como "Porto"), menciona que não há ou que são poucas

Dados fornecidos:
{json_data}

IMPORTANTE: Se os dados não tiverem a informação pedida, diz "Não encontrei essa informação específica" em vez de inventar.
"""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "És um assistente que transforma dados estruturados em respostas naturais. NUNCA inventes informação que não está nos dados fornecidos."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,  # Reduzido para ser mais factual
        "max_tokens": 200,
    }
    try:
        resp = requests.post(GROQ_URL, headers=headers, json=data, timeout=20)
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"⚠️ Erro a gerar resposta natural: {e}")
        return "Não consegui interpretar os dados agora 😅"

# =====================================================
# 🎆 GERAÇÃO DE RESPOSTAS NATURAIS (FESTA OU QUINTAS)
# =====================================================
def gerar_resposta_llm(pergunta, perfil=None, contexto_base=None):
    """
    Gera uma resposta contextual:
    - sobre a festa (usa event.json)
    - ou sobre as quintas (usa SQLite ou Qdrant)
    """
    perfil = perfil or {}
    nome = perfil.get("nome", "Utilizador")
    personalidade = perfil.get("personalidade", "neutro")

    # ✅ 1 — Consultas sobre quintas (base SQLite ou Qdrant)
    if e_pergunta_de_quintas(pergunta):
        if e_pergunta_estado(pergunta):
            # Perguntas tipo "porquê", "respondeu", "estado"
            nota = procurar_resposta_semelhante(pergunta, contexto="quintas")
            if nota:
                return nota
            else:
                # Fallback: tenta consultar a base de dados
                sql = "SELECT COUNT(*) as total, SUM(CASE WHEN estado LIKE '%Respondeu%' THEN 1 ELSE 0 END) as respondidas FROM quintas"
                dados = executar_sql(sql)
                if dados and dados[0].get('total'):
                    total = dados[0]['total']
                    resp = dados[0]['respondidas']
                    return (
                        f"Já contactámos {total} quintas e temos {resp} respostas 📞 "
                        f"Temos o Monte da Galega reservado como backup! Pergunta sobre alguma específica 😊"
                    )
                return "Ainda não há quinta fechada, mas já contactámos várias! Temos o Monte da Galega como plano B 😉"
        else:
            # ✅ PERGUNTAS SIMPLES - SQL direto sem LLM
            p = pergunta.lower()
            
            # "quantas quintas?"
            if any(t in p for t in ["quantas", "quantas quintas", "numero", "número", "total"]) and "zona" not in p:
                sql = "SELECT COUNT(*) as total FROM quintas"
                dados = executar_sql(sql)
                if dados and dados[0].get('total'):
                    total = dados[0]['total']
                    return f"Já contactámos {total} quintas no total 📊 Pergunta-me sobre zonas, preços ou características específicas!"
                return "Ainda não temos quintas na base de dados 😅"
            
            # "que quintas?" / "lista de quintas"
            if any(t in p for t in ["que quintas", "quais quintas", "lista", "nomes das quintas"]) and "zona" not in p:
                sql = "SELECT nome, zona, morada FROM quintas LIMIT 10"
                dados = executar_sql(sql)
                if dados:
                    nomes = [f"**{d['nome']}** ({d.get('zona', 'zona n/d')})" for d in dados[:5]]
                    total_sql = "SELECT COUNT(*) as total FROM quintas"
                    total_dados = executar_sql(total_sql)
                    total = total_dados[0]['total'] if total_dados else len(dados)
                    
                    resposta = f"Já contactámos {total} quintas. Aqui estão algumas:\n\n"
                    resposta += "\n".join(f"• {n}" for n in nomes)
                    if total > 5:
                        resposta += f"\n\n...e mais {total - 5} quintas! Pergunta-me sobre zonas ou características específicas 😊"
                    return resposta
                return "Ainda não temos quintas contactadas 😅"
            
            # "quintas no Porto" / "zona Porto"
            if any(t in p for t in ["porto", "no porto", "zona porto", "zona do porto"]):
                sql = "SELECT COUNT(*) as total FROM quintas WHERE zona LIKE '%Porto%'"
                dados = executar_sql(sql)
                if dados and dados[0].get('total', 0) > 0:
                    sql_lista = "SELECT nome, morada FROM quintas WHERE zona LIKE '%Porto%' LIMIT 5"
                    lista = executar_sql(sql_lista)
                    return gerar_resposta_dados_llm(pergunta, lista)
                else:
                    # Ver que zonas existem
                    sql_zonas = "SELECT DISTINCT zona FROM quintas WHERE zona IS NOT NULL AND zona != '' LIMIT 10"
                    zonas = executar_sql(sql_zonas)
                    if zonas:
                        zonas_txt = ", ".join([z['zona'] for z in zonas if z.get('zona')])
                        return f"Não temos quintas na zona do Porto 😅 As zonas que já contactámos são: {zonas_txt}. Queres ver alguma destas?"
                    return "Não temos quintas na zona do Porto 😅"
            
            # "quintas em Lisboa" / "zona Lisboa"
            if any(t in p for t in ["lisboa", "em lisboa", "zona lisboa", "zona de lisboa"]):
                sql = "SELECT nome, zona, morada FROM quintas WHERE zona LIKE '%Lisboa%' LIMIT 10"
                dados = executar_sql(sql)
                if dados:
                    return gerar_resposta_dados_llm(pergunta, dados)
                return "Não encontrei quintas em Lisboa 😅"
            
            # Busca genérica por zona (ex: "em Coruña", "quintas em X")
            if any(t in p for t in ["em ", "zona de ", "zona ", "quais"]):
                # Extrai o nome da zona da pergunta
                import re
                # Remove palavras comuns e fica com o nome da zona
                zona_busca = re.sub(r'\b(em|zona|de|da|do|das|dos|quintas|quais|que|qual)\b', '', p, flags=re.IGNORECASE)
                zona_busca = zona_busca.strip()
                
                if zona_busca and len(zona_busca) > 2:
                    # Normaliza a zona para fazer match
                    zona_normalizada = normalizar_zona(zona_busca)
                    
                    print(f"🔍 Busca por zona: '{zona_busca}' → normalizado: '{zona_normalizada}'")
                    
                    # Tenta encontrar quintas nessa zona (busca flexível)
                    # Usa LOWER e remove acentos no SQL também
                    sql = f"""
                    SELECT nome, zona, morada 
                    FROM quintas 
                    WHERE LOWER(REPLACE(REPLACE(REPLACE(REPLACE(zona, 'ã', 'a'), 'á', 'a'), 'à', 'a'), 'ñ', 'n')) 
                    LIKE '%{zona_normalizada}%' 
                    LIMIT 10
                    """
                    dados = executar_sql(sql)
                    
                    if dados:
                        zona_real = dados[0].get('zona', zona_busca)
                        nomes = "\n".join([f"• **{d['nome']}**" for d in dados])
                        return f"Quintas em **{zona_real}** ({len(dados)} encontrada{'s' if len(dados) > 1 else ''}):\n\n{nomes}\n\nQueres saber mais sobre alguma? 😊"
                    else:
                        return f"Não encontrei quintas em '{zona_busca}' 😅\n\nTenta 'que zonas temos?' para ver as disponíveis!"
            
            # "que zonas" / "zonas disponíveis"
            if any(t in p for t in ["que zonas", "quais zonas", "zonas", "regioes", "regiões"]):
                sql = "SELECT zona, COUNT(*) as total FROM quintas WHERE zona IS NOT NULL AND zona != '' GROUP BY zona ORDER BY total DESC"
                dados = executar_sql(sql)
                if dados:
                    zonas_txt = ", ".join([f"**{d['zona']}** ({d['total']})" for d in dados[:10]])
                    if len(dados) > 10:
                        zonas_txt += f" e mais {len(dados) - 10} zonas"
                    return f"As principais zonas contactadas são:\n{zonas_txt} 📍"
                return "Ainda não temos zonas definidas 😅"
            
            # Perguntas complexas → usar SQLite + LLM
            sql = gerar_sql_da_pergunta(pergunta)
            if sql:
                print(f"📊 SQL gerado: {sql}")
                dados = executar_sql(sql)
                if dados:
                    # ✅ VALIDAÇÃO: só usar LLM se houver dados reais
                    if len(dados) == 0:
                        return "Não encontrei nenhuma quinta que corresponda a isso 😅 Tenta outra pergunta!"
                    
                    # Verifica se tem campos válidos (não vazios ou None)
                    campos_validos = any(
                        v is not None and v != "" and v != 0 
                        for d in dados 
                        for v in d.values()
                    )
                    
                    if not campos_validos:
                        return "Não encontrei informação específica sobre isso 😅 Tenta reformular!"
                    
                    return gerar_resposta_dados_llm(pergunta, dados)
                else:
                    return "Não encontrei nenhuma quinta que corresponda a isso 😅 Tenta outra pergunta!"
            else:
                return "Não consegui interpretar bem a tua pergunta sobre as quintas 😅 Tenta reformular?"

    # ✅ 2 — Caso contrário, responde sobre a festa
    if not contexto_base:
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                contexto_base = json.load(f)
        except Exception:
            contexto_base = {}

    # Verifica se o event.json tem dados válidos
    if not contexto_base or not contexto_base.get("nome_local"):
        # Para conversas casuais/saudações, resposta muito breve
        if any(t in pergunta.lower() for t in ["olá", "ola", "oi", "hey", "bom dia", "boa tarde", "boa noite"]):
            return (
                f"Olá, {nome}! 👋\n\n"
                "Estamos a organizar os detalhes da festa de passagem de ano 🎆\n"
                "Estou disponível para responder a qualquer questão!"
            )
        
        return (
            "Ainda estamos a organizar os detalhes da festa 🎆\n"
            "Já temos o Monte da Galega reservado como backup, mas estamos a ver outras opções!\n"
            "Pergunta-me sobre as quintas que já contactámos 😊"
        )

    coords = contexto_base.get("coordenadas", {})
    latitude = coords.get("latitude", "desconhecida")
    longitude = coords.get("longitude", "desconhecida")

    contexto_texto = (
        f"📍 Local: {contexto_base.get('nome_local', 'ainda a definir')}\n"
        f"🏠 Morada: {contexto_base.get('morada', 'ainda a confirmar')}\n"
        f"🗺️ Coordenadas: {latitude}, {longitude}\n"
        f"🔗 Google Maps: {contexto_base.get('link_google_maps', 'sem link')}\n"
        f"🐾 Aceita animais: {'Sim' if contexto_base.get('aceita_animais') else 'Não'}\n"
        f"🏊 Piscina: {'Sim' if contexto_base.get('tem_piscina') else 'Não'}\n"
        f"🔥 Churrasqueira: {'Sim' if contexto_base.get('tem_churrasqueira') else 'Não'}\n"
        f"🎱 Snooker: {'Sim' if contexto_base.get('tem_snooker') else 'Não'}\n"
        f"🍷 Pode levar vinho: {'Sim' if contexto_base.get('pode_levar_vinho') else 'Não'}\n"
        f"🥘 Pode levar comida: {'Sim' if contexto_base.get('pode_levar_comida') else 'Não'}\n"
        f"💃 Dress code: {contexto_base.get('dress_code', 'não especificado')}\n"
        f"⏰ Hora de início: {contexto_base.get('hora_inicio', 'não definida')}\n"
        f"📶 Wi-Fi: {contexto_base.get('wifi', 'não indicado')}\n"
        f"🌐 Link oficial: {contexto_base.get('link', 'sem link')}"
    )

    # ✅ Prompt para o evento
    prompt = f"""
Tu és o assistente oficial da festa de passagem de ano 🎆.
Responde de forma breve (máximo 2 frases), divertida e natural.

🎯 Contexto real do evento:
{contexto_texto}

NOTA IMPORTANTE: Se o local ainda não estiver definido, menciona que estão a ver opções e que já têm o Monte da Galega como backup.

🧍 Perfil do utilizador:
- Nome: {nome}
- Personalidade: {personalidade}

💬 Pergunta do utilizador:
{pergunta}

🎙️ Instruções:
- Usa sempre os dados reais do JSON quando disponíveis
- Se os dados não estiverem completos, menciona que ainda estão a organizar
- Se perguntarem sobre o local e ainda não houver, diz que têm o Monte da Galega como plano B
- Se perguntarem algo pessoal ou fora do tema, responde com humor leve
- Mantém sempre o Português de Portugal e a segunda pessoa do singular
- Evita respostas longas (máximo 2 frases curtas)
"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "És um assistente sociável e divertido que fala Português de Portugal."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 180,
    }

    try:
        response = requests.post(GROQ_URL, headers=headers, json=data, timeout=20)
        response.raise_for_status()
        result = response.json()
        resposta = result["choices"][0]["message"]["content"].strip()
        return resposta
    except Exception as e:
        print(f"⚠️ Erro no LLM Groq: {e}")
        return "Estou com interferências celestiais... tenta outra vez 😅"