"""
Limpa collection de perfis e reimporta
"""
import sys
import os
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from modules.perfis_manager import client, COLLECTION_PERFIS, importar_perfis_do_json
from qdrant_client import models

print("🧹 A limpar collection de perfis de forma completa...")

try:
    # Lista collections existentes
    collections = client.get_collections()
    collection_names = [c.name for c in collections.collections]
    
    print(f"📦 Collections existentes: {collection_names}")
    
    # Se existe, apaga
    if COLLECTION_PERFIS in collection_names:
        print(f"🗑️ A apagar '{COLLECTION_PERFIS}'...")
        client.delete_collection(COLLECTION_PERFIS)
        print("✅ Collection apagada!")
        
        # Aguarda um pouco
        time.sleep(2)
    else:
        print(f"ℹ️ Collection '{COLLECTION_PERFIS}' não existe")
    
    # Verifica se foi mesmo apagada
    collections_after = client.get_collections()
    collection_names_after = [c.name for c in collections_after.collections]
    
    if COLLECTION_PERFIS in collection_names_after:
        print("⚠️ Collection ainda existe! A forçar...")
        client.delete_collection(COLLECTION_PERFIS)
        time.sleep(3)
    
    print("\n📦 A reimportar perfis...")
    success = importar_perfis_do_json()
    
    if success:
        print("\n✅ Processo completo!")
        
        # Verifica resultado final
        from modules.perfis_manager import listar_todos_perfis
        perfis = listar_todos_perfis()
        total = len(perfis)
        
        print(f"📊 Total de perfis agora: {total}")
        
        if total == 35:
            print("✅ Número correto! Tudo OK!")
        else:
            print(f"⚠️ Esperado: 35, Encontrado: {total}")
            
            # Lista nomes para ver duplicados
            nomes = [p["nome"] for p in perfis]
            duplicados = set([n for n in nomes if nomes.count(n) > 1])
            if duplicados:
                print(f"⚠️ Nomes duplicados: {duplicados}")
    else:
        print("❌ Falha na importação")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
"""
Limpa collection de perfis e reimporta
"""
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from modules.perfis_manager import client, COLLECTION_PERFIS, importar_perfis_do_json

print("🧹 A limpar collection de perfis...")

try:
    # Apaga a collection
    client.delete_collection(COLLECTION_PERFIS)
    print("✅ Collection apagada!")
    
    # Reimporta
    print("\n📦 A reimportar perfis...")
    importar_perfis_do_json()
    
    print("\n✅ Processo completo!")
    
    # Verifica
    from modules.perfis_manager import listar_todos_perfis
    total = len(listar_todos_perfis())
    print(f"📊 Total de perfis agora: {total}")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()