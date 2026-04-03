"""
SPYNET OSINT ULTIMATE — SISTEMA COMPLETO PARA RENDER
Funcionalidades: OSINT + Gestão de Casos + PDF + Monitoramento (Painel)
"""

from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for, send_file
from datetime import datetime, timezone, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdf_canvas
from functools import wraps
import json, os, requests, hashlib, uuid, re

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
# FUNÇÕES OSINT COMPLETAS
# ============================================

def buscar_redes_sociais(nome, username=None, email=None, telefone=None):
    resultados = []
    
    # Instagram
    if username:
        resultados.append({"categoria": "📷 INSTAGRAM", "titulo": "Perfil", "url": f"https://www.instagram.com/{username}", "icone": "📷"})
    if nome:
        resultados.append({"categoria": "📷 INSTAGRAM", "titulo": "Busca por nome", "url": f"https://www.instagram.com/explore/tags/{nome.replace(' ', '')}", "icone": "📷"})
    
    # Facebook
    if nome:
        resultados.append({"categoria": "📘 FACEBOOK", "titulo": "Busca por nome", "url": f"https://www.facebook.com/search/top?q={nome.replace(' ', '%20')}", "icone": "📘"})
    if email:
        resultados.append({"categoria": "📘 FACEBOOK", "titulo": "Busca por email", "url": f"https://www.facebook.com/search/top?q={email}", "icone": "📘"})
    
    # Twitter/X
    if username:
        resultados.append({"categoria": "🐦 TWITTER/X", "titulo": "Perfil", "url": f"https://twitter.com/{username}", "icone": "🐦"})
    if nome:
        resultados.append({"categoria": "🐦 TWITTER/X", "titulo": "Busca por nome", "url": f"https://twitter.com/search?q={nome.replace(' ', '%20')}", "icone": "🐦"})
    
    # LinkedIn
    if nome:
        resultados.append({"categoria": "💼 LINKEDIN", "titulo": "Busca por nome", "url": f"https://www.linkedin.com/search/results/people/?keywords={nome.replace(' ', '%20')}", "icone": "💼"})
    
    # TikTok
    if username:
        resultados.append({"categoria": "🎵 TIKTOK", "titulo": "Perfil", "url": f"https://www.tiktok.com/@{username}", "icone": "🎵"})
    if nome:
        resultados.append({"categoria": "🎵 TIKTOK", "titulo": "Busca por nome", "url": f"https://www.tiktok.com/search?q={nome.replace(' ', '%20')}", "icone": "🎵"})
    
    # YouTube
    if nome:
        resultados.append({"categoria": "📺 YOUTUBE", "titulo": "Busca por nome", "url": f"https://www.youtube.com/results?search_query={nome.replace(' ', '+')}", "icone": "📺"})
    
    # GitHub
    if username:
        resultados.append({"categoria": "💻 GITHUB", "titulo": "Perfil", "url": f"https://github.com/{username}", "icone": "💻"})
    
    # WhatsApp
    if telefone:
        telefone_limpo = re.sub(r'\D', '', telefone)
        resultados.append({"categoria": "💬 WHATSAPP", "titulo": "Abrir conversa", "url": f"https://wa.me/55{telefone_limpo}", "icone": "💬"})
    
    # Telegram
    if telefone:
        telefone_limpo = re.sub(r'\D', '', telefone)
        resultados.append({"categoria": "✈️ TELEGRAM", "titulo": "Verificar perfil", "url": f"https://t.me/+55{telefone_limpo}", "icone": "✈️"})
    
    # Gravatar (email)
    if email:
        resultados.append({"categoria": "🖼️ GRAVATAR", "titulo": "Avatar", "url": f"https://pt.gravatar.com/{email}", "icone": "🖼️"})
    
    return resultados

