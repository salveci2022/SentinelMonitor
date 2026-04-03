"""
SPYNET OSINT — VERSÃO PARA RENDER (CORRIGIDA)
"""

from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from datetime import datetime, timezone, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdf_canvas
from functools import wraps
import json, os, requests, hashlib, uuid

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "spynet-osint-2026")

BR_TZ = timezone(timedelta(hours=-3))

# ============================================
# CONFIGURAÇÕES
# ============================================
SISTEMA_SENHA = os.environ.get("SISTEMA_SENHA", "spynet2026")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CASOS_FILE = os.path.join(DATA_DIR, "casos.json")

for pasta in [DATA_DIR]:
    os.makedirs(pasta, exist_ok=True)

# ============================================
# FUNÇÕES DOS CASOS
# ============================================

def _load(path, default):
    try:
        if not os.path.exists(path): return default
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: return default

def _save(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def load_casos(): return _load(CASOS_FILE, [])
def save_casos(c): _save(CASOS_FILE, c)

def now_br():
    return datetime.now(BR_TZ).strftime("%d/%m/%Y %H:%M")

def login_required(f):
    @wraps(f)
    def dec(*args, **kwargs):
        if not session.get("logado"): return redirect(url_for("login"))
        return f(*args, **kwargs)
    return dec

# ============================================
# FUNÇÕES OSINT
# ============================================

def buscar_redes_sociais(nome, username=None):
    resultados = []
    redes = [
        {"nome": "Instagram", "url": f"https://www.instagram.com/{username if username else nome.replace(' ', '')}", "icone": "📷"},
        {"nome": "Facebook", "url": f"https://www.facebook.com/search/top?q={nome.replace(' ', '%20')}", "icone": "📘"},
        {"nome": "Twitter/X", "url": f"https://twitter.com/search?q={nome.replace(' ', '%20')}", "icone": "🐦"},
        {"nome": "LinkedIn", "url": f"https://www.linkedin.com/search/results/people/?keywords={nome.replace(' ', '%20')}", "icone": "💼"},
        {"nome": "TikTok", "url": f"https://www.tiktok.com/search?q={nome.replace(' ', '%20')}", "icone": "🎵"},
        {"nome": "YouTube", "url": f"https://www.youtube.com/results?search_query={nome.replace(' ', '+')}", "icone": "📺"},
    ]
    for rede in redes:
        resultados.append({"categoria": "🌐 REDES SOCIAIS", "titulo": rede["nome"], "url": rede["url"], "icone": rede["icone"]})
    return resultados

# ============================================
# ROTAS
# ============================================

@app.route("/")
def index():
    if not session.get("logado"): 
        return redirect(url_for("login"))
    return redirect(url_for("painel"))

@app.route("/login", methods=["GET", "POST"])
def login():
    erro = ""
    if request.method == "POST":
        senha = request.form.get("senha")
        if senha == SISTEMA_SENHA:
            session["logado"] = True
            return redirect(url_for("painel"))
        else:
            erro = "Senha incorreta!"
    return render_template_string(LOGIN_HTML, erro=erro)

@app.route("/logout")
def logout():
    session.pop("logado", None)
    return redirect(url_for("login"))

@app.route("/painel")
@login_required
def painel():
    casos = load_casos()
    total = len(casos)
    ativos = len([c for c in casos if c.get("status") == "Em andamento"])
    concl = len([c for c in casos if c.get("status") == "Concluído"])
    return render_template_string(PAINEL_HTML, 
        casos=list(reversed(casos)),
        total=total, ativos=ativos, concl=concl)

@app.route("/osint/redes", methods=["POST"])
@login_required
def osint_redes():
    data = request.get_json() or {}
    nome = data.get("nome", "")
    username = data.get("username", "")
    resultados = buscar_redes_sociais(nome, username)
    return jsonify({"resultados": resultados})

@app.route("/osint/pesquisar")
@login_required
def osint_pesquisar():
    return render_template_string(OSINT_HTML)

@app.route("/novo_caso", methods=["GET","POST"])
@login_required
def novo_caso():
    if request.method == "POST":
        d = request.form
        caso = {
            "id": f"SPN-{datetime.now(BR_TZ).strftime('%Y%m%d%H%M%S')}",
            "criado_em": now_br(),
            "investigador": "Salveci dos Santos",
            "status": "Em andamento",
            "tipo": d.get("tipo", ""),
            "cliente": d.get("cliente", ""),
            "investigado": d.get("investigado", ""),
            "objetivo": d.get("objetivo", ""),
            "etapas": [],
            "notas": d.get("notas", ""),
        }
        casos = load_casos()
        casos.append(caso)
        save_casos(casos)
        return redirect(url_for("caso_detalhe", caso_id=caso["id"]))
    return render_template_string(NOVO_CASO_HTML)

@app.route("/caso/<caso_id>")
@login_required
def caso_detalhe(caso_id):
    casos = load_casos()
    caso = next((c for c in casos if c["id"] == caso_id), None)
    if not caso: return redirect(url_for("painel"))
    return render_template_string(CASO_DETALHE_HTML, caso=caso)

@app.route("/api/caso/<caso_id>/etapa", methods=["POST"])
@login_required
def adicionar_etapa(caso_id):
    data = request.get_json(force=True, silent=True) or {}
    casos = load_casos()
    for c in casos:
        if c["id"] == caso_id:
            etapa = {
                "num": len(c.get("etapas", [])) + 1,
                "titulo": data.get("titulo", ""),
                "tipo": data.get("tipo", ""),
                "dados": data.get("dados", ""),
                "ts": now_br()
            }
            c.setdefault("etapas", []).append(etapa)
            break
    save_casos(casos)
    return jsonify({"ok": True})

@app.route("/api/caso/<caso_id>/status", methods=["POST"])
@login_required
def atualizar_status(caso_id):
    data = request.get_json(force=True, silent=True) or {}
    casos = load_casos()
    for c in casos:
        if c["id"] == caso_id:
            c["status"] = data.get("status", c["status"])
            break
    save_casos(casos)
    return jsonify({"ok": True})

@app.route("/api/limpar_casos", methods=["POST"])
@login_required
def limpar_casos():
    save_casos([])
    return jsonify({"ok": True})

@app.route("/relatorio/<caso_id>.pdf")
@login_required
def gerar_relatorio(caso_id):
    casos = load_casos()
    caso = next((c for c in casos if c["id"] == caso_id), None)
    if not caso: return "Caso não encontrado", 404

    buffer = BytesIO()
    c = pdf_canvas.Canvas(buffer, pagesize=A4)
    W, H = A4

    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, H - 50, "RELATÓRIO DE INVESTIGAÇÃO")
    c.setFont("Helvetica", 10)
    c.drawString(50, H - 80, f"ID: {caso['id']} - Emitido: {now_br()}")
    c.drawString(50, H - 100, f"Investigado: {caso.get('investigado', '—')}")
    c.drawString(50, H - 120, f"Cliente: {caso.get('cliente', '—')}")
    c.drawString(50, H - 140, f"Status: {caso.get('status', '—')}")
    c.drawString(50, H - 160, f"Objetivo: {caso.get('objetivo', '—')}")
    c.showPage()
    c.save()
    buffer.seek(0)

    nome = f"relatorio_{caso['id']}.pdf"
    return send_file(buffer, as_attachment=True, download_name=nome, mimetype="application/pdf")

