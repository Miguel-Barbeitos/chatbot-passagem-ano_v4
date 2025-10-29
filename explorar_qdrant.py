"""
Explorador Completo do Qdrant
Mostra TODAS as coleções e TODOS os itens em detalhe
"""

import os
import sys
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

try:
    from qdrant_client import QdrantClient
except ImportError:
    print("❌ Instala: pip install qdrant-client")
    sys.exit(1)

# =====================================================
# 🔌 CONEXÃO
# =====================================================

def conectar_qdrant():
    """Conecta ao Qdrant"""
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_key = os.getenv("QDRANT_API_KEY")
    
    if qdrant_url and qdrant_key:
        print("☁️  Conectando ao Qdrant Cloud...")
        return QdrantClient(url=qdrant_url, api_key=qdrant_key)
    
    qdrant_path = os.path.join(BASE_DIR, "qdrant_data")
    
    try:
        print(f"💾 Conectando ao Qdrant local: {qdrant_path}")
        return QdrantClient(path=qdrant_path)
    except RuntimeError as e:
        if "already accessed" in str(e):
            # Tenta usar módulo existente
            try:
                from modules.perfis_manager import client
                print("🔄 Reutilizando conexão existente (Streamlit a correr)")
                return client
            except:
                pass
        raise

# =====================================================
# 📊 LISTAR COLEÇÕES
# =====================================================

def listar_colecoes(client):
    """Lista todas as coleções"""
    collections = client.get_collections()
    
    if not collections.collections:
        print("❌ Nenhuma coleção encontrada!")
        return []
    
    colecoes_info = []
    
    for col in collections.collections:
        info = client.get_collection(col.name)
        
        colecoes_info.append({
            'nome': col.name,
            'pontos': info.points_count,
            'vector_size': info.config.params.vectors.size if hasattr(info.config.params, 'vectors') else 'N/A',
            'distance': info.config.params.vectors.distance.name if hasattr(info.config.params, 'vectors') else 'N/A'
        })
    
    return colecoes_info

# =====================================================
# 🔍 EXPLORAR COLEÇÃO
# =====================================================

def explorar_colecao(client, nome_colecao, limite=None, mostrar_vetores=False):
    """Explora uma coleção em detalhe"""
    
    print(f"\n{'=' * 80}")
    print(f"🔍 COLEÇÃO: {nome_colecao}")
    print(f"{'=' * 80}\n")
    
    # Info geral
    info = client.get_collection(nome_colecao)
    print(f"📊 Total de pontos: {info.points_count}")
    print(f"📏 Tamanho do vetor: {info.config.params.vectors.size if hasattr(info.config.params, 'vectors') else 'N/A'}")
    print(f"📐 Distância: {info.config.params.vectors.distance.name if hasattr(info.config.params, 'vectors') else 'N/A'}")
    print()
    
    if info.points_count == 0:
        print("⚠️  Coleção vazia!")
        return
    
    # Scroll todos os pontos
    offset = None
    todos_pontos = []
    batch_size = 100
    
    while True:
        resultado = client.scroll(
            collection_name=nome_colecao,
            limit=batch_size,
            offset=offset,
            with_vectors=mostrar_vetores
        )
        
        pontos, offset = resultado
        
        if not pontos:
            break
        
        todos_pontos.extend(pontos)
        
        if offset is None:
            break
        
        if limite and len(todos_pontos) >= limite:
            todos_pontos = todos_pontos[:limite]
            break
    
    print(f"📥 Carregados {len(todos_pontos)} pontos")
    print()
    
    # Analisa estrutura dos payloads
    if todos_pontos:
        print("=" * 80)
        print("📋 ESTRUTURA DOS DADOS")
        print("=" * 80)
        
        # Pega chaves do primeiro ponto
        primeiro_payload = todos_pontos[0].payload
        chaves = list(primeiro_payload.keys())
        
        print(f"\n🔑 Campos disponíveis ({len(chaves)}):")
        for chave in sorted(chaves):
            tipo = type(primeiro_payload[chave]).__name__
            print(f"  • {chave} ({tipo})")
        print()
    
    # Mostra cada ponto
    print("=" * 80)
    print("📄 DADOS COMPLETOS")
    print("=" * 80)
    
    for i, ponto in enumerate(todos_pontos, 1):
        print(f"\n{'─' * 80}")
        print(f"📍 PONTO #{i} (ID: {ponto.id})")
        print(f"{'─' * 80}")
        
        # Payload
        print("\n📦 PAYLOAD:")
        for chave, valor in sorted(ponto.payload.items()):
            # Formata valor
            if isinstance(valor, dict):
                print(f"\n  {chave}:")
                for sub_chave, sub_valor in valor.items():
                    print(f"    • {sub_chave}: {sub_valor}")
            elif isinstance(valor, list):
                if len(valor) > 0 and isinstance(valor[0], str):
                    print(f"  {chave}: {', '.join(valor[:3])}{'...' if len(valor) > 3 else ''}")
                else:
                    print(f"  {chave}: [{len(valor)} itens]")
            elif isinstance(valor, str) and len(valor) > 100:
                print(f"  {chave}: {valor[:100]}...")
            else:
                print(f"  {chave}: {valor}")
        
        # Vetor (se pedido)
        if mostrar_vetores and hasattr(ponto, 'vector'):
            if isinstance(ponto.vector, list):
                print(f"\n🔢 VETOR ({len(ponto.vector)} dimensões):")
                print(f"  Primeiros 5: {ponto.vector[:5]}")
                print(f"  Últimos 5: {ponto.vector[-5:]}")
        
        print()
    
    return todos_pontos