def buscar_bens_patrimoniais(cpf_cnpj):
    resultados = []
    if cpf_cnpj:
        resultados.append({"categoria": "🏠 IMÓVEIS", "titulo": "Buscar Imóveis", "url": f"https://www.google.com/search?q=registro+de+imoveis+cpf+{cpf_cnpj}", "icone": "🏠"})
        resultados.append({"categoria": "🚗 VEÍCULOS", "titulo": "Buscar Veículos", "url": f"https://www.google.com/search?q=consulta+veiculo+renavam+por+cpf+{cpf_cnpj}", "icone": "🚗"})
        if len(cpf_cnpj) == 14:
            resultados.append({"categoria": "🏢 EMPRESAS", "titulo": "Consulta CNPJ", "url": f"https://www.receitaws.com.br/v1/cnpj/{cpf_cnpj}", "icone": "🏢"})
        resultados.append({"categoria": "👥 PARTICIPAÇÕES", "titulo": "Sócios", "url": f"https://www.google.com/search?q=socio+administrador+{cpf_cnpj}", "icone": "👥"})
    return resultados

def buscar_localizacao(endereco, cep=None, cidade=None):
    query = endereco if endereco else cep
    if cidade:
        query = f"{query} {cidade}"
    return {
        "maps_url": f"https://www.google.com/maps/search/{query.replace(' ', '+')}",
        "waze_url": f"https://www.waze.com/live-map/directions?to=search.{query.replace(' ', '+')}"
    }

def buscar_credito(cpf):
    resultados = []
    if cpf:
        resultados.append({"categoria": "📊 SCORE", "titulo": "Consultar Score", "url": "https://www.serasa.com.br/consulta-cpf/", "icone": "📊"})
        resultados.append({"categoria": "🚫 RESTRIÇÕES", "titulo": "Restrições Bancárias", "url": "https://www.serasa.com.br/consulta-cpf/restricoes/", "icone": "🚫"})
        resultados.append({"categoria": "📋 PROTESTOS", "titulo": "Protestos", "url": f"https://www.google.com/search?q=protesto+cartorio+cpf+{cpf}", "icone": "📋"})
        resultados.append({"categoria": "💰 RENDA", "titulo": "Renda Presumida", "url": f"https://www.google.com/search?q=renda+presumida+cpf+{cpf}", "icone": "💰"})
    return resultados

def buscar_dados_vazados(email):
    resultados = []
    if email:
        resultados.append({"categoria": "🔓 HAVE I BEEN PWNED", "titulo": "Verificar vazamentos", "url": f"https://haveibeenpwned.com/account/{email}", "icone": "🔓"})
        resultados.append({"categoria": "🔎 LEAKCHECK", "titulo": "Verificar vazamentos", "url": f"https://leakcheck.io/?q={email}", "icone": "🔎"})
        resultados.append({"categoria": "📂 BREACH DIRECTORY", "titulo": "Verificar vazamentos", "url": f"https://breachdirectory.org/#{email}", "icone": "📂"})
        resultados.append({"categoria": "🔍 GOOGLE", "titulo": "Busca geral", "url": f"https://www.google.com/search?q=%22{email}%22+breach+OR+vazamento", "icone": "🔍"})
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

# ============================================
# ROTAS OSINT
# ============================================

@app.route("/osint/redes", methods=["POST"])
@login_required
def osint_redes():
    data = request.get_json() or {}
    nome = data.get("nome", "")
    username = data.get("username", "")
    email = data.get("email", "")
    telefone = data.get("telefone", "")
    resultados = buscar_redes_sociais(nome, username, email, telefone)
    return jsonify({"resultados": resultados})

@app.route("/osint/bens", methods=["POST"])
@login_required
def osint_bens():
    data = request.get_json() or {}
    cpf_cnpj = data.get("cpf_cnpj", "")
    resultados = buscar_bens_patrimoniais(cpf_cnpj)
    return jsonify({"resultados": resultados})

@app.route("/osint/localizacao", methods=["POST"])
@login_required
def osint_localizacao():
    data = request.get_json() or {}
    endereco = data.get("endereco", "")
    cep = data.get("cep", "")
    cidade = data.get("cidade", "")
    localizacao = buscar_localizacao(endereco, cep, cidade)
    return jsonify(localizacao)

