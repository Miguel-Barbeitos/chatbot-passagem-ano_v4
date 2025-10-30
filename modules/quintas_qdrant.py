#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
modules/quintas_qdrant.py
=========================
Módulo para usar as quintas diretamente do Qdrant Cloud
Collection: quintas_info (35 pontos)
"""

import os
from typing import List, Dict, Optional
from qdrant_client import QdrantClient, models

# Configuração
COLLECTION_NAME = "quintas_info"

class QuintasQdrant:
    """Gestor de quintas usando Qdrant Cloud"""
    
    def __init__(self):
        self.client = self._get_client()
        self._cache = None
    
    def _get_client(self) -> QdrantClient:
        """Conecta ao Qdrant Cloud"""
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_key = os.getenv("QDRANT_API_KEY")
        
        if not qdrant_url or not qdrant_key:
            # Tenta Streamlit secrets
            try:
                import streamlit as st
                qdrant_url = st.secrets.get("QDRANT_URL")
                qdrant_key = st.secrets.get("QDRANT_API_KEY")
            except:
                pass
        
        if qdrant_url and qdrant_key:
            return QdrantClient(url=qdrant_url, api_key=qdrant_key)
        else:
            raise ValueError("❌ Credenciais do Qdrant não configuradas!")
    
    def _get_all_quintas(self) -> List[Dict]:
        """Busca todas as quintas do Qdrant (com cache)"""
        if self._cache is not None:
            return self._cache
        
        quintas = []
        offset = None
        
        try:
            while True:
                resultados, offset = self.client.scroll(
                    collection_name=COLLECTION_NAME,
                    limit=100,
                    offset=offset
                )
                
                if not resultados:
                    break
                
                for ponto in resultados:
                    quinta = ponto.payload
                    # Adiciona ID do ponto
                    quinta['_id'] = ponto.id
                    quintas.append(quinta)
                
                if offset is None:
                    break
            
            self._cache = quintas
            print(f"✅ {len(quintas)} quintas carregadas do Qdrant")
            return quintas
            
        except Exception as e:
            print(f"❌ Erro ao buscar quintas: {e}")
            return []
    
    def contar(self) -> int:
        """Conta total de quintas"""
        quintas = self._get_all_quintas()
        return len(quintas)
    
    def listar_todas(self, limite: int = None) -> List[Dict]:
        """Lista todas as quintas (ou até o limite)"""
        quintas = self._get_all_quintas()
        if limite:
            return quintas[:limite]
        return quintas
    
    def buscar_por_nome(self, nome: str) -> Optional[Dict]:
        """Busca quinta por nome (aproximado)"""
        nome_lower = nome.lower().strip()
        quintas = self._get_all_quintas()
        
        # Busca exata
        for q in quintas:
            if q.get('nome', '').lower() == nome_lower:
                return q
        
        # Busca aproximada (contém)
        for q in quintas:
            if nome_lower in q.get('nome', '').lower():
                return q
        
        # Busca por partes do nome
        palavras_busca = nome_lower.split()
        if len(palavras_busca) > 1:
            for q in quintas:
                nome_quinta = q.get('nome', '').lower()
                if all(palavra in nome_quinta for palavra in palavras_busca):
                    return q
        
        return None
    
    def buscar_por_zona(self, zona: str) -> List[Dict]:
        """Busca quintas por zona"""
        zona_lower = zona.lower().strip()
        quintas = self._get_all_quintas()
        
        resultados = []
        for q in quintas:
            zona_quinta = q.get('zona', '').lower()
            if zona_lower in zona_quinta or zona_quinta in zona_lower:
                resultados.append(q)
        
        return resultados
    
    def contar_com_resposta(self) -> int:
        """Conta quintas que já responderam"""
        quintas = self._get_all_quintas()
        return len([q for q in quintas if q.get('resposta')])
    
    def contar_sem_resposta(self) -> int:
        """Conta quintas sem resposta"""
        quintas = self._get_all_quintas()
        return len([q for q in quintas if not q.get('resposta')])
    
    def listar_com_resposta(self) -> List[Dict]:
        """Lista quintas que responderam"""
        quintas = self._get_all_quintas()
        return [q for q in quintas if q.get('resposta')]
    
    def buscar_por_caracteristica(self, caracteristica: str) -> List[Dict]:
        """
        Busca quintas por característica (piscina, churrasqueira, etc.)
        """
        caracteristica_lower = caracteristica.lower()
        quintas = self._get_all_quintas()
        
        resultados = []
        for q in quintas:
            # Busca em vários campos
            campos_texto = [
                q.get('comodidades', ''),
                q.get('observacoes', ''),
                q.get('resposta', ''),
                q.get('resumo_resposta', '')
            ]
            
            texto_completo = ' '.join([str(c).lower() for c in campos_texto])
            
            if caracteristica_lower in texto_completo:
                resultados.append(q)
        
        return resultados
    
    def executar_query_simulada(self, query: str) -> List[Dict]:
        """
        Simula queries SQL comuns usando Qdrant
        """
        query_lower = query.lower()
        quintas = self._get_all_quintas()
        
        # COUNT(*) total
        if 'count(*)' in query_lower and 'where' not in query_lower:
            return [{"total": len(quintas)}]
        
        # COUNT(*) com resposta
        if 'count(*)' in query_lower and 'resposta is not null' in query_lower:
            com_resposta = len([q for q in quintas if q.get('resposta')])
            return [{"total": com_resposta}]
        
        # COUNT(*) sem resposta
        if 'count(*)' in query_lower and 'resposta is null' in query_lower:
            sem_resposta = len([q for q in quintas if not q.get('resposta')])
            return [{"total": sem_resposta}]
        
        # SELECT com LIMIT
        if 'select' in query_lower and 'limit' in query_lower:
            import re
            match = re.search(r'limit\s+(\d+)', query_lower)
            if match:
                limite = int(match.group(1))
                return quintas[:limite]
        
        # SELECT por zona
        if 'where' in query_lower and 'zona' in query_lower:
            import re
            match = re.search(r"zona\s+like\s+'%([^']+)%'", query_lower, re.IGNORECASE)
            if match:
                zona_busca = match.group(1)
                return self.buscar_por_zona(zona_busca)
        
        # SELECT por nome
        if 'where' in query_lower and 'nome' in query_lower:
            import re
            match = re.search(r"nome\s+like\s+'%([^']+)%'", query_lower, re.IGNORECASE)
            if match:
                nome_busca = match.group(1)
                quinta = self.buscar_por_nome(nome_busca)
                return [quinta] if quinta else []
        
        # Default: retorna tudo ou limite
        if 'limit' in query_lower:
            import re
            match = re.search(r'limit\s+(\d+)', query_lower)
            if match:
                return quintas[:int(match.group(1))]
        
        return quintas
    
    def get_estatisticas(self) -> Dict:
        """Retorna estatísticas das quintas"""
        quintas = self._get_all_quintas()
        
        total = len(quintas)
        com_resposta = len([q for q in quintas if q.get('resposta')])
        sem_resposta = total - com_resposta
        
        # Agrupa por zona
        zonas = {}
        for q in quintas:
            zona = q.get('zona', 'Desconhecida')
            zonas[zona] = zonas.get(zona, 0) + 1
        
        # Agrupa por estado
        estados = {}
        for q in quintas:
            estado = q.get('estado', 'Desconhecido')
            estados[estado] = estados.get(estado, 0) + 1
        
        return {
            'total': total,
            'com_resposta': com_resposta,
            'sem_resposta': sem_resposta,
            'zonas': zonas,
            'estados': estados,
            'fonte': 'Qdrant (quintas_info)'
        }

# Instância global
_manager = None

def get_manager() -> QuintasQdrant:
    """Retorna instância singleton"""
    global _manager
    if _manager is None:
        _manager = QuintasQdrant()
    return _manager

# Funções de conveniência (compatíveis com o código existente)
def executar_query(query: str) -> List[Dict]:
    """Executa query simulada no Qdrant"""
    return get_manager().executar_query_simulada(query)

def listar_quintas(limite: int = None) -> List[Dict]:
    """Lista quintas"""
    return get_manager().listar_todas(limite)

def buscar_quinta(nome: str) -> Optional[Dict]:
    """Busca quinta por nome"""
    return get_manager().buscar_por_nome(nome)

def contar_quintas() -> int:
    """Conta quintas"""
    return get_manager().contar()

def get_estatisticas() -> Dict:
    """Estatísticas"""
    return get_manager().get_estatisticas()

# Para compatibilidade com SQLite
def executar_sql(query: str) -> List[Dict]:
    """Alias para executar_query (compatibilidade)"""
    return executar_query(query)

# Script de teste
if __name__ == "__main__":
    print("🧪 TESTANDO QUINTAS QDRANT")
    print("="*60)
    
    try:
        manager = get_manager()
        
        print(f"\n✅ Conectado ao Qdrant!")
        
        stats = get_estatisticas()
        print(f"\n📊 Estatísticas:")
        print(f"   Total: {stats['total']}")
        print(f"   Com resposta: {stats['com_resposta']}")
        print(f"   Sem resposta: {stats['sem_resposta']}")
        
        print(f"\n🏘️  Zonas:")
        for zona, count in sorted(stats['zonas'].items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"   • {zona}: {count}")
        
        print(f"\n🏡 Primeiras 3 quintas:")
        quintas = listar_quintas(3)
        for q in quintas:
            print(f"   • {q.get('nome', 'N/A')} ({q.get('zona', 'N/A')})")
        
        # Teste de busca
        print(f"\n🔍 Teste de busca:")
        teste_nome = "Monte"
        resultado = buscar_quinta(teste_nome)
        if resultado:
            print(f"   Busca '{teste_nome}': {resultado.get('nome')}")
        
        # Teste de query SQL
        print(f"\n📝 Teste de query SQL:")
        resultado = executar_sql("SELECT COUNT(*) as total FROM quintas")
        print(f"   COUNT(*): {resultado}")
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)

def buscar_quinta_por_nome(nome: str):
    """Busca quinta específica por nome (case-insensitive, flexível)"""
    try:
        quintas = listar_quintas()
        nome_lower = nome.lower().strip()
        
        # 1. Busca exata
        for q in quintas:
            if q.get('nome', '').lower() == nome_lower:
                return q
        
        # 2. Busca parcial (nome contém busca)
        for q in quintas:
            nome_quinta = q.get('nome', '').lower()
            if nome_lower in nome_quinta:
                return q
        
        # 3. Busca reversa (busca contém nome da quinta)
        # Ex: "Casas de Romaria Brovales" contém "Casas de Romaria"
        for q in quintas:
            nome_quinta = q.get('nome', '').lower()
            if nome_quinta in nome_lower:
                return q
        
        # 4. Busca por palavras-chave principais
        # Remove palavras comuns e busca pelas principais
        palavras_comuns = ['quinta', 'casa', 'casas', 'monte', 'herdade', 'centro', 'rural', 'turismo', 'de', 'da', 'do', 'das', 'dos']
        palavras_busca = [p for p in nome_lower.split() if p not in palavras_comuns and len(p) > 3]
        
        if palavras_busca:
            for q in quintas:
                nome_quinta = q.get('nome', '').lower()
                # Se todas as palavras-chave estão no nome
                if all(palavra in nome_quinta for palavra in palavras_busca):
                    return q
        
        # 5. Fuzzy matching (similaridade >=60%)
        from difflib import get_close_matches
        nomes_quintas = [q.get('nome', '') for q in quintas]
        matches = get_close_matches(nome, nomes_quintas, n=1, cutoff=0.6)
        
        if matches:
            nome_aproximado = matches[0]
            print(f"🔍 Fuzzy match encontrado: '{nome}' → '{nome_aproximado}'")
            for q in quintas:
                if q.get('nome', '') == nome_aproximado:
                    return q
        
        return None
    except Exception as e:
        print(f"❌ Erro ao buscar quinta: {e}")
        return None