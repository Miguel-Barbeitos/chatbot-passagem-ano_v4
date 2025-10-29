"""
🎉 Módulo de Organização da Passagem de Ano
Centraliza informações sobre: evento, quintas, confirmações, distâncias
"""

import os
import json
import sqlite3
from datetime import datetime
from pathlib import Path

# Caminhos
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
EVENT_JSON = DATA_DIR / "event.json"
CONFIRMADOS_JSON = DATA_DIR / "confirmados.json"
QUINTAS_DB = DATA_DIR / "quintas.db"

# =====================================================
# 📅 INFORMAÇÕES DO EVENTO
# =====================================================

def get_evento():
    """Carrega informações do evento"""
    try:
        with open(EVENT_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Dados padrão se ficheiro não existir
        return {
            "nome": "Passagem de Ano 2024/2025",
            "data_inicio": "2025-12-30",
            "data_fim": "2026-01-04",
            "check_in": "15:00",
            "check_out": "12:00",
            "cor": "Amarelo",
            "orcamento_pessoa": 300,  # JÁ INCLUI: dormidas + refeições + compras
            "quinta_prereservada": "Monte da Galega",
            "total_convidados": 35,
            "capacidade_minima": 35,
            "capacidade_ideal": 40
        }

def get_datas_evento():
    """Retorna datas formatadas do evento"""
    evento = get_evento()
    
    # Parse datas
    from datetime import datetime
    data_inicio = datetime.strptime(evento['data_inicio'], '%Y-%m-%d')
    data_fim = datetime.strptime(evento['data_fim'], '%Y-%m-%d')
    
    # Calcula duração
    duracao = (data_fim - data_inicio).days
    
    return {
        "inicio": data_inicio.strftime('%d/%m/%Y'),
        "fim": data_fim.strftime('%d/%m/%Y'),
        "check_in": evento['check_in'],
        "check_out": evento['check_out'],
        "duracao_dias": duracao,
        "ano_novo": "31/12/2024"  # Dia específico da passagem de ano
    }

def get_tema_cor():
    """Retorna tema e cor do evento"""
    evento = get_evento()
    return {
        "cor": evento.get('cor', 'Amarelo'),
        "tema": f"Passagem de Ano - Tema {evento.get('cor', 'Amarelo')}"
    }

def get_orcamento():
    """Retorna informação sobre orçamento"""
    evento = get_evento()
    orcamento_pessoa = evento.get('orcamento_pessoa', 300)
    total_convidados = evento.get('total_convidados', 35)
    
    return {
        "por_pessoa": orcamento_pessoa,
        "total_estimado": orcamento_pessoa * total_convidados,
        "inclui": [
            "Alojamento (todas as noites)",
            "Refeições completas",
            "Compras e extras"
        ],
        "observacao": f"€{orcamento_pessoa}/pessoa - tudo incluído"
    }

# =====================================================
# 👥 CONFIRMAÇÕES
# =====================================================

def get_confirmacoes():
    """Carrega confirmações dos convidados"""
    try:
        with open(CONFIRMADOS_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"total_confirmados": 0, "confirmados": []}

def get_stats_confirmacoes():
    """Estatísticas de confirmações"""
    confirmacoes = get_confirmacoes()
    evento = get_evento()
    
    total_confirmados = confirmacoes.get('total_confirmados', 0)
    total_convidados = evento.get('total_convidados', 35)
    
    # Calcula taxa
    taxa = (total_confirmados / total_convidados * 100) if total_convidados > 0 else 0
    
    # Lista de confirmados
    lista_confirmados = confirmacoes.get('confirmados', [])
    
    return {
        "total_confirmados": total_confirmados,
        "total_convidados": total_convidados,
        "taxa_confirmacao": round(taxa, 1),
        "faltam_confirmar": total_convidados - total_confirmados,
        "confirmados": lista_confirmados
    }

def pessoa_confirmou(nome):
    """Verifica se uma pessoa confirmou presença"""
    confirmacoes = get_confirmacoes()
    lista = confirmacoes.get('confirmados', [])
    
    # Normaliza nome para comparação
    nome_norm = nome.lower().strip()
    
    for confirmado in lista:
        if confirmado.lower().strip() == nome_norm:
            return True
    
    return False

# =====================================================
# 🏡 QUINTAS
# =====================================================

def get_quinta_prereservada():
    """Retorna informações da quinta pré-reservada"""
    evento = get_evento()
    nome_quinta = evento.get('quinta_prereservada', 'Monte da Galega')
    
    # Busca info completa da quinta
    quinta = get_info_quinta(nome_quinta)
    
    if quinta:
        return {
            "nome": quinta.get('nome'),
            "zona": quinta.get('zona'),
            "status": "Pré-reservada",
            "website": quinta.get('website'),
            "telefone": quinta.get('telefone'),
            "capacidade": quinta.get('capacidade_confirmada'),
            "custo": quinta.get('custo_total')
        }
    
    return {
        "nome": nome_quinta,
        "status": "Pré-reservada",
        "observacao": "Dados completos não disponíveis na BD"
    }

def get_stats_quintas():
    """Estatísticas das quintas contactadas"""
    try:
        conn = sqlite3.connect(QUINTAS_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Conta por estado
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN resposta = 'Sim' THEN 1 ELSE 0 END) as disponiveis,
                SUM(CASE WHEN resposta = 'Não' THEN 1 ELSE 0 END) as indisponiveis,
                SUM(CASE WHEN resposta IS NULL OR resposta = '' THEN 1 ELSE 0 END) as sem_resposta
            FROM quintas
        """)
        
        stats = cursor.fetchone()
        conn.close()
        
        return {
            "total_contactadas": stats['total'],
            "responderam": stats['disponiveis'] + stats['indisponiveis'],
            "disponiveis": stats['disponiveis'],
            "indisponiveis": stats['indisponiveis'],
            "sem_resposta": stats['sem_resposta']
        }
    
    except Exception as e:
        print(f"❌ Erro ao buscar stats quintas: {e}")
        return {
            "total_contactadas": 0,
            "responderam": 0,
            "disponiveis": 0,
            "indisponiveis": 0,
            "sem_resposta": 0
        }

def get_info_quinta(nome):
    """Busca informação completa de uma quinta por nome"""
    try:
        conn = sqlite3.connect(QUINTAS_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM quintas WHERE nome = ?", (nome,))
        quinta = cursor.fetchone()
        conn.close()
        
        if quinta:
            return dict(quinta)
        return None
    
    except Exception as e:
        print(f"❌ Erro ao buscar quinta: {e}")
        return None

def get_resposta_quinta(nome):
    """Busca resposta específica de uma quinta"""
    quinta = get_info_quinta(nome)
    
    if not quinta:
        return None
    
    return {
        "nome": quinta.get('nome'),
        "resposta": quinta.get('resposta'),
        "estado": quinta.get('estado'),
        "resumo": quinta.get('resumo_resposta'),
        "data_resposta": quinta.get('ultima_resposta'),
        "disponivel": quinta.get('resposta') == 'Sim',
        "preco": quinta.get('custo_total'),
        "capacidade": quinta.get('capacidade_confirmada')
    }

def listar_quintas_disponiveis():
    """Lista quintas que confirmaram disponibilidade"""
    try:
        conn = sqlite3.connect(QUINTAS_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT nome, zona, custo_total, capacidade_confirmada, 
                   website, telefone, resumo_resposta
            FROM quintas 
            WHERE resposta = 'Sim'
            ORDER BY custo_total ASC
        """)
        
        quintas = cursor.fetchall()
        conn.close()
        
        return [dict(q) for q in quintas]
    
    except Exception as e:
        print(f"❌ Erro ao listar quintas disponíveis: {e}")
        return []

