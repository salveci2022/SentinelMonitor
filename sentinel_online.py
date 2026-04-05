"""
SPYNET OSINT — VERSÃO PARA RENDER (CORRIGIDA)

Variáveis de ambiente necessárias:
  SECRET_KEY      = <gerado com secrets.token_hex(32)>
  SISTEMA_SENHA   = <senha de acesso ao sistema>
  INVESTIGADOR    = <nome do investigador responsável>
"""

from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for, send_file
from datetime import datetime, timezone, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdf_canvas
from functools import wraps
import json, os, secrets

app = Flask(__name__)

# ============================================
# CONFIGURAÇÕES - via variáveis de ambiente
# ============================================
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
SISTEMA_SENHA  = os.environ.get("SISTEMA_SENHA")
INVESTIGADOR   = os.environ.get("INVESTIGADOR", "SPYNET Investigações")

BR_TZ = timezone(timedelta(hours=-3))

DATA_DIR   = os.path.join(os.path.dirname(__file__), "data")
CASOS_FILE = os.path.join(DATA_DIR, "casos.json")
os.makedirs(DATA_DIR, exist_ok=True)

# ============================================
# HELPERS
# ============================================

def _load(path, default):
    try:
        if not os.path.exists(path): return default
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: return default

def _save(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
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
    u = username if username else nome.replace(' ', '')
    n = nome.replace(' ', '%20')
    redes = [
        {"nome": "Instagram",  "url": f"https://www.instagram.com/{u}",                                  "icone": "📷"},
        {"nome": "Facebook",   "url": f"https://www.facebook.com/search/top?q={n}",                      "icone": "📘"},
        {"nome": "Twitter/X",  "url": f"https://twitter.com/search?q={n}",                               "icone": "🐦"},
        {"nome": "LinkedIn",   "url": f"https://www.linkedin.com/search/results/people/?keywords={n}",   "icone": "💼"},
        {"nome": "TikTok",     "url": f"https://www.tiktok.com/search?q={n}",                            "icone": "🎵"},
        {"nome": "YouTube",    "url": f"https://www.youtube.com/results?search_query={n}",               "icone": "📺"},
        {"nome": "JusBrasil",  "url": f"https://www.jusbrasil.com.br/busca?q={n}",                       "icone": "📜"},
        {"nome": "HaveIBeenPwned", "url": f"https://haveibeenpwned.com/account/{u}",                     "icone": "🔐"},
    ]
    for rede in redes:
        resultados.append({
            "categoria": "🌐 REDES SOCIAIS",
            "titulo": rede["nome"],
            "url": rede["url"],
            "icone": rede["icone"]
        })
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
    if not SISTEMA_SENHA:
        return "❌ SISTEMA_SENHA não configurada no ambiente.", 500
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
    total  = len(casos)
    ativos = len([c for c in casos if c.get("status") == "Em andamento"])
    concl  = len([c for c in casos if c.get("status") == "Concluído"])
    return render_template_string(PAINEL_HTML,
        casos=list(reversed(casos)),
        total=total, ativos=ativos, concl=concl)

@app.route("/osint/redes", methods=["POST"])
@login_required
def osint_redes():
    data = request.get_json() or {}
    nome     = data.get("nome", "")
    username = data.get("username", "")
    resultados = buscar_redes_sociais(nome, username)
    return jsonify({"resultados": resultados})

@app.route("/osint/pesquisar")
@login_required
def osint_pesquisar():
    return render_template_string(OSINT_HTML)

@app.route("/novo_caso", methods=["GET", "POST"])
@login_required
def novo_caso():
    if request.method == "POST":
        d = request.form
        caso = {
            "id": f"SPN-{datetime.now(BR_TZ).strftime('%Y%m%d%H%M%S')}",
            "criado_em": now_br(),
            "investigador": INVESTIGADOR,  # via env var — não hardcoded
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

    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, H - 50, "RELATÓRIO DE INVESTIGAÇÃO")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, H - 75, f"SPYNET Intelligence — {INVESTIGADOR}")
    c.setFont("Helvetica", 10)
    c.drawString(50, H - 95,  f"Emitido em: {now_br()}")
    c.drawString(50, H - 115, f"ID do Caso: {caso['id']}")
    c.line(50, H - 125, W - 50, H - 125)
    c.drawString(50, H - 145, f"Investigado: {caso.get('investigado', '—')}")
    c.drawString(50, H - 165, f"Cliente: {caso.get('cliente', '—')}")
    c.drawString(50, H - 185, f"Tipo: {caso.get('tipo', '—')}")
    c.drawString(50, H - 205, f"Status: {caso.get('status', '—')}")
    c.drawString(50, H - 225, f"Objetivo: {caso.get('objetivo', '—')}")

    if caso.get("notas"):
        c.drawString(50, H - 245, f"Notas: {caso['notas']}")

    # Etapas
    y = H - 280
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "ETAPAS DA INVESTIGAÇÃO")
    y -= 20
    c.setFont("Helvetica", 10)
    for etapa in caso.get("etapas", []):
        if y < 60:
            c.showPage()
            y = H - 50
        c.drawString(50, y, f"Etapa {etapa['num']}: {etapa['titulo']} [{etapa['tipo']}] — {etapa['ts']}")
        y -= 15
        dados = etapa.get("dados", "")
        for linha in dados.split("\n"):
            if y < 60:
                c.showPage()
                y = H - 50
            c.drawString(70, y, linha[:90])
            y -= 13
        y -= 5

    c.save()
    buffer.seek(0)
    nome = f"relatorio_{caso['id']}.pdf"
    return send_file(buffer, as_attachment=True, download_name=nome, mimetype="application/pdf")

