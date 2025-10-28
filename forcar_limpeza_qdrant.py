"""
Força limpeza TOTAL do Qdrant - apaga todos os pontos
"""
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from modules.perfis_manager import client, COLLECTION_PERFIS, importar_perfis_do_json

print("🔥 LIMPEZA FORÇADA - Apaga TODOS os pontos da collection")
print("=" * 50)

try:
    # Lista pontos existentes
    print(f"🔍 A listar pontos em '{COLLECTION_PERFIS}'...")
    pontos, _ = client.scroll(collection_name=COLLECTION_PERFIS, limit=200)
    
    print(f"📦 Encontrados {len(pontos)} pontos")
    
    if len(pontos) > 0:
        print("🗑️ A apagar todos os pontos...")
        
        # Apaga por ID
        ids = [p.id for p in pontos]
        
        # Apaga em batches de 50
        for i in range(0, len(ids), 50):
            batch = ids[i:i+50]
            client.delete(
                collection_name=COLLECTION_PERFIS,
                points_selector=batch
            )
            print(f"   Apagados {len(batch)} pontos...")
        
        print("✅ Todos os pontos apagados!")
    else:
        print("ℹ️ Collection já está vazia")
    
    # Verifica
    pontos_depois, _ = client.scroll(collection_name=COLLECTION_PERFIS, limit=10)
    print(f"📊 Pontos restantes: {len(pontos_depois)}")
    
    if len(pontos_depois) == 0:
        print("\n📦 A importar perfis limpos...")
        importar_perfis_do_json()
        
        # Verifica final
        from modules.perfis_manager import listar_todos_perfis
        total = len(listar_todos_perfis())
        print(f"\n✅ Total final: {total} perfis")
        
        if total == 35:
            print("🎉 SUCESSO! Número correto!")
        else:
            print(f"⚠️ Ainda incorreto. Esperado: 35, Atual: {total}")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()