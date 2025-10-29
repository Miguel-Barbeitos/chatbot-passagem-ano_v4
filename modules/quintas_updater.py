#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
modules/quintas_updater.py
==========================
Funções auxiliares para atualizar quintas no Qdrant
CRIA CLIENTE PRÓPRIO DE FORMA SEGURA (sem hardcoded keys)
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
import os

def _get_qdrant_client():
    """
    Cria cliente Qdrant (privado)
    Usa a mesma lógica que quintas_qdrant.py
    """
    try:
        # Tenta Streamlit primeiro
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
    
    if not qdrant_url or not qdrant_key:
        raise Exception(
            "❌ Credenciais Qdrant não encontradas!\n"
            "   Configure QDRANT_URL e QDRANT_API_KEY em:\n"
            "   - .streamlit/secrets.toml (Streamlit), ou\n"
            "   - Variáveis de ambiente (terminal)"
        )
    
    return QdrantClient(url=qdrant_url, api_key=qdrant_key, timeout=10.0)

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
        collection_name = "quintas"
        
        # Busca a quinta pelo nome
        results = client.scroll(
            collection_name=collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="nome",
                        match=MatchValue(value=nome_quinta)
                    )
                ]
            ),
            limit=1
        )
        
        if not results[0]:
            return False
        
        point = results[0][0]
        point_id = point.id
        
        # Atualiza o payload (mantém campos existentes)
        payload_atual = point.payload
        payload_atual.update(campos)
        
        # Faz update no Qdrant
        client.set_payload(
            collection_name=collection_name,
            payload=payload_atual,
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