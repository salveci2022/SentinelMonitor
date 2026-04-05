#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PAINEL DE ADMINISTRAÇÃO SPYNET OSINT
Execute em um servidor separado (ou local) para gerenciar clientes.

Variáveis de ambiente necessárias:
  ADMIN_SECRET_KEY = <gerado com secrets.token_hex(32)>
  ADMIN_SENHA      = <sua senha de administrador>
"""

from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import json
import os
import secrets
from datetime import datetime

app = Flask(__name__)

# ==============================================
# SEGURANÇA - via variáveis de ambiente
# ==============================================
app.secret_key = os.environ.get('ADMIN_SECRET_KEY', secrets.token_hex(32))
ADMIN_SENHA = os.environ.get('ADMIN_SENHA')

CHAVES_FILE = "chaves_geradas.json"

def load_chaves():
    if os.path.exists(CHAVES_FILE):
        with open(CHAVES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_chaves(chaves):
    with open(CHAVES_FILE, 'w', encoding='utf-8') as f:
        json.dump(chaves, f, ensure_ascii=False, indent=2)

# ============================================
# TEMPLATES
# ============================================

ADMIN_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SPYNET ADMIN</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{background:#0a0e1a;font-family:'Courier New',monospace;color:#e8edf5;padding:20px}
        .navbar{background:linear-gradient(90deg,#050a12,#0a0e1a);border-bottom:2px solid #0088ff;padding:15px;margin-bottom:25px;display:flex;justify-content:space-between;align-items:center}
        .logo{font-size:24px;color:#00ffcc;text-shadow:0 0 8px #00ffcc}
        .stats{display:flex;gap:20px;margin-bottom:25px;flex-wrap:wrap}
        .stat-card{background:rgba(0,20,40,0.6);border:1px solid #0088ff;padding:20px;border-radius:4px;flex:1;text-align:center}
        .stat-number{font-size:32px;color:#00ffcc}
        table{width:100%;border-collapse:collapse}
        th,td{padding:12px;text-align:left;border-bottom:1px solid #1a2a3a}
        th{color:#00ffcc}
        .btn{background:#0088ff;border:none;padding:5px 12px;border-radius:3px;cursor:pointer;color:#0a0e1a;text-decoration:none}
        .btn-danger{background:#ff2244;color:#fff}
        .btn-logout{background:rgba(255,34,68,0.2);color:#ff2244;border:1px solid #ff2244;padding:6px 14px;border-radius:4px;text-decoration:none}
        .status-ativa{color:#00cc66}
        .status-desativada{color:#ff2244}
        code{background:rgba(0,136,255,0.1);padding:2px 6px;border-radius:3px;font-size:12px}
    </style>
</head>
<body>
<div class="navbar">
    <div class="logo">🕵️ SPYNET ADMIN</div>
    <a href="/admin/logout" class="btn-logout">Sair</a>
</div>

<div class="stats">
    <div class="stat-card"><div class="stat-number">{{ total }}</div><div>TOTAL DE CLIENTES</div></div>
    <div class="stat-card"><div class="stat-number">{{ ativas }}</div><div>LICENÇAS ATIVAS</div></div>
    <div class="stat-card"><div class="stat-number">{{ vencidas }}</div><div>LICENÇAS DESATIVADAS</div></div>
</div>

<h2 style="margin-bottom:15px;color:#00ffcc">📋 CLIENTES E LICENÇAS</h2>
<table>
    <thead>
        <tr><th>CHAVE</th><th>CLIENTE</th><th>TIPO</th><th>EXPIRAÇÃO</th><th>STATUS</th><th>AÇÕES</th></tr>
    </thead>
    <tbody>
        {% for c in chaves %}
        <tr>
            <td><code>{{ c.chave }}</code></td>
            <td>{{ c.cliente }}</td>
            <td>{{ c.tipo }}</td>
            <td>{{ c.expiracao }}</td>
            <td class="status-{{ 'ativa' if c.ativa else 'desativada' }}">{{ '✅ ATIVA' if c.ativa else '❌ DESATIVADA' }}</td>
            <td>
                {% if c.ativa %}
                <button class="btn btn-danger" onclick="desativar('{{ c.chave }}')">Desativar</button>
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>

<script>
function desativar(chave) {
    if(confirm('Desativar esta licença?')) {
        fetch('/admin/desativar', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({chave: chave})
        }).then(r => r.json()).then(() => location.reload());
    }
}
</script>
</body>
</html>
'''

LOGIN_ADMIN_HTML = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Admin Login</title>
<style>
body{background:#0a0e1a;display:flex;justify-content:center;align-items:center;height:100vh;font-family:monospace}
.card{background:rgba(0,20,40,0.6);border:1px solid #0088ff;padding:40px;border-radius:4px;width:350px}
h2{color:#00ffcc;margin-bottom:20px}
input{width:100%;padding:12px;margin:10px 0;background:#0a0e1a;border:1px solid #0088ff;color:#00ffcc;border-radius:4px}
button{width:100%;padding:12px;background:#0088ff;border:none;cursor:pointer;border-radius:4px;font-weight:bold}
.erro{color:#ff2244;margin-top:10px}
</style>
</head>
<body>
<div class="card">
<h2>🔐 ADMIN LOGIN</h2>
<form method="POST">
<input type="password" name="senha" placeholder="Senha de administrador" autofocus>
<button type="submit">ENTRAR</button>
{% if erro %}<div class="erro">{{ erro }}</div>{% endif %}
</form>
</div>
</body>
</html>
'''

# ============================================
# ROTAS
# ============================================

@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if not ADMIN_SENHA:
        return "❌ ADMIN_SENHA não configurada no ambiente.", 500
    erro = ""
    if request.method == "POST":
        if request.form.get("senha") == ADMIN_SENHA:
            session["admin_logado"] = True
            return redirect(url_for("admin_dashboard"))
        erro = "Senha incorreta"
    return render_template_string(LOGIN_ADMIN_HTML, erro=erro)

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_logado"):
        return redirect(url_for("admin_login"))
    chaves = load_chaves()
    total = len(chaves)
    ativas = len([c for c in chaves if c.get("ativa", True)])
    vencidas = len([c for c in chaves if not c.get("ativa", True)])
    return render_template_string(ADMIN_HTML,
        chaves=chaves, total=total, ativas=ativas, vencidas=vencidas)

@app.route("/admin/desativar", methods=["POST"])
def admin_desativar():
    if not session.get("admin_logado"):
        return jsonify({"erro": "Não autorizado"}), 401
    data = request.get_json()
    chave = data.get("chave")
    chaves = load_chaves()
    for c in chaves:
        if c["chave"] == chave:
            c["ativa"] = False
            break
    save_chaves(chaves)
    return jsonify({"ok": True})

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logado", None)
    return redirect(url_for("admin_login"))

# ============================================
# MAIN
# ============================================
if __name__ == "__main__":
    print("=" * 50)
    print("🕵️ SPYNET ADMIN - PAINEL DE CONTROLE")
    print("=" * 50)
    if not ADMIN_SENHA:
        print("⚠️  ATENÇÃO: ADMIN_SENHA não definida!")
        print("   Execute: export ADMIN_SENHA='sua_senha'")
    print("📱 Acesse: http://localhost:5001/admin")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5001, debug=False)
