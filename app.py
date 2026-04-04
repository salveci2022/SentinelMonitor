from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, jsonify
import os
import json
import hashlib
import secrets
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# ==============================================
# SEGURANÇA
# ==============================================
def login_obrigatorio(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# ==============================================
# ROTAS PRINCIPAIS
# ==============================================
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/fazer_login', methods=['POST'])
def fazer_login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    # CREDENCIAIS - Você pode mudar aqui
    if username == 'Spynet2026' and password == '246357@Net':
        session['usuario'] = username
        session['login_time'] = datetime.now().isoformat()
        return redirect(url_for('dashboard'))
    else:
        return render_template('login.html', erro='Usuário ou senha incorretos!')

@app.route('/dashboard')
@login_obrigatorio
def dashboard():
    return render_template('dashboard.html')

@app.route('/sentinel')
@login_obrigatorio
def sentinel():
    return render_template('sentinel.html')

@app.route('/osint')
@login_obrigatorio
def osint():
    return render_template('osint.html')

@app.route('/casos')
@login_obrigatorio
def casos():
    return render_template('casos.html')

@app.route('/sair')
def sair():
    session.clear()
    return redirect(url_for('login'))

# ==============================================
# API - ESTATÍSTICAS
# ==============================================
@app.route('/api/estatisticas', methods=['GET'])
def estatisticas():
    return jsonify({
        'total': 0,
        'em_andamento': 0,
        'concluidos': 0,
        'prioridade_alta': 0,
        'sistema': 'SPYNET Intelligence',
        'versao': '2.0',
        'status': 'online'
    })

# ==============================================
# INICIAR SERVIDOR
# ==============================================
if __name__ == '__main__':
    print("="*50)
    print("🔐 SPYNET SECURITY SYSTEM - ATIVADO")
    print("="*50)
    print(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"🔑 Chave: {app.secret_key[:20]}...")
    print(f"🌐 Acesse: http://localhost:5000")
    print("="*50)
    app.run(debug=False, host='0.0.0.0', port=5000)