def listar_quintas_por_preco(limite=5):
    """Lista quintas mais baratas que responderam"""
    quintas = listar_quintas_disponiveis()
    
    # Ordena por preço
    quintas_ordenadas = sorted(
        quintas, 
        key=lambda q: q.get('custo_total', 999999)
    )
    
    return quintas_ordenadas[:limite]

# =====================================================
# 📍 DISTÂNCIAS
# =====================================================

def calcular_distancia(zona):
    """
    Calcula distância de Lisboa baseado na zona
    NOTA: Usa função existente em llm_groq.py (estimar_distancia_por_zona)
    Mas pode ser melhorada no futuro com coordenadas GPS reais
    """
    
    # Import da função existente
    from llm_groq import estimar_distancia_por_zona
    
    distancia_info = estimar_distancia_por_zona(zona)
    
    if distancia_info:
        return {
            "km": distancia_info.get('km'),
            "tempo": distancia_info.get('tempo'),
            "pais": distancia_info.get('pais'),
            "de": "Lisboa (ponto de partida)"
        }
    
    return {
        "km": None,
        "tempo": "Desconhecido",
        "pais": "Desconhecido",
        "observacao": "Distância não disponível para esta zona"
    }

def get_info_quinta_com_distancia(nome):
    """Busca quinta com cálculo de distância"""
    quinta = get_info_quinta(nome)
    
    if not quinta:
        return None
    
    zona = quinta.get('zona', '')
    distancia = calcular_distancia(zona)
    
    return {
        **quinta,
        "distancia": distancia
    }

# =====================================================
# 🎯 FUNÇÕES DE CONSULTA RÁPIDA
# =====================================================

def get_resumo_organizacao():
    """Resumo completo da organização"""
    evento = get_evento()
    stats_quintas = get_stats_quintas()
    stats_confirmacoes = get_stats_confirmacoes()
    quinta_pre = get_quinta_prereservada()
    
    return {
        "evento": {
            "nome": evento.get('nome'),
            "datas": f"{evento.get('data_inicio')} a {evento.get('data_fim')}",
            "cor_tema": evento.get('cor')
        },
        "quinta_prereservada": quinta_pre,
        "quintas": stats_quintas,
        "confirmacoes": stats_confirmacoes,
        "orcamento_pessoa": evento.get('orcamento_pessoa')
    }

