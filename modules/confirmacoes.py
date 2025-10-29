# -*- coding: utf-8 -*-
"""
Sistema de Confirmacoes usando JSON
"""
import os
import sys
import json
import unicodedata
from datetime import datetime

# Adiciona o diretorio raiz ao path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Import direto do modulo
import modules.perfis_manager as pm

CONFIRMACOES_PATH = os.path.join(BASE_DIR, "config", "confirmacoes.json")

def ler_confirmacoes():
    """Le confirmacoes do JSON"""
    try:
        os.makedirs(os.path.dirname(CONFIRMACOES_PATH), exist_ok=True)
        
        if not os.path.exists(CONFIRMACOES_PATH):
            dados_iniciais = {
                "confirmados": [],
                "total": 0,
                "ultima_atualizacao": None,
                "por_familia": {}
            }
            with open(CONFIRMACOES_PATH, "w", encoding="utf-8") as f:
                json.dump(dados_iniciais, f, ensure_ascii=False, indent=2)
            return dados_iniciais
        
        with open(CONFIRMACOES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Erro ao ler confirmacoes: {e}")
        return {"confirmados": [], "total": 0, "por_familia": {}}

def guardar_confirmacoes(dados):
    """Guarda confirmacoes no JSON"""
    try:
        dados["ultima_atualizacao"] = datetime.now().isoformat()
        with open(CONFIRMACOES_PATH, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Erro ao guardar confirmacoes: {e}")
        return False


def normalizar_nome(nome):
    """Normaliza nome para comparação (remove acentos, minúsculas)"""
    if not isinstance(nome, str):
        return ""
    nome = unicodedata.normalize('NFKD', nome)
    nome = ''.join(c for c in nome if not unicodedata.combining(c))
    return nome.lower().strip()

def confirmar_pessoa(nome, confirmado_por=None):
    """Confirma uma pessoa"""
    try:
        # Busca o perfil diretamente
        perfil = pm.buscar_perfil(nome)
        
        # Se não encontrou, tenta busca normalizada
        if not perfil:
            print(f"⚠️ Perfil '{nome}' não encontrado, tentando busca normalizada...")
            nome_normalizado = normalizar_nome(nome)
            
            todos_perfis = pm.listar_todos_perfis()
            for p in todos_perfis:
                if normalizar_nome(p.get("nome", "")) == nome_normalizado:
                    perfil = p
                    print(f"✅ Encontrado: {p.get('nome')}")
                    break
        
        if not perfil:
            return {
                "sucesso": False,
                "mensagem": f"'{nome}' nao esta na lista de convidados",
                "familia_sugerida": []
            }
        
        # Le confirmacoes atuais
        dados = ler_confirmacoes()
        
        # Usa o nome do perfil encontrado (não o nome da query)
        nome_real = perfil["nome"]
        
        # Ja confirmado?
        if nome_real in dados["confirmados"]:
            return {
                "sucesso": True,
                "mensagem": f"{nome_real} ja esta confirmado!",
                "familia_sugerida": []
            }
        
        # Adiciona confirmacao
        dados["confirmados"].append(nome_real)
        dados["total"] = len(dados["confirmados"])
        
        # Organiza por familia
        familia_id = perfil["familia_id"]
        if familia_id not in dados["por_familia"]:
            dados["por_familia"][familia_id] = []
        if nome_real not in dados["por_familia"][familia_id]:
            dados["por_familia"][familia_id].append(nome_real)
        
        # Guarda
        guardar_confirmacoes(dados)
        
        # Atualiza perfil no Qdrant
        pm.atualizar_perfil(nome_real, {
            "confirmado": True,
            "confirmado_por": confirmado_por or nome_real,
            "data_confirmacao": datetime.now().isoformat()
        })
        
        # Sugere familia
        familia = pm.listar_familia(familia_id)
        familia_nao_confirmada = [
            p["nome"] for p in familia 
            if p["nome"] != nome_real and p["nome"] not in dados["confirmados"]
        ]
        
        return {
            "sucesso": True,
            "mensagem": f"Boa! {nome_real} confirmado",
            "familia_sugerida": familia_nao_confirmada
        }
        
    except Exception as e:
        print(f"Erro ao confirmar: {e}")
        import traceback
        traceback.print_exc()
        return {
            "sucesso": False,
            "mensagem": "Erro ao confirmar",
            "familia_sugerida": []
        }

def confirmar_familia_completa(familia_id, confirmado_por):
    """Confirma toda a familia de uma vez"""
    try:
        familia = pm.listar_familia(familia_id)
        if not familia:
            return {
                "sucesso": False,
                "mensagem": "Familia nao encontrada",
                "confirmados": []
            }
        
        confirmados = []
        for membro in familia:
            resultado = confirmar_pessoa(membro["nome"], confirmado_por)
            if resultado["sucesso"]:
                confirmados.append(membro["nome"])
        
        return {
            "sucesso": True,
            "mensagem": f"Familia confirmada: {', '.join(confirmados)}",
            "confirmados": confirmados
        }
    except Exception as e:
        print(f"Erro: {e}")
        return {
            "sucesso": False,
            "mensagem": "Erro ao confirmar familia",
            "confirmados": []
        }

def remover_confirmacao(nome):
    """Remove confirmacao"""
    try:
        dados = ler_confirmacoes()
        
        if nome not in dados["confirmados"]:
            return {"sucesso": False, "mensagem": f"{nome} nao estava confirmado"}
        
        dados["confirmados"].remove(nome)
        dados["total"] = len(dados["confirmados"])
        
        # Remove das familias
        for familia in dados["por_familia"].values():
            if nome in familia:
                familia.remove(nome)
        
        guardar_confirmacoes(dados)
        
        # Atualiza Qdrant
        pm.atualizar_perfil(nome, {
            "confirmado": False,
            "confirmado_por": None,
            "data_confirmacao": None
        })
        
        return {"sucesso": True, "mensagem": f"{nome} removido da lista"}
    except Exception as e:
        print(f"Erro: {e}")
        return {"sucesso": False, "mensagem": "Erro ao remover"}

def get_confirmados():
    """Retorna lista de confirmados"""
    dados = ler_confirmacoes()
    return sorted(dados["confirmados"])

def get_estatisticas():
    """Retorna estatisticas das confirmacoes"""
    dados = ler_confirmacoes()
    
    familias_completas = []
    familias_parciais = []
    
    for familia_id, membros in dados["por_familia"].items():
        familia_total = pm.listar_familia(familia_id)
        if len(membros) == len(familia_total):
            familias_completas.append(familia_id)
        elif len(membros) > 0:
            familias_parciais.append(familia_id)
    
    return {
        "total_confirmados": dados["total"],
        "familias_completas": len(familias_completas),
        "familias_parciais": len(familias_parciais),
        "ultima_atualizacao": dados.get("ultima_atualizacao")
    }

def pode_confirmar_por(confirmador, confirmado):
    """Verifica se alguem pode confirmar outra pessoa"""
    perfil_confirmador = pm.buscar_perfil(confirmador)
    if not perfil_confirmador:
        return False
    
    # Pode confirmar a si proprio
    if confirmador == confirmado:
        return True
    
    # Pode confirmar quem esta na sua lista
    return confirmado in perfil_confirmador.get("pode_confirmar_por", [])

def detectar_intencao_confirmacao(texto):
    """Deteta qual a intencao de confirmacao"""
    texto_lower = texto.lower()
    
    # Familia completa
    if any(p in texto_lower for p in ["nos", "familia", "todos", "toda a familia"]):
        return {"tipo": "familia", "explicito": True, "nomes_mencionados": []}
    
    # So filhos
    if any(p in texto_lower for p in ["miudos", "filhos", "criancas"]):
        return {"tipo": "filhos", "explicito": True, "nomes_mencionados": []}
    
    # Individual explicito
    if any(p in texto_lower for p in ["so eu", "apenas eu", "eu sozinho"]):
        return {"tipo": "individual", "explicito": True, "nomes_mencionados": []}
    
    # Deteta nomes proprios mencionados
    import re
    possiveis_nomes = re.findall(r'\b[A-Z][a-z]+\b', texto)
    
    if possiveis_nomes:
        return {"tipo": "especificos", "explicito": True, "nomes_mencionados": possiveis_nomes}
    
    # Padrao: "eu vou", "confirmo"
    if any(p in texto_lower for p in ["eu vou", "confirmo", "vou"]):
        return {"tipo": "individual", "explicito": False, "nomes_mencionados": []}
    
    return {"tipo": "desconhecido", "explicito": False, "nomes_mencionados": []}

if __name__ == "__main__":
    print("Testando sistema de confirmacoes...")
    
    print("\nConfirmando Barbeitos...")
    resultado = confirmar_pessoa("Barbeitos")
    print(f"   {resultado['mensagem']}")
    
    print("\nConfirmando Jorge (familia completa?)...")
    resultado = confirmar_pessoa("Jorge")
    print(f"   {resultado['mensagem']}")
    if resultado["familia_sugerida"]:
        print(f"   Sugestao: {', '.join(resultado['familia_sugerida'])}")
    
    print("\nEstatisticas:")
    stats = get_estatisticas()
    print(f"   Total confirmados: {stats['total_confirmados']}")
    print(f"   Familias completas: {stats['familias_completas']}")
    
    print("\nLista de confirmados:")
    for nome in get_confirmados():
        perfil = pm.buscar_perfil(nome)
        if perfil:
            print(f"   - {nome} ({perfil.get('familia_id', 'N/A')})")
        else:
            print(f"   - {nome}")