# ============================================
# TEMPLATES HTML
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
        h1{color:#00ffcc;margin-bottom:20px}
        input{width:100%;padding:14px;margin:10px 0;background:rgba(0,0,0,0.5);border:1px solid #00ffcc;border-radius:10px;color:white;font-size:16px}
        button{width:100%;padding:14px;background:#00ffcc;border:none;border-radius:10px;font-weight:bold;cursor:pointer;font-size:16px}
        .erro{color:#ff4444;margin-top:10px}
    </style>
</head>
<body>
<div class="card">
    <h1>🔍 SPYNET OSINT</h1>
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
        .stat-card{background:rgba(255,255,255,0.1);border-radius:15px;padding:20px;flex:1;text-align:center;min-width:120px}
        .stat-number{font-size:32px;font-weight:bold;color:#00ffcc}
        .caso-card{background:rgba(255,255,255,0.1);border-radius:15px;padding:15px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}
        .btn-pequeno{background:#00ffcc;padding:5px 12px;border-radius:20px;text-decoration:none;color:#000;font-size:12px;display:inline-block}
        .btn-pdf{background:#00cc66;color:#fff}
    </style>
</head>
<body>
<div class="navbar">
    <div class="logo">🔍 SPYNET OSINT</div>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
        <a href="/osint/pesquisar" class="btn">🔎 OSINT</a>
        <a href="/novo_caso" class="btn">➕ Novo Caso</a>
        <button class="btn btn-red" onclick="limparTodosCasos()">🗑️ Limpar</button>
        <a href="/logout" class="btn btn-red">🚪 Sair</a>
    </div>
</div>
<div class="stats">
    <div class="stat-card"><div class="stat-number">{{ total }}</div><div>Total Casos</div></div>
    <div class="stat-card"><div class="stat-number">{{ ativos }}</div><div>Em Andamento</div></div>
    <div class="stat-card"><div class="stat-number">{{ concl }}</div><div>Concluídos</div></div>
</div>
<h3 style="margin-bottom:15px">📁 Meus Casos</h3>
{% for caso in casos %}
<div class="caso-card">
    <div>
        <strong>{{ caso.id }}</strong><br>
        <small>{{ caso.investigado }} • {{ caso.status }}</small>
    </div>
    <div style="display:flex;gap:8px">
        <a href="/caso/{{ caso.id }}" class="btn-pequeno">👁️ Ver</a>
        <a href="/relatorio/{{ caso.id }}.pdf" class="btn-pequeno btn-pdf">📄 PDF</a>
    </div>
</div>
{% else %}
<p>Nenhum caso registrado. <a href="/novo_caso" style="color:#00ffcc">Criar primeiro caso →</a></p>
{% endfor %}
<script>
function limparTodosCasos(){
    if(confirm('Remover TODOS os casos? Esta ação não pode ser desfeita.')){
        fetch('/api/limpar_casos',{method:'POST'}).then(()=>location.reload());
    }
}
</script>
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
.card h2{margin-bottom:20px;color:#00ffcc}
input,select,textarea{width:100%;padding:12px;margin:10px 0;background:rgba(0,0,0,0.5);border:1px solid #00ffcc;border-radius:10px;color:#fff;font-size:14px}
button{background:#00ffcc;border:none;padding:12px;border-radius:10px;font-weight:bold;cursor:pointer;width:100%;font-size:15px}
</style>
</head>
<body>
<div class="navbar">
    <div class="logo">🔍 SPYNET</div>
    <a href="/painel" class="btn">← Voltar</a>
</div>
<div class="card">
    <h2>➕ Novo Caso</h2>
    <form method="POST">
        <select name="tipo" required>
            <option value="">Tipo de caso...</option>
            <option>Investigação de pessoa física</option>
            <option>Investigação de pessoa jurídica</option>
            <option>Localização patrimonial</option>
            <option>Análise de crédito</option>
            <option>Monitoramento de redes sociais</option>
        </select>
        <input type="text" name="cliente" placeholder="Cliente" required>
        <input type="text" name="investigado" placeholder="Investigado" required>
        <textarea name="objetivo" rows="3" placeholder="Objetivo da investigação" required></textarea>
        <textarea name="notas" rows="3" placeholder="Notas iniciais"></textarea>
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
.navbar{background:rgba(0,0,0,0.8);padding:15px;border-radius:15px;display:flex;justify-content:space-between;margin-bottom:20px;gap:10px;flex-wrap:wrap}
.logo{font-size:24px;font-weight:bold;color:#00ffcc}
.btn{background:#00ffcc;border:none;padding:8px 18px;border-radius:25px;cursor:pointer;text-decoration:none;color:#000;display:inline-block}
.btn-pdf{background:#00cc66;color:#fff}
.card{background:rgba(255,255,255,0.1);border-radius:20px;padding:25px;margin-bottom:20px}
.card h3{color:#00ffcc;margin-bottom:15px}
.status{display:inline-block;padding:5px 12px;border-radius:20px;font-size:12px}
.status-andamento{background:#ffaa00;color:#000}
.status-concluido{background:#00cc66;color:#000}
.etapa-card{background:rgba(0,0,0,0.3);border-radius:15px;padding:15px;margin-bottom:10px}
.etapa-card p{margin-top:8px;font-size:13px;line-height:1.5}
input,textarea,select{width:100%;padding:12px;margin:8px 0;background:rgba(0,0,0,0.5);border:1px solid #00ffcc;border-radius:10px;color:#fff;font-size:14px}
button{background:#00ffcc;border:none;padding:12px;border-radius:10px;font-weight:bold;cursor:pointer;font-size:14px}
.badge{background:rgba(0,136,255,0.3);padding:3px 8px;border-radius:5px;font-size:11px}
.info-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin-top:10px}
.info-item label{font-size:11px;color:#aaa;display:block}
.info-item span{font-size:14px}
</style>
</head>
<body>
<div class="navbar">
    <div class="logo">🔍 SPYNET</div>
    <div style="display:flex;gap:8px">
        <a href="/relatorio/{{ caso.id }}.pdf" class="btn btn-pdf">📄 PDF</a>
        <a href="/painel" class="btn">← Painel</a>
    </div>
</div>
<div class="card">
    <h3>{{ caso.investigado }}</h3>
    <span class="badge">{{ caso.id }}</span> &bull; {{ caso.criado_em }}
    <div class="info-grid" style="margin-top:15px">
        <div class="info-item"><label>Cliente</label><span>{{ caso.cliente }}</span></div>
        <div class="info-item"><label>Tipo</label><span>{{ caso.tipo }}</span></div>
        <div class="info-item"><label>Investigador</label><span>{{ caso.investigador }}</span></div>
        <div class="info-item"><label>Status</label>
            <span class="status status-{{ 'andamento' if caso.status == 'Em andamento' else 'concluido' }}">{{ caso.status }}</span>
        </div>
    </div>
    <div style="margin-top:15px"><label style="font-size:11px;color:#aaa">Objetivo</label><p>{{ caso.objetivo }}</p></div>
    {% if caso.notas %}<div style="margin-top:10px"><label style="font-size:11px;color:#aaa">Notas</label><p>{{ caso.notas }}</p></div>{% endif %}
    <div style="margin-top:15px;display:flex;gap:10px;flex-wrap:wrap">
        <button onclick="mudarStatus('Concluído')" style="background:#00cc66">✅ Concluir</button>
        <button onclick="mudarStatus('Em andamento')" style="background:#ffaa00;color:#000">🔄 Reabrir</button>
    </div>
</div>
<div class="card">
    <h3>📋 Etapas da Investigação</h3>
    {% for e in caso.etapas %}
    <div class="etapa-card">
        <strong>Etapa {{ e.num }}: {{ e.titulo }}</strong>
        <div style="margin-top:4px"><span class="badge">{{ e.tipo }}</span> &bull; {{ e.ts }}</div>
        <p>{{ e.dados }}</p>
    </div>
    {% else %}<p style="color:#aaa">Nenhuma etapa registrada.</p>{% endfor %}
</div>
<div class="card">
    <h3>➕ Adicionar Etapa</h3>
    <input type="text" id="titulo" placeholder="Título da etapa">
    <select id="tipo">
        <option>Identificação</option>
        <option>OSINT</option>
        <option>Patrimonial</option>
        <option>Vigilância</option>
        <option>Conclusão</option>
    </select>
    <textarea id="dados" rows="5" placeholder="Dados coletados nesta etapa..."></textarea>
    <button onclick="adicionarEtapa()">➕ SALVAR ETAPA</button>
</div>
<script>
const CASO_ID = "{{ caso.id }}";
async function adicionarEtapa(){
    const t = document.getElementById('titulo').value;
    const ti = document.getElementById('tipo').value;
    const d = document.getElementById('dados').value;
    if(!t || !d){ alert('Preencha título e dados'); return; }
    const r = await fetch(`/api/caso/${CASO_ID}/etapa`,{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({titulo:t,tipo:ti,dados:d})
    });
    if((await r.json()).ok) location.reload();
}
async function mudarStatus(status){
    await fetch(`/api/caso/${CASO_ID}/status`,{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({status:status})
    });
    location.reload();
}
</script>
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
.card h2{color:#00ffcc;margin-bottom:15px}
input{width:100%;padding:12px;margin:8px 0;background:rgba(0,0,0,0.5);border:1px solid #00ffcc;border-radius:10px;color:#fff;font-size:15px}
button{background:#00ffcc;border:none;padding:12px;border-radius:10px;font-weight:bold;cursor:pointer;width:100%;font-size:15px;margin-top:8px}
.resultado-card{background:rgba(0,0,0,0.3);border-left:2px solid #00ffcc;padding:12px;margin-bottom:8px;border-radius:0 8px 8px 0}
.resultado-card a{color:#00ffcc;word-break:break-all}
.categoria-titulo{color:#ffaa44;margin:15px 0 8px;font-weight:bold}
</style>
</head>
<body>
<div class="navbar">
    <div class="logo">🔍 SPYNET OSINT</div>
    <a href="/painel" class="btn">← Painel</a>
</div>
<div class="card">
    <h2>🌐 Busca em Redes Sociais</h2>
    <input type="text" id="rede_nome" placeholder="Nome completo do investigado">
    <input type="text" id="rede_username" placeholder="Username / arroba (opcional)">
    <button onclick="buscarRedes()">🔍 BUSCAR</button>
    <div id="rede_resultados" style="margin-top:15px"></div>
</div>
<script>
async function buscarRedes(){
    const n = document.getElementById('rede_nome').value;
    const u = document.getElementById('rede_username').value;
    if(!n && !u){ alert('Digite nome ou username'); return; }
    const r = await fetch('/osint/redes',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({nome:n,username:u})
    });
    const d = await r.json();
    let h = '', cat = '';
    d.resultados.forEach(res => {
        if(cat !== res.categoria){
            h += `<div class="categoria-titulo">${res.categoria}</div>`;
            cat = res.categoria;
        }
        h += `<div class="resultado-card">
            <strong>${res.icone} ${res.titulo}</strong><br>
            <a href="${res.url}" target="_blank" rel="noopener">${res.url}</a>
        </div>`;
    });
    document.getElementById('rede_resultados').innerHTML = h;
}
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
    print("=" * 50)
    if not SISTEMA_SENHA:
        print("⚠️  ATENÇÃO: SISTEMA_SENHA não definida!")
    print(f"🔍 Investigador: {INVESTIGADOR}")
    print(f"📱 Acesse: http://0.0.0.0:{port}")
    print("=" * 50)
    app.run(host="0.0.0.0", port=port, debug=False)