def responder_pergunta_organizacao(pergunta):
    """
    Responde perguntas comuns sobre a organização
    Retorna string formatada ou None se não souber responder
    """
    
    p = pergunta.lower().strip()
    
    # ===== JÁ TEMOS QUINTA? =====
    if any(frase in p for frase in ['já temos', 'temos quinta', 'temos alguma quinta', 'há quinta']):
        quinta_pre = get_quinta_prereservada()
        stats = get_stats_quintas()
        
        resposta = f"""✅ Sim! Temos o **{quinta_pre['nome']}** pré-reservado.

📊 Estado da procura:
• {stats['total_contactadas']} quintas contactadas
• {stats['responderam']} responderam
• {stats['disponiveis']} disponíveis
• {stats['indisponiveis']} indisponíveis
• {stats['sem_resposta']} sem resposta ainda"""
        
        return resposta
    
    # ===== QUANTAS QUINTAS RESPONDERAM? =====
    if 'quantas' in p and ('responderam' in p or 'resposta' in p):
        stats = get_stats_quintas()
        
        resposta = f"""📊 **{stats['responderam']}** quintas responderam de {stats['total_contactadas']} contactadas:

✅ {stats['disponiveis']} disponíveis
❌ {stats['indisponiveis']} indisponíveis
⏳ {stats['sem_resposta']} sem resposta"""
        
        return resposta
    
    # ===== QUANTOS CONFIRMARAM? =====
    if 'quantos' in p and ('confirmaram' in p or 'confirmados' in p):
        stats = get_stats_confirmacoes()
        
        resposta = f"""👥 **{stats['total_confirmados']}** pessoas confirmadas de {stats['total_convidados']} convidados

📊 Taxa de confirmação: {stats['taxa_confirmacao']}%
⏳ Faltam confirmar: {stats['faltam_confirmar']} pessoas"""
        
        if stats['confirmados']:
            resposta += f"\n\n✅ Confirmados:\n"
            for nome in stats['confirmados'][:10]:  # Máximo 10
                resposta += f"• {nome}\n"
            
            if len(stats['confirmados']) > 10:
                resposta += f"• ... e mais {len(stats['confirmados']) - 10}"
        
        return resposta
    
    # ===== QUAIS SÃO OS DIAS? =====
    if 'quais' in p and ('dias' in p or 'datas' in p) or 'quando' in p:
        datas = get_datas_evento()
        
        resposta = f"""📅 **Passagem de Ano 2024/2025**

📆 Datas: {datas['inicio']} a {datas['fim']}
🏠 Check-in: {datas['check_in']}
🚪 Check-out: {datas['check_out']}
⏱️ Duração: {datas['duracao_dias']} dias

🎆 Passagem de Ano: 31/12/2024 à meia-noite!"""
        
        return resposta
    
    # ===== QUAL A COR? =====
    if 'cor' in p or 'tema' in p:
        tema = get_tema_cor()
        
        resposta = f"""🎨 **Cor/Tema deste ano: {tema['cor']}**

{tema['tema']}"""
        
        return resposta
    
    # ===== QUANTO CUSTA? =====
    if any(palavra in p for palavra in ['quanto', 'preço', 'preco', 'custo', 'valor']):
        if 'pessoa' in p or 'por pessoa' in p:
            orcamento = get_orcamento()
            
            resposta = f"""💰 **€{orcamento['por_pessoa']} por pessoa**

✅ Já inclui TUDO:
"""
            for item in orcamento['inclui']:
                resposta += f"• {item}\n"
            
            resposta += f"\n📊 Total estimado ({get_evento()['total_convidados']} pessoas): €{orcamento['total_estimado']}"
            
            return resposta
    
    # Não sabe responder
    return None

# =====================================================
# 🧪 TESTE
# =====================================================

if __name__ == "__main__":
    print("🧪 TESTE DO MÓDULO ORGANIZAÇÃO\n")
    
    # Testa resumo
    print("📊 RESUMO DA ORGANIZAÇÃO:")
    print("=" * 60)
    resumo = get_resumo_organizacao()
    print(json.dumps(resumo, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 60)
    
    # Testa perguntas
    perguntas_teste = [
        "Já temos quinta?",
        "Quantas quintas responderam?",
        "Quantos já confirmaram?",
        "Quais são os dias?",
        "Qual a cor deste ano?",
        "Quanto custa por pessoa?"
    ]
    
    print("\n🧪 TESTE DE PERGUNTAS:")
    print("=" * 60)
    
    for pergunta in perguntas_teste:
        print(f"\n❓ {pergunta}")
        print("-" * 60)
        resposta = responder_pergunta_organizacao(pergunta)
        if resposta:
            print(resposta)
        else:
            print("⚠️ Não soube responder")
        print()