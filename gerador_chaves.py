#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SPYNET — GERADOR DE CHAVES
Execute localmente para gerar chaves para seus clientes.
Apos gerar, commite data/chaves_validas.json no GitHub.
"""

import secrets
from datetime import datetime, timedelta
import json, os

CHAVES_GERADAS = "data/chaves_geradas.json"
CHAVES_VALIDAS = "data/chaves_validas.json"
os.makedirs('data', exist_ok=True)

PLANOS = {
    "1": {"dias": 30,   "tipo": "MENSAL",     "preco": "R$ 97"},
    "2": {"dias": 90,   "tipo": "TRIMESTRAL", "preco": "R$ 247"},
    "3": {"dias": 365,  "tipo": "ANUAL",       "preco": "R$ 497"},
    "4": {"dias": 9999, "tipo": "VITALICIA",   "preco": "R$ 997"},
    "5": {"dias": 7,    "tipo": "TRIAL",       "preco": "Gratis"},
}

def gerar_chave(cliente, dias, tipo):
    expiracao = datetime.now() + timedelta(days=dias)
    token = secrets.token_hex(12).upper()
    chave = '-'.join([token[i:i+4] for i in range(0, 24, 4)])
    return {
        "chave": chave, "cliente": cliente, "tipo": tipo, "dias": dias,
        "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "expiracao": expiracao.strftime("%d/%m/%Y"),
        "expiracao_timestamp": expiracao.timestamp(),
        "ativa": True, "ultimo_acesso": ""
    }

def _load(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)
    return []

def _save(path, dados):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f: json.dump(dados, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def adicionar_chave(c):
    for path in [CHAVES_GERADAS, CHAVES_VALIDAS]:
        dados = _load(path); dados.append(c); _save(path, dados)

def desativar_chave(chave):
    for path in [CHAVES_GERADAS, CHAVES_VALIDAS]:
        dados = _load(path)
        for c in dados:
            if c['chave'].upper() == chave.upper(): c['ativa'] = False
        _save(path, dados)

def main():
    while True:
        print("\n" + "="*60)
        print("  SPYNET SECURITY - GERADOR DE CHAVES")
        print("="*60)
        print("  1. Gerar nova chave")
        print("  2. Listar chaves")
        print("  3. Desativar chave")
        print("  4. Sair")
        opcao = input("  Escolha: ").strip()

        if opcao == "1":
            cliente = input("\n  Nome do cliente: ").strip()
            if not cliente: print("  Nome obrigatorio!"); continue
            print("\n  PLANOS:")
            for k, v in PLANOS.items():
                print(f"    {k}. {v['tipo']:<12} {v['dias']:>5} dias - {v['preco']}")
            plano = input("  Plano (1-5): ").strip()
            if plano not in PLANOS: print("  Plano invalido!"); continue
            c = gerar_chave(cliente, PLANOS[plano]['dias'], PLANOS[plano]['tipo'])
            adicionar_chave(c)
            print("\n" + "="*60)
            print("  CHAVE GERADA!")
            print(f"  Cliente : {c['cliente']}")
            print(f"  Plano   : {c['tipo']} - {PLANOS[plano]['preco']}")
            print(f"  Expira  : {c['expiracao']}")
            print(f"\n  CHAVE: {c['chave']}")
            print("="*60)
            print("  PROXIMO PASSO: commite data/chaves_validas.json no GitHub!")
            try:
                import pyperclip; pyperclip.copy(c['chave']); print("  Copiado!")
            except: pass
            input("  Enter para continuar...")

        elif opcao == "2":
            chaves = _load(CHAVES_GERADAS)
            if not chaves: print("  Nenhuma chave ainda."); input("  Enter..."); continue
            print("\n" + "="*80)
            print(f"  {'CHAVE':<30} {'CLIENTE':<20} {'TIPO':<12} {'EXPIRA':<12} STATUS")
            print("="*80)
            for c in chaves:
                st = "ATIVA" if c.get("ativa", True) else "DESATIVADA"
                print(f"  {c['chave']:<30} {c['cliente']:<20} {c['tipo']:<12} {c['expiracao']:<12} {st}")
            print(f"\n  Total: {len(chaves)} | Ativas: {sum(1 for c in chaves if c.get('ativa',True))}")
            input("  Enter para continuar...")

        elif opcao == "3":
            chave = input("  Chave para desativar: ").strip()
            desativar_chave(chave)
            print(f"  Desativada: {chave}")
            print("  Commite data/chaves_validas.json no GitHub!")
            input("  Enter para continuar...")

        elif opcao == "4":
            print("  Saindo..."); break

if __name__ == "__main__":
    main()
