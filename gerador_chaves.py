#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GERADOR DE CHAVES SPYNET OSINT
Execute este programa para gerar chaves de ativação para seus clientes
"""

import hashlib
import random
import string
from datetime import datetime, timedelta
import json
import os

# ============================================
# CONFIGURAÇÕES
# ============================================

CHAVES_FILE = "chaves_geradas.json"

def gerar_chave(cliente_id, dias_validade, tipo="MENSAL"):
    """
    Gera uma chave de ativação única
    
    cliente_id: nome ou ID do cliente
    dias_validade: 30, 90, 180, 365
    tipo: MENSAL, TRIMESTRAL, ANUAL, VITALICIA
    """
    # Data de expiração
    expiracao = datetime.now() + timedelta(days=dias_validade)
    
    # Código aleatório
    random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    
    # Gera hash único
    dados = f"{cliente_id}-{expiracao.strftime('%Y%m%d')}-{random_code}"
    chave = hashlib.sha256(dados.encode()).hexdigest()[:24].upper()
    
    # Formata a chave (ex: ABCD-1234-EFGH-5678-IJKL-9012)
    chave_formatada = '-'.join([chave[i:i+4] for i in range(0, 24, 4)])
    
    return {
        "chave": chave_formatada,
        "cliente": cliente_id,
        "tipo": tipo,
        "dias": dias_validade,
        "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "expiracao": expiracao.strftime("%d/%m/%Y"),
        "expiracao_timestamp": expiracao.timestamp(),
        "ativa": True
    }

def salvar_chave(chave_data):
    """Salva a chave no arquivo"""
    if os.path.exists(CHAVES_FILE):
        with open(CHAVES_FILE, 'r', encoding='utf-8') as f:
            chaves = json.load(f)
    else:
        chaves = []
    
    chaves.append(chave_data)
    
    with open(CHAVES_FILE, 'w', encoding='utf-8') as f:
        json.dump(chaves, f, ensure_ascii=False, indent=2)
    
    return chave_data

def listar_chaves():
    """Lista todas as chaves geradas"""
    if os.path.exists(CHAVES_FILE):
        with open(CHAVES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def desativar_chave(chave):
    """Desativa uma chave"""
    chaves = listar_chaves()
    for c in chaves:
        if c["chave"] == chave:
            c["ativa"] = False
            break
    
    with open(CHAVES_FILE, 'w', encoding='utf-8') as f:
        json.dump(chaves, f, ensure_ascii=False, indent=2)

def main():
    print("=" * 60)
    print("🔐 SPYNET OSINT - GERADOR DE CHAVES")
    print("=" * 60)
    print("")
    
    while True:
        print("\n" + "=" * 40)
        print("1. Gerar nova chave")
        print("2. Listar chaves geradas")
        print("3. Desativar chave")
        print("4. Sair")
        print("=" * 40)
        
        opcao = input("Escolha: ")
        
        if opcao == "1":
            print("\n" + "-" * 40)
            cliente = input("Nome do cliente: ")
            
            print("\nPlanos disponíveis:")
            print("1. Mensal (30 dias) - R$ 97")
            print("2. Trimestral (90 dias) - R$ 247")
            print("3. Anual (365 dias) - R$ 497")
            print("4. Vitalícia (9999 dias) - R$ 997")
            print("5. Trial (7 dias) - Grátis")
            
            plano = input("Escolha o plano (1-5): ")
            
            planos = {
                "1": {"dias": 30, "tipo": "MENSAL"},
                "2": {"dias": 90, "tipo": "TRIMESTRAL"},
                "3": {"dias": 365, "tipo": "ANUAL"},
                "4": {"dias": 9999, "tipo": "VITALICIA"},
                "5": {"dias": 7, "tipo": "TRIAL"}
            }
            
            if plano not in planos:
                print("❌ Plano inválido!")
                continue
            
            dias = planos[plano]["dias"]
            tipo = planos[plano]["tipo"]
            
            chave_data = gerar_chave(cliente, dias, tipo)
            salvar_chave(chave_data)
            
            print("\n" + "=" * 50)
            print("✅ CHAVE GERADA COM SUCESSO!")
            print("=" * 50)
            print(f"Cliente: {chave_data['cliente']}")
            print(f"Tipo: {chave_data['tipo']}")
            print(f"Expira em: {chave_data['expiracao']}")
            print(f"\n🔑 CHAVE: {chave_data['chave']}")
            print("=" * 50)
            
            # Copiar para clipboard
            try:
                import pyperclip
                pyperclip.copy(chave_data['chave'])
                print("📋 Chave copiada para a área de transferência!")
            except:
                pass
            
            input("\nPressione Enter para continuar...")
        
        elif opcao == "2":
            chaves = listar_chaves()
            if not chaves:
                print("\n📭 Nenhuma chave gerada ainda.")
            else:
                print("\n" + "=" * 80)
                print(f"{'CHAVE':<30} {'CLIENTE':<20} {'TIPO':<12} {'EXPIRAÇÃO':<12} {'STATUS':<8}")
                print("=" * 80)
                for c in chaves:
                    status = "✅ ATIVA" if c.get("ativa", True) else "❌ DESATIVADA"
                    print(f"{c['chave']:<30} {c['cliente']:<20} {c['tipo']:<12} {c['expiracao']:<12} {status:<8}")
                print("=" * 80)
            input("\nPressione Enter para continuar...")
        
        elif opcao == "3":
            chave = input("Digite a chave para desativar: ")
            desativar_chave(chave)
            print(f"✅ Chave {chave} desativada!")
            input("\nPressione Enter para continuar...")
        
        elif opcao == "4":
            print("👋 Saindo...")
            break
        
        else:
            print("❌ Opção inválida!")

if __name__ == "__main__":
    main()