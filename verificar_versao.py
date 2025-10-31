#!/usr/bin/env python3
"""
Script para verificar qual versão do llm_groq.py está instalada
"""

def verificar_versao(filepath="llm_groq.py"):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        print("🔍 VERIFICANDO VERSÃO DO llm_groq.py\n")
        print("="*60)
        
        # Verificar tamanho
        tamanho = len(conteudo)
        print(f"📦 Tamanho: {tamanho:,} bytes ({tamanho/1024:.1f} KB)")
        
        # Verificar features
        features = {
            "v4.0": '"indisponível" NOT LIKE' in conteudo,
            "v4.1": 'ultima_lista_quintas' in conteudo,
            "v4.2": '"e as outras"' in conteudo,
            "v4.3": 'ultima_pergunta_tipo' in conteudo,
            "v4.4": 'from difflib import get_close_matches' in conteudo,
            "v4.5": 'distancias_lisboa' in conteudo,
            "v4.6": '"ja temos sitio"' in conteudo or 'já temos sítio' in conteudo,
        }
        
        print("\n✅ FEATURES DETECTADAS:\n")
        versao_atual = "v3.x ou anterior"
        for versao, presente in features.items():
            status = "✅" if presente else "❌"
            print(f"{status} {versao}: {'SIM' if presente else 'NÃO'}")
            if presente:
                versao_atual = versao
        
        print("\n" + "="*60)
        print(f"📌 VERSÃO INSTALADA: {versao_atual}")
        print("="*60)
        
        if versao_atual != "v4.6":
            print(f"\n⚠️  ATENÇÃO: Não está na versão v4.6!")
            print(f"   Versão atual: {versao_atual}")
            print(f"   Versão esperada: v4.6")
            print("\n   Por favor, instala a v4.6 seguindo o guia.")
        else:
            print("\n🎉 TUDO OK! Estás na versão v4.6!")
        
        return versao_atual
        
    except FileNotFoundError:
        print(f"❌ Ficheiro não encontrado: {filepath}")
        return None
    except Exception as e:
        print(f"❌ Erro: {e}")
        return None

if __name__ == "__main__":
    import sys
    filepath = sys.argv[1] if len(sys.argv) > 1 else "llm_groq.py"
    verificar_versao(filepath)