from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, jsonify
import os
import requests
import re
import urllib.parse
from datetime import datetime

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = os.environ.get('SECRET_KEY', 'spynet_secret_key_2026')

# ==============================================
# ROTA PARA ARQUIVOS ESTÁTICOS
# ==============================================
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# ==============================================
# LOGIN
# ==============================================
@app.route('/')
def login():
    return render_template('login.html')

@app.route('/fazer_login', methods=['POST'])
def fazer_login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if username == 'Spynet2026' and password == '246357@Net':
        session['usuario'] = username
        return redirect(url_for('dashboard'))
    else:
        return render_template('login.html', erro='Usuário ou senha incorretos!')

# ==============================================
# DASHBOARD
# ==============================================
@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# ==============================================
# SENTINEL MONITOR
# ==============================================
@app.route('/sentinel')
def sentinel():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('sentinel.html')

# ==============================================
# OSINT
# ==============================================
@app.route('/osint')
def osint():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('osint.html')

# ==============================================
# CASOS
# ==============================================
@app.route('/casos')
def casos_page():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('casos.html')

@app.route('/api/estatisticas', methods=['GET'])
def estatisticas():
    return jsonify({
        'total': 0,
        'em_andamento': 0,
        'concluidos': 0,
        'prioridade_alta': 0
    })

# ==============================================
# SAIR
# ==============================================
@app.route('/sair')
def sair():
    session.clear()
    return redirect(url_for('login'))

# ==============================================
# INICIAR
# ==============================================
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)