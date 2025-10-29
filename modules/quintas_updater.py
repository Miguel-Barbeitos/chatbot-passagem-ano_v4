#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
modules/quintas_updater.py
==========================
Funções auxiliares para atualizar quintas no Qdrant
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
import os

def _get_qdrant_client():
    """Cria cliente Qdrant"""
    try:
        # Tenta Streamlit secrets primeiro
        import streamlit as st
        qdrant_url = st.secrets.get("QDRANT_URL")
        qdrant_key = st.secrets.get("QDRANT_API_KEY")
        if qdrant_url and qdrant_key:
            return QdrantClient(url=qdrant_url, api_key=qdrant_key, timeout=10.0)
    except:
        pass
    
    # Fallback: variáveis de ambiente
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_key = os.getenv("QDRANT_API_KEY")
    
    # Se não encontrou, usa valores padrão (para terminal)
    if not qdrant_url:
        qdrant_url = "https://53262e06-1c9b-4530-a703-94f9e573b71a.europe-west3-0.gcp.cloud.qdrant.io:6333"
    if not qdrant_key:
        qdrant_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.8j0MluKJ7Hzk0B2Fey7FBsbQXvr21rvkNlsKCH1COpo"
    
    return QdrantClient(url=qdrant_url, api_key=qdrant_key, timeout=10.0)

def atualizar_quinta_por_email(email_quinta: str, campos: dict):
    """
    Atualiza campos de uma quinta no Qdrant usando o email
    
    Args:
        email_quinta: Email da quinta a atualizar
        campos: Dicionário com campos a atualizar
    
    Returns:
        bool: True se sucesso
    """
    try:
        client = _get_qdrant_client()
        collection_name = "quintas_info"
        
        # Busca TODAS as quintas
        results = client.scroll(
            collection_name=collection_name,
            limit=100
        )
        
        # Procura a quinta pelo email
        quinta_encontrada = None
        point_id = None
        
        for point in results[0]:
            payload_email = point.payload.get('email', '').lower()
            
            # Verifica se o email da quinta contém o domínio do email procurado
            if email_quinta.lower() in payload_email or payload_email in email_quinta.lower():
                quinta_encontrada = point.payload
                point_id = point.id
                break
        
        if not quinta_encontrada:
            print(f"  ⚠️ Quinta com email '{email_quinta}' não encontrada")
            return False
        
        # Atualiza o payload
        payload_atualizado = quinta_encontrada.copy()
        payload_atualizado.update(campos)
        
        # Faz update no Qdrant
        client.set_payload(
            collection_name=collection_name,
            payload=payload_atualizado,
            points=[point_id]
        )
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao atualizar quinta com email '{email_quinta}': {e}")
        import traceback
        traceback.print_exc()
        return False

def atualizar_quinta(nome_quinta: str, campos: dict):
    """
    Atualiza campos de uma quinta no Qdrant
    
    Args:
        nome_quinta: Nome da quinta a atualizar
        campos: Dicionário com campos a atualizar
    
    Returns:
        bool: True se sucesso
    """
    try:
        client = _get_qdrant_client()
        collection_name = "quintas_info"
        
        # Busca TODAS as quintas (sem filtro, porque não há índice)
        results = client.scroll(
            collection_name=collection_name,
            limit=100  # Pega todas
        )
        
        # Procura a quinta pelo nome manualmente
        quinta_encontrada = None
        point_id = None
        
        for point in results[0]:
            if point.payload.get('nome') == nome_quinta:
                quinta_encontrada = point.payload
                point_id = point.id
                break
        
        if not quinta_encontrada:
            return False
        
        # Atualiza o payload (mantém campos existentes)
        payload_atualizado = quinta_encontrada.copy()
        payload_atualizado.update(campos)
        
        # Faz update no Qdrant
        client.set_payload(
            collection_name=collection_name,
            payload=payload_atualizado,
            points=[point_id]
        )
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao atualizar quinta '{nome_quinta}': {e}")
        import traceback
        traceback.print_exc()
        return False

def marcar_quintas_responderam(quintas_dict: dict):
    """
    Marca múltiplas quintas como 'responderam'
    
    Args:
        quintas_dict: Dict com {nome_quinta: {email, data, etc}}
    
    Returns:
        tuple: (sucessos, falhas)
    """
    sucessos = 0
    falhas = []
    
    for nome_quinta, info in quintas_dict.items():
        campos = {
            'respondeu': True,
            'email_resposta': info.get('email', ''),
            'data_resposta': info.get('data_resposta', ''),
            'status': 'respondeu'
        }
        
        if atualizar_quinta(nome_quinta, campos):
            sucessos += 1
        else:
            falhas.append(nome_quinta)
    
    return sucessos, falhas