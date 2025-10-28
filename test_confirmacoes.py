"""
Script de teste do sistema de confirmações
Corre este ficheiro da raiz do projeto
"""
import sys
import os

# Garante que está na raiz
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from modules.perfis_manager import buscar_perfil, listar_familia
from modules.confirmacoes import (
    confirmar_pessoa,
    get_confirmados,
    get_estatisticas
)

print("🧪 Testando sistema de confirmações...\n")

# Teste 1: Confirmar Barbeitos
print("✅ Teste 1: Confirmando Barbeitos...")
resultado = confirmar_pessoa("Barbeitos")
print(f"   {resultado['mensagem']}")
if resultado["familia_sugerida"]:
    print(f"   💡 Família sugerida: {', '.join(resultado['familia_sugerida'])}")

# Teste 2: Confirmar Jorge
print("\n✅ Teste 2: Confirmando Jorge...")
resultado = confirmar_pessoa("Jorge")
print(f"   {resultado['mensagem']}")
if resultado["familia_sugerida"]:
    print(f"   💡 Família sugerida: {', '.join(resultado['familia_sugerida'])}")

# Teste 3: Confirmar Isabel (pela Jorge)
print("\n✅ Teste 3: Jorge confirma a Isabel...")
resultado = confirmar_pessoa("Isabel", confirmado_por="Jorge")
print(f"   {resultado['mensagem']}")

# Estatísticas
print("\n📊 Estatísticas:")
stats = get_estatisticas()
print(f"   Total confirmados: {stats['total_confirmados']}")
print(f"   Famílias completas: {stats['familias_completas']}")
print(f"   Famílias parciais: {stats['familias_parciais']}")

# Lista
print("\n📋 Lista completa de confirmados:")
for nome in get_confirmados():
    perfil = buscar_perfil(nome)
    familia = perfil.get('familia_id', 'N/A') if perfil else 'N/A'
    print(f"   • {nome} ({familia})")

print("\n✅ Testes concluídos!")