# =====================================================
# 📊 ESTATÍSTICAS
# =====================================================

def gerar_estatisticas(client, nome_colecao):
    """Gera estatísticas sobre uma coleção"""
    
    print(f"\n{'=' * 80}")
    print(f"📊 ESTATÍSTICAS: {nome_colecao}")
    print(f"{'=' * 80}\n")
    
    # Carrega todos os pontos
    offset = None
    todos_pontos = []
    
    while True:
        resultado = client.scroll(
            collection_name=nome_colecao,
            limit=100,
            offset=offset
        )
        
        pontos, offset = resultado
        
        if not pontos:
            break
        
        todos_pontos.extend(pontos)
        
        if offset is None:
            break
    
    if not todos_pontos:
        print("⚠️  Coleção vazia!")
        return
    
    print(f"📥 Total de pontos: {len(todos_pontos)}")
    print()
    
    # Analisa campos
    primeiro_payload = todos_pontos[0].payload
    
    print("📋 Análise por campo:")
    print("─" * 80)
    
    for chave in sorted(primeiro_payload.keys()):
        valores = [p.payload.get(chave) for p in todos_pontos if p.payload.get(chave) is not None]
        
        if not valores:
            print(f"\n  {chave}: (vazio)")
            continue
        
        print(f"\n  {chave}:")
        
        # Tipo
        tipos = set(type(v).__name__ for v in valores)
        print(f"    Tipo: {', '.join(tipos)}")
        
        # Estatísticas por tipo
        if 'int' in tipos or 'float' in tipos:
            nums = [v for v in valores if isinstance(v, (int, float))]
            if nums:
                print(f"    Min: {min(nums)}")
                print(f"    Max: {max(nums)}")
                print(f"    Média: {sum(nums)/len(nums):.2f}")
        
        if 'str' in tipos:
            strs = [v for v in valores if isinstance(v, str)]
            if strs:
                print(f"    Valores únicos: {len(set(strs))}")
                print(f"    Comprimento médio: {sum(len(s) for s in strs)/len(strs):.0f} caracteres")
                
                # Top 5 valores mais comuns
                from collections import Counter
                top = Counter(strs).most_common(5)
                if len(top) <= 10:
                    print(f"    Valores:")
                    for val, count in top:
                        print(f"      • {val}: {count}x")
        
        if 'list' in tipos:
            listas = [v for v in valores if isinstance(v, list)]
            if listas:
                print(f"    Tamanho médio da lista: {sum(len(l) for l in listas)/len(listas):.1f}")
        
        # Preenchimento
        preenchidos = len(valores)
        total = len(todos_pontos)
        percentagem = (preenchidos / total) * 100
        print(f"    Preenchimento: {preenchidos}/{total} ({percentagem:.1f}%)")

# =====================================================
# 💾 EXPORTAR PARA JSON
# =====================================================

def exportar_para_json(client, nome_colecao, filepath):
    """Exporta coleção para JSON"""
    
    print(f"\n💾 A exportar {nome_colecao} para {filepath}...")
    
    # Carrega todos os pontos
    offset = None
    todos_pontos = []
    
    while True:
        resultado = client.scroll(
            collection_name=nome_colecao,
            limit=100,
            offset=offset,
            with_vectors=False
        )
        
        pontos, offset = resultado
        
        if not pontos:
            break
        
        todos_pontos.extend(pontos)
        
        if offset is None:
            break
    
    # Converte para JSON serializável
    dados = []
    for ponto in todos_pontos:
        dados.append({
            'id': ponto.id,
            'payload': ponto.payload
        })
    
    # Guarda
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Exportado {len(dados)} pontos para {filepath}")

# =====================================================
# 🎯 MENU INTERATIVO
# =====================================================