@app.route("/osint/credito", methods=["POST"])
@login_required
def osint_credito():
    data = request.get_json() or {}
    cpf = data.get("cpf", "")
    resultados = buscar_credito(cpf)
    return jsonify({"resultados": resultados})

@app.route("/osint/vazamentos", methods=["POST"])
@login_required
def osint_vazamentos():
    data = request.get_json() or {}
    email = data.get("email", "")
    resultados = buscar_dados_vazados(email)
    return jsonify({"resultados": resultados})

@app.route("/osint")
@login_required
def osint_page():
    return render_template_string(OSINT_HTML)

@app.route("/osint/pesquisar")
@login_required
def osint_pesquisar():
    return render_template_string(OSINT_HTML)

# ============================================
# ROTAS DOS CASOS
# ============================================

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

# ============================================
# ROTAS DO SENTINEL (MONITORAMENTO - PAINEL)
# ============================================

@app.route("/sentinel")
@login_required
def sentinel_page():
    return render_template_string(SENTINEL_HTML)

# ============================================
# PDF
# ============================================

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
    c.setFont("Helvetica", 10)
    c.drawString(50, H - 80, f"ID: {caso['id']}")
    c.drawString(50, H - 100, f"Emitido: {now_br()}")
    c.drawString(50, H - 130, f"Investigado: {caso.get('investigado', '—')}")
    c.drawString(50, H - 150, f"Cliente: {caso.get('cliente', '—')}")
    c.drawString(50, H - 170, f"Status: {caso.get('status', '—')}")
    c.drawString(50, H - 200, f"Objetivo: {caso.get('objetivo', '—')}")
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, H - 240, "ETAPAS REALIZADAS")
    
    y = H - 270
    c.setFont("Helvetica", 9)
    for e in caso.get("etapas", []):
        if y < 50:
            c.showPage()
            y = H - 50
        c.drawString(50, y, f"ETAPA {e['num']}: {e['titulo']} - {e['ts']}")
        y -= 15
        for linha in e.get("dados", "").split("\n"):
            if linha.strip():
                if y < 50:
                    c.showPage()
                    y = H - 50
                c.drawString(65, y, linha.strip()[:80])
                y -= 12
        y -= 8
    
    c.save()
    buffer.seek(0)
    
    return send_file(buffer, as_attachment=True, download_name=f"relatorio_{caso['id']}.pdf", mimetype="application/pdf")

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
        body{background:linear-gradient(135deg,#0a0a2a,#1a1a3a);font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh}
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
<div><a href="/osint" class="btn">🔎 OSINT</a><a href="/sentinel" class="btn">🛡️ MONITOR</a><a href="/novo_caso" class="btn">➕ NOVO CASO</a><button class="btn btn-red" onclick="limparTodosCasos()">🗑️ LIMPAR</button><a href="/logout" class="btn btn-red">🚪 SAIR</a></div></div>
<div class="stats"><div class="stat-card"><div class="stat-number">{{ total }}</div><div>TOTAL CASOS</div></div><div class="stat-card"><div class="stat-number">{{ ativos }}</div><div>EM ANDAMENTO</div></div><div class="stat-card"><div class="stat-number">{{ concl }}</div><div>CONCLUÍDOS</div></div></div>
<h3>📁 CASOS INVESTIGATIVOS</h3>
{% for caso in casos %}
<div class="caso-card"><div><strong>{{ caso.id }}</strong><br><small>{{ caso.investigado }} • {{ caso.status }}</small></div><div><a href="/caso/{{ caso.id }}" class="btn-pequeno">👁️ VER</a><a href="/relatorio/{{ caso.id }}.pdf" class="btn-pequeno btn-pdf">📄 PDF</a></div></div>
{% else %}<p>NENHUM CASO REGISTRADO. <a href="/novo_caso" style="color:#00ffcc">CRIAR PRIMEIRO CASO →</a></p>{% endfor %}
<script>function limparTodosCasos(){if(confirm('⚠️ REMOVER TODOS OS CASOS?')){fetch('/api/limpar_casos',{method:'POST'}).then(()=>location.reload());}}</script>
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
<body><div class="navbar"><div class="logo">🔍 SPYNET</div><a href="/painel" class="btn">← PAINEL</a></div>
<div class="card"><h2>➕ NOVO CASO</h2>
<form method="POST">
<select name="tipo" required><option value="">TIPO DE CASO...</option><option>Investigação de pessoa física</option><option>Investigação de pessoa jurídica</option><option>Localização patrimonial</option><option>Análise de crédito</option><option>Infidelidade conjugal</option><option>Due Diligence empresarial</option></select>
<input type="text" name="cliente" placeholder="CLIENTE (CONTRATANTE)" required>
<input type="text" name="investigado" placeholder="INVESTIGADO / ALVO" required>
<textarea name="objetivo" rows="3" placeholder="OBJETIVO DA INVESTIGAÇÃO" required></textarea>
<textarea name="notas" rows="3" placeholder="NOTAS INICIAIS (OPCIONAL)"></textarea>
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
<body><div class="navbar"><div class="logo">🔍 SPYNET</div><a href="/painel" class="btn">← PAINEL</a></div>
<div class="card"><h2>{{ caso.investigado }}</h2><p><span class="badge">{{ caso.id }}</span> • {{ caso.criado_em }}</p><p><strong>CLIENTE:</strong> {{ caso.cliente }}</p><p><strong>TIPO:</strong> {{ caso.tipo }}</p><p><strong>STATUS:</strong> <span class="status status-{{ 'andamento' if caso.status == 'Em andamento' else 'concluido' }}">{{ caso.status }}</span></p><p><strong>OBJETIVO:</strong> {{ caso.objetivo }}</p>{% if caso.notas %}<p><strong>NOTAS:</strong> {{ caso.notas }}</p>{% endif %}</div>
<div class="card"><h3>📋 ETAPAS</h3>{% for e in caso.etapas %}<div class="etapa-card"><strong>ETAPA {{ e.num }}: {{ e.titulo }}</strong><div><span class="badge">{{ e.tipo }}</span> • {{ e.ts }}</div><p style="margin-top:10px">{{ e.dados }}</p></div>{% else %}<p>NENHUMA ETAPA REGISTRADA.</p>{% endfor %}</div>
<div class="card"><h3>➕ ADICIONAR ETAPA</h3><input type="text" id="titulo" placeholder="TÍTULO"><select id="tipo"><option>Identificação Cadastral</option><option>Análise Digital (OSINT)</option><option>Estrutura Patrimonial</option><option>Vínculos e Relacionamentos</option><option>Conclusão Investigativa</option></select><textarea id="dados" rows="5" placeholder="DADOS E ANÁLISE..."></textarea><button onclick="adicionarEtapa()">➕ SALVAR</button></div>
<script>const CASO_ID = "{{ caso.id }}";async function adicionarEtapa(){const t=document.getElementById('titulo').value,ti=document.getElementById('tipo').value,d=document.getElementById('dados').value;if(!t||!d){alert('PREENCHE TÍTULO E DADOS');return}const r=await fetch(`/api/caso/${CASO_ID}/etapa`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({titulo:t,tipo:ti,dados:d})});if((await r.json()).ok)location.reload()}</script>
</body>
</html>
'''

OSINT_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SPYNET — OSINT COMPLETO</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);color:#fff;font-family:Arial;padding:20px}
        .navbar{background:rgba(0,0,0,0.8);padding:15px;border-radius:15px;display:flex;justify-content:space-between;margin-bottom:20px}
        .logo{font-size:24px;font-weight:bold;color:#00ffcc}
        .btn{background:#00ffcc;border:none;padding:8px 18px;border-radius:25px;cursor:pointer;text-decoration:none;color:#000}
        .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(400px,1fr));gap:20px}
        .card{background:rgba(255,255,255,0.1);border-radius:20px;padding:25px}
        .card h2{color:#00ffcc;margin-bottom:15px;font-size:16px}
        input{width:100%;padding:12px;margin:10px 0;background:rgba(0,0,0,0.5);border:1px solid #00ffcc;border-radius:10px;color:#fff}
        button{background:#00ffcc;border:none;padding:12px;border-radius:10px;font-weight:bold;cursor:pointer;width:100%;margin-top:10px}
        .resultado-card{background:rgba(0,0,0,0.3);border-left:2px solid #00ffcc;padding:12px;margin-bottom:8px}
        .resultado-card a{color:#00ffcc;text-decoration:none}
        .categoria-titulo{color:#ffaa44;margin:15px 0 8px;font-size:12px}
    </style>
</head>
<body>
<div class="navbar"><div class="logo">🔍 SPYNET OSINT</div><div><a href="/painel" class="btn">← PAINEL</a></div></div>
<div class="grid">
    <div class="card"><h2>🌐 REDES SOCIAIS</h2><input type="text" id="rede_nome" placeholder="Nome completo"><input type="text" id="rede_username" placeholder="Username"><input type="email" id="rede_email" placeholder="Email"><input type="tel" id="rede_telefone" placeholder="Telefone"><button onclick="buscarRedes()">🔍 BUSCAR REDES</button><div id="rede_resultados"></div></div>
    <div class="card"><h2>🏠 BENS PATRIMONIAIS</h2><input type="text" id="bens_cpf" placeholder="CPF ou CNPJ"><button onclick="buscarBens()">🔍 BUSCAR BENS</button><div id="bens_resultados"></div></div>
    <div class="card"><h2>📍 LOCALIZAÇÃO</h2><input type="text" id="local_endereco" placeholder="Endereço"><input type="text" id="local_cep" placeholder="CEP"><input type="text" id="local_cidade" placeholder="Cidade"><button onclick="buscarLocalizacao()">🗺️ LOCALIZAR</button><div id="local_resultados"></div></div>
    <div class="card"><h2>📊 ANÁLISE DE CRÉDITO</h2><input type="text" id="credito_cpf" placeholder="CPF"><button onclick="buscarCredito()">📊 ANALISAR</button><div id="credito_resultados"></div></div>
    <div class="card"><h2>🔓 DADOS VAZADOS</h2><input type="email" id="vazado_email" placeholder="Email"><button onclick="buscarVazados()">🔍 VERIFICAR</button><div id="vazado_resultados"></div></div>
</div>
<script>
async function buscarRedes(){const n=document.getElementById('rede_nome').value,u=document.getElementById('rede_username').value,e=document.getElementById('rede_email').value,t=document.getElementById('rede_telefone').value;if(!n&&!u&&!e&&!t){alert('Digite nome, username, email ou telefone');return;}const r=await fetch('/osint/redes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nome:n,username:u,email:e,telefone:t})});const d=await r.json();let h='',cat='';d.resultados.forEach(r=>{if(cat!==r.categoria){h+=`<div class="categoria-titulo">${r.categoria}</div>`;cat=r.categoria;}h+=`<div class="resultado-card"><strong>${r.titulo}</strong><br><a href="${r.url}" target="_blank">${r.url}</a></div>`;});document.getElementById('rede_resultados').innerHTML=h;}
async function buscarBens(){const c=document.getElementById('bens_cpf').value;if(!c){alert('Digite CPF ou CNPJ');return;}const r=await fetch('/osint/bens',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cpf_cnpj:c})});const d=await r.json();let h='',cat='';d.resultados.forEach(r=>{if(cat!==r.categoria){h+=`<div class="categoria-titulo">${r.categoria}</div>`;cat=r.categoria;}h+=`<div class="resultado-card"><strong>${r.titulo}</strong><br><a href="${r.url}" target="_blank">${r.url}</a></div>`;});document.getElementById('bens_resultados').innerHTML=h;}
async function buscarLocalizacao(){const e=document.getElementById('local_endereco').value,c=document.getElementById('local_cep').value,ci=document.getElementById('local_cidade').value;if(!e&&!c){alert('Digite endereço ou CEP');return;}const r=await fetch('/osint/localizacao',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({endereco:e,cep:c,cidade:ci})});const d=await r.json();let h=`<div class="resultado-card"><strong>🗺️ GOOGLE MAPS</strong><br><a href="${d.maps_url}" target="_blank">Abrir no Google Maps</a></div><div class="resultado-card"><strong>🚗 WAZE</strong><br><a href="${d.waze_url}" target="_blank">Abrir no Waze</a></div>`;document.getElementById('local_resultados').innerHTML=h;}
async function buscarCredito(){const c=document.getElementById('credito_cpf').value;if(!c){alert('Digite CPF');return;}const r=await fetch('/osint/credito',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cpf:c})});const d=await r.json();let h='',cat='';d.resultados.forEach(r=>{if(cat!==r.categoria){h+=`<div class="categoria-titulo">${r.categoria}</div>`;cat=r.categoria;}h+=`<div class="resultado-card"><strong>${r.titulo}</strong><br><a href="${r.url}" target="_blank">${r.url}</a></div>`;});document.getElementById('credito_resultados').innerHTML=h;}
async function buscarVazados(){const e=document.getElementById('vazado_email').value;if(!e){alert('Digite email');return;}const r=await fetch('/osint/vazamentos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:e})});const d=await r.json();let h='',cat='';d.resultados.forEach(r=>{if(cat!==r.categoria){h+=`<div class="categoria-titulo">${r.categoria}</div>`;cat=r.categoria;}h+=`<div class="resultado-card"><strong>${r.titulo}</strong><br><a href="${r.url}" target="_blank">${r.url}</a></div>`;});document.getElementById('vazado_resultados').innerHTML=h;}
</script>
</body>
</html>
'''

SENTINEL_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SPYNET — MONITOR</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);color:#fff;font-family:Arial;padding:20px}
        .navbar{background:rgba(0,0,0,0.8);padding:15px;border-radius:15px;display:flex;justify-content:space-between;margin-bottom:20px}
        .logo{font-size:24px;font-weight:bold;color:#00ffcc}
        .btn{background:#00ffcc;border:none;padding:8px 18px;border-radius:25px;cursor:pointer;text-decoration:none;color:#000}
        .card{background:rgba(255,255,255,0.1);border-radius:20px;padding:25px;text-align:center}
        .info-icon{font-size:48px;margin-bottom:15px}
        .info-text{color:#8899aa;margin-top:10px;font-size:12px}
        .badge{background:#ffaa44;color:#000;padding:5px 12px;border-radius:20px;font-size:12px;display:inline-block}
    </style>
</head>
<body>
<div class="navbar"><div class="logo">🛡️ SPYNET MONITOR</div><div><a href="/painel" class="btn">← PAINEL</a></div></div>
<div class="card">
    <div class="info-icon">🖥️</div>
    <h2>MONITORAMENTO EM TEMPO REAL</h2>
    <div class="badge">⚠️ FUNCIONA APENAS NO COMPUTADOR</div>
    <div class="info-text">
        <p>O monitoramento em tempo real (screenshot, áudio e keylogger) só funciona no computador onde o programa está instalado.</p>
        <p style="margin-top:15px">Para utilizar estas funcionalidades, baixe o programa no seu computador.</p>
        <p style="margin-top:15px">Acesse o link para download ou entre em contato com o suporte.</p>
    </div>
</div>
</body>
</html>
'''

# ============================================
# REQUIREMENTS.TXT
# ============================================

REQUIREMENTS = """
flask>=3.0.0
reportlab>=4.0.0
requests>=2.31.0
"""

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 50)
    print("🔍 SPYNET OSINT ULTIMATE - SISTEMA COMPLETO")
    print("=" * 50)
    print(f"🔐 Senha de acesso: {SISTEMA_SENHA}")
    print(f"📱 Acesse: http://0.0.0.0:{port}")
    print("=" * 50)
    print("✅ FUNCIONALIDADES:")
    print("   • 🔎 OSINT COMPLETO (Redes, Bens, Localização, Crédito, Vazamentos)")
    print("   • 📁 Gestão de Casos Investigativos")
    print("   • 📄 Exportação de Relatórios PDF")
    print("   • 🛡️ Painel de Monitoramento")
    print("=" * 50)
    app.run(host="0.0.0.0", port=port, debug=False)