# ============================================
# TEMPLATES
# ============================================

LOGIN_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SPYNET — ACESSO</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{background:linear-gradient(135deg,#0a0a2a,#1a1a3a);font-family:'Segoe UI',Arial;display:flex;justify-content:center;align-items:center;height:100vh}
        .card{background:rgba(255,255,255,0.1);backdrop-filter:blur(10px);border-radius:20px;padding:40px;width:380px;text-align:center}
        h1{color:#00ffcc}
        input{width:100%;padding:14px;margin:10px 0;background:rgba(0,0,0,0.5);border:1px solid #00ffcc;border-radius:10px;color:white;font-size:16px}
        button{width:100%;padding:14px;background:#00ffcc;border:none;border-radius:10px;font-weight:bold;cursor:pointer;font-size:16px}
        .erro{color:#ff4444;margin-top:10px}
    </style>
</head>
<body>
<div class="card">
    <h1>🔍 SPYNET</h1>
    <form method="POST">
        <input type="password" name="senha" placeholder="Senha" autofocus required>
        <button type="submit">🔐 ACESSAR</button>
    </form>
    {% if erro %}<div class="erro">{{ erro }}</div>{% endif %}
</div>
</body>
</html>
'''

PAINEL_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SPYNET — Painel</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);color:#fff;font-family:Arial;padding:20px}
        .navbar{background:rgba(0,0,0,0.8);padding:15px;border-radius:15px;display:flex;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:10px}
        .logo{font-size:24px;font-weight:bold;color:#00ffcc}
        .btn{background:#00ffcc;border:none;padding:8px 18px;border-radius:25px;cursor:pointer;text-decoration:none;color:#000;font-weight:bold;display:inline-block}
        .btn-red{background:#ff4444;color:#fff}
        .stats{display:flex;gap:20px;margin-bottom:20px;flex-wrap:wrap}
        .stat-card{background:rgba(255,255,255,0.1);border-radius:15px;padding:20px;flex:1;text-align:center}
        .stat-number{font-size:32px;font-weight:bold;color:#00ffcc}
        .caso-card{background:rgba(255,255,255,0.1);border-radius:15px;padding:15px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap}
        .btn-pequeno{background:#00ffcc;padding:5px 12px;border-radius:20px;text-decoration:none;color:#000;font-size:12px}
        .btn-pdf{background:#00cc66;color:#fff}
    </style>
</head>
<body>
<div class="navbar"><div class="logo">🔍 SPYNET OSINT</div>
<div><a href="/osint/pesquisar" class="btn">🔎 OSINT</a><a href="/novo_caso" class="btn">➕ Novo Caso</a><button class="btn btn-red" onclick="limparTodosCasos()">🗑️ LIMPAR</button><a href="/logout" class="btn btn-red">🚪 Sair</a></div></div>
<div class="stats"><div class="stat-card"><div class="stat-number">{{ total }}</div><div>Total Casos</div></div><div class="stat-card"><div class="stat-number">{{ ativos }}</div><div>Em Andamento</div></div><div class="stat-card"><div class="stat-number">{{ concl }}</div><div>Concluídos</div></div></div>
<h3>📁 Meus Casos</h3>
{% for caso in casos %}
<div class="caso-card"><div><strong>{{ caso.id }}</strong><br><small>{{ caso.investigado }} • {{ caso.status }}</small></div><div><a href="/caso/{{ caso.id }}" class="btn-pequeno">👁️ Ver</a><a href="/relatorio/{{ caso.id }}.pdf" class="btn-pequeno btn-pdf">📄 PDF</a></div></div>
{% else %}<p>Nenhum caso registrado. <a href="/novo_caso" style="color:#00ffcc">Criar primeiro caso →</a></p>{% endfor %}
<script>function limparTodosCasos(){if(confirm('Remover todos os casos?')){fetch('/api/limpar_casos',{method:'POST'}).then(()=>location.reload());}}</script>
</body>
</html>
'''

NOVO_CASO_HTML = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>SPYNET — Novo Caso</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);color:#fff;font-family:Arial;padding:20px}
.navbar{background:rgba(0,0,0,0.8);padding:15px;border-radius:15px;display:flex;justify-content:space-between;margin-bottom:20px}
.logo{font-size:24px;font-weight:bold;color:#00ffcc}
.btn{background:#00ffcc;border:none;padding:8px 18px;border-radius:25px;cursor:pointer;text-decoration:none;color:#000}
.card{background:rgba(255,255,255,0.1);border-radius:20px;padding:25px;max-width:600px;margin:0 auto}
input,select,textarea{width:100%;padding:12px;margin:10px 0;background:rgba(0,0,0,0.5);border:1px solid #00ffcc;border-radius:10px;color:#fff}
button{background:#00ffcc;border:none;padding:12px;border-radius:10px;font-weight:bold;cursor:pointer;width:100%}
</style>
</head>
<body><div class="navbar"><div class="logo">🔍 SPYNET</div><a href="/painel" class="btn">← Voltar</a></div>
<div class="card"><h2>➕ Novo Caso</h2>
<form method="POST">
<select name="tipo" required><option value="">Tipo de caso...</option><option>Investigação de pessoa física</option><option>Investigação de pessoa jurídica</option><option>Localização patrimonial</option><option>Análise de crédito</option></select>
<input type="text" name="cliente" placeholder="Cliente" required>
<input type="text" name="investigado" placeholder="Investigado" required>
<textarea name="objetivo" rows="3" placeholder="Objetivo" required></textarea>
<textarea name="notas" rows="3" placeholder="Notas"></textarea>
<button type="submit">🔍 CRIAR CASO</button>
</form>
</div>
</body>
</html>
'''

CASO_DETALHE_HTML = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>SPYNET — {{ caso.id }}</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);color:#fff;font-family:Arial;padding:20px}
.navbar{background:rgba(0,0,0,0.8);padding:15px;border-radius:15px;display:flex;justify-content:space-between;margin-bottom:20px}
.logo{font-size:24px;font-weight:bold;color:#00ffcc}
.btn{background:#00ffcc;border:none;padding:8px 18px;border-radius:25px;cursor:pointer;text-decoration:none;color:#000}
.card{background:rgba(255,255,255,0.1);border-radius:20px;padding:25px;margin-bottom:20px}
.status{display:inline-block;padding:5px 12px;border-radius:20px;font-size:12px}
.status-andamento{background:#ffaa00;color:#000}
.status-concluido{background:#00cc66;color:#000}
.etapa-card{background:rgba(0,0,0,0.3);border-radius:15px;padding:15px;margin-bottom:10px}
input,textarea,select{width:100%;padding:12px;margin:10px 0;background:rgba(0,0,0,0.5);border:1px solid #00ffcc;border-radius:10px;color:#fff}
button{background:#00ffcc;border:none;padding:12px;border-radius:10px;font-weight:bold;cursor:pointer}
.badge{background:rgba(0,136,255,0.3);padding:3px 8px;border-radius:5px;font-size:11px}
</style>
</head>
<body><div class="navbar"><div class="logo">🔍 SPYNET</div><a href="/painel" class="btn">← Painel</a></div>
<div class="card"><h2>{{ caso.investigado }}</h2><p><span class="badge">{{ caso.id }}</span> • {{ caso.criado_em }}</p><p><strong>Cliente:</strong> {{ caso.cliente }}</p><p><strong>Tipo:</strong> {{ caso.tipo }}</p><p><strong>Status:</strong> <span class="status status-{{ 'andamento' if caso.status == 'Em andamento' else 'concluido' }}">{{ caso.status }}</span></p><p><strong>Objetivo:</strong> {{ caso.objetivo }}</p>{% if caso.notas %}<p><strong>Notas:</strong> {{ caso.notas }}</p>{% endif %}</div>
<div class="card"><h3>📋 Etapas</h3>{% for e in caso.etapas %}<div class="etapa-card"><strong>Etapa {{ e.num }}: {{ e.titulo }}</strong><div><span class="badge">{{ e.tipo }}</span> • {{ e.ts }}</div><p style="margin-top:10px">{{ e.dados }}</p></div>{% else %}<p>Nenhuma etapa registrada.</p>{% endfor %}</div>
<div class="card"><h3>➕ Adicionar Etapa</h3><input type="text" id="titulo" placeholder="Título"><select id="tipo"><option>Identificação</option><option>OSINT</option><option>Patrimonial</option><option>Conclusão</option></select><textarea id="dados" rows="5" placeholder="Dados"></textarea><button onclick="adicionarEtapa()">➕ SALVAR</button></div>
<script>const CASO_ID = "{{ caso.id }}";async function adicionarEtapa(){const t=document.getElementById('titulo').value,ti=document.getElementById('tipo').value,d=document.getElementById('dados').value;if(!t||!d){alert('Preencha tudo');return}const r=await fetch(`/api/caso/${CASO_ID}/etapa`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({titulo:t,tipo:ti,dados:d})});if((await r.json()).ok)location.reload()}</script>
</body>
</html>
'''

OSINT_HTML = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>SPYNET — OSINT</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);color:#fff;font-family:Arial;padding:20px}
.navbar{background:rgba(0,0,0,0.8);padding:15px;border-radius:15px;display:flex;justify-content:space-between;margin-bottom:20px}
.logo{font-size:24px;font-weight:bold;color:#00ffcc}
.btn{background:#00ffcc;border:none;padding:8px 18px;border-radius:25px;cursor:pointer;text-decoration:none;color:#000}
.card{background:rgba(255,255,255,0.1);border-radius:20px;padding:25px;margin-bottom:20px}
input{width:100%;padding:12px;margin:10px 0;background:rgba(0,0,0,0.5);border:1px solid #00ffcc;border-radius:10px;color:#fff}
button{background:#00ffcc;border:none;padding:12px;border-radius:10px;font-weight:bold;cursor:pointer;width:100%}
.resultado-card{background:rgba(0,0,0,0.3);border-left:2px solid #00ffcc;padding:12px;margin-bottom:8px}
.resultado-card a{color:#00ffcc}
.categoria-titulo{color:#ffaa44;margin:15px 0 8px}
</style>
</head>
<body><div class="navbar"><div class="logo">🔍 SPYNET OSINT</div><div><a href="/painel" class="btn">← Painel</a></div></div>
<div class="card"><h2>🌐 REDES SOCIAIS</h2><input type="text" id="rede_nome" placeholder="Nome completo"><input type="text" id="rede_username" placeholder="Username"><button onclick="buscarRedes()">🔍 BUSCAR</button><div id="rede_resultados"></div></div>
<script>
async function buscarRedes(){const n=document.getElementById('rede_nome').value,u=document.getElementById('rede_username').value;if(!n&&!u){alert('Digite nome ou username');return;}const r=await fetch('/osint/redes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nome:n,username:u})});const d=await r.json();let h='',cat='';d.resultados.forEach(r=>{if(cat!==r.categoria){h+=`<div class="categoria-titulo">${r.categoria}</div>`;cat=r.categoria;}h+=`<div class="resultado-card"><strong>${r.titulo}</strong><br><a href="${r.url}" target="_blank">${r.url}</a></div>`;});document.getElementById('rede_resultados').innerHTML=h;}
</script>
</body>
</html>
'''

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 50)
    print("🔍 SPYNET OSINT - RENDER VERSION")
    print(f"🔐 Senha: {SISTEMA_SENHA}")
    print(f"📱 Acesse: http://0.0.0.0:{port}")
    print("=" * 50)
    app.run(host="0.0.0.0", port=port, debug=False)