def menu_principal():
    """Menu interativo"""
    
    print("=" * 80)
    print("🔍 EXPLORADOR COMPLETO DO QDRANT")
    print("=" * 80)
    print()
    
    try:
        client = conectar_qdrant()
        print("✅ Conectado!")
        print()
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return
    
    # Lista coleções
    print("=" * 80)
    print("📦 COLEÇÕES DISPONÍVEIS")
    print("=" * 80)
    
    colecoes = listar_colecoes(client)
    
    if not colecoes:
        return
    
    print()
    for i, col in enumerate(colecoes, 1):
        emoji = "👥" if "perfis" in col['nome'] else ("🏡" if "quintas" in col['nome'] else "💬")
        print(f"{i}. {emoji} {col['nome']}")
        print(f"   Pontos: {col['pontos']}")
        print(f"   Vetor: {col['vector_size']}D ({col['distance']})")
        print()
    
    # Menu de opções
    while True:
        print("=" * 80)
        print("📋 OPÇÕES:")
        print("=" * 80)
        print()
        print("1. 📄 Ver todos os dados de uma coleção")
        print("2. 📊 Ver estatísticas de uma coleção")
        print("3. 💾 Exportar coleção para JSON")
        print("4. 🔍 Ver dados com vetores")
        print("5. 📦 Ver resumo de todas as coleções")
        print("0. 🚪 Sair")
        print()
        
        opcao = input("Escolhe uma opção: ").strip()
        
        if opcao == "0":
            print("\n👋 Até logo!")
            break
        
        elif opcao == "1":
            print("\nColeções disponíveis:")
            for i, col in enumerate(colecoes, 1):
                print(f"{i}. {col['nome']} ({col['pontos']} pontos)")
            
            num = input("\nNúmero da coleção (ou Enter para todas): ").strip()
            
            if num == "":
                # Todas
                for col in colecoes:
                    explorar_colecao(client, col['nome'], mostrar_vetores=False)
            else:
                try:
                    idx = int(num) - 1
                    if 0 <= idx < len(colecoes):
                        limite = input("Limite de pontos (Enter = todos): ").strip()
                        limite = int(limite) if limite else None
                        explorar_colecao(client, colecoes[idx]['nome'], limite=limite, mostrar_vetores=False)
                except ValueError:
                    print("❌ Número inválido!")
        
        elif opcao == "2":
            print("\nColeções disponíveis:")
            for i, col in enumerate(colecoes, 1):
                print(f"{i}. {col['nome']}")
            
            num = input("\nNúmero da coleção: ").strip()
            
            try:
                idx = int(num) - 1
                if 0 <= idx < len(colecoes):
                    gerar_estatisticas(client, colecoes[idx]['nome'])
            except ValueError:
                print("❌ Número inválido!")
        
        elif opcao == "3":
            print("\nColeções disponíveis:")
            for i, col in enumerate(colecoes, 1):
                print(f"{i}. {col['nome']}")
            
            num = input("\nNúmero da coleção: ").strip()
            
            try:
                idx = int(num) - 1
                if 0 <= idx < len(colecoes):
                    nome = colecoes[idx]['nome']
                    filepath = os.path.join(BASE_DIR, f"{nome}_export.json")
                    exportar_para_json(client, nome, filepath)
            except ValueError:
                print("❌ Número inválido!")
        
        elif opcao == "4":
            print("\nColeções disponíveis:")
            for i, col in enumerate(colecoes, 1):
                print(f"{i}. {col['nome']}")
            
            num = input("\nNúmero da coleção: ").strip()
            
            try:
                idx = int(num) - 1
                if 0 <= idx < len(colecoes):
                    limite = input("Limite de pontos (Enter = todos): ").strip()
                    limite = int(limite) if limite else None
                    explorar_colecao(client, colecoes[idx]['nome'], limite=limite, mostrar_vetores=True)
            except ValueError:
                print("❌ Número inválido!")
        
        elif opcao == "5":
            print()
            for col in colecoes:
                emoji = "👥" if "perfis" in col['nome'] else ("🏡" if "quintas" in col['nome'] else "💬")
                print(f"{emoji} {col['nome']}: {col['pontos']} pontos")
        
        else:
            print("❌ Opção inválida!")
        
        input("\n[Enter para continuar]")
        print("\n" * 2)

# =====================================================
# 🎯 EXECUÇÃO DIRETA
# =====================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Modo não-interativo
        client = conectar_qdrant()
        
        if sys.argv[1] == "--list":
            # Lista coleções
            colecoes = listar_colecoes(client)
            for col in colecoes:
                print(f"{col['nome']}: {col['pontos']} pontos")
        
        elif sys.argv[1] == "--export" and len(sys.argv) > 2:
            # Exporta coleção
            nome_colecao = sys.argv[2]
            filepath = sys.argv[3] if len(sys.argv) > 3 else f"{nome_colecao}_export.json"
            exportar_para_json(client, nome_colecao, filepath)
        
        elif sys.argv[1] == "--show" and len(sys.argv) > 2:
            # Mostra coleção
            nome_colecao = sys.argv[2]
            limite = int(sys.argv[3]) if len(sys.argv) > 3 else None
            explorar_colecao(client, nome_colecao, limite=limite)
        
        elif sys.argv[1] == "--stats" and len(sys.argv) > 2:
            # Estatísticas
            nome_colecao = sys.argv[2]
            gerar_estatisticas(client, nome_colecao)
        
        else:
            print("Uso:")
            print("  python explorar_qdrant.py                    # Menu interativo")
            print("  python explorar_qdrant.py --list             # Lista coleções")
            print("  python explorar_qdrant.py --show COLECAO [N] # Mostra N pontos")
            print("  python explorar_qdrant.py --stats COLECAO    # Estatísticas")
            print("  python explorar_qdrant.py --export COLECAO   # Exporta JSON")
    
    else:
        # Menu interativo
        menu_principal()