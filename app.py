from flask import Flask, render_template, render_template_string, request, redirect, url_for, session, jsonify, send_file
import os, json, secrets
from datetime import datetime
from functools import wraps

app = Flask(__name__)

app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
ADMIN_USER = os.environ.get('ADMIN_USER')
ADMIN_PASS = os.environ.get('ADMIN_PASS')

CASOS_FILE  = 'data/casos.json'
CHAVES_FILE = 'data/chaves_validas.json'
os.makedirs('data', exist_ok=True)

def carregar_casos():
    if os.path.exists(CASOS_FILE):
        with open(CASOS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def salvar_casos(casos):
    with open(CASOS_FILE, 'w', encoding='utf-8') as f:
        json.dump(casos, f, ensure_ascii=False, indent=2)

def carregar_chaves():
    if not os.path.exists(CHAVES_FILE):
        return []
    try:
        with open(CHAVES_FILE, 'r', encoding='utf-8') as f:
            conteudo = f.read().strip()
            if not conteudo:
                return []
            return json.loads(conteudo)
    except (json.JSONDecodeError, Exception):
        return []

def salvar_chaves(chaves):
    tmp = CHAVES_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(chaves, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CHAVES_FILE)

def validar_chave(chave_digitada):
    chaves = carregar_chaves()
    chave_limpa = chave_digitada.strip().upper()
    for c in chaves:
        if c['chave'].upper() == chave_limpa:
            if not c.get('ativa', True):
                return False, 'Licenca desativada. Entre em contato: contato@peterlima.com.br'
            exp = c.get('expiracao_timestamp', 0)
            if exp < datetime.now().timestamp():
                venc = c.get('expiracao', '?')
                return False, 'Licenca vencida em ' + venc + '. Renove seu plano.'
            c['ultimo_acesso'] = datetime.now().strftime('%d/%m/%Y %H:%M')
            salvar_chaves(chaves)
            return True, c
    return False, 'Chave invalida. Verifique se digitou corretamente.'

def login_obrigatorio(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def chave_obrigatoria(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('chave_validada'):
            return redirect(url_for('ativar'))
        return f(*args, **kwargs)
    return decorated

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

ATIVAR_HTML = (
    '<!DOCTYPE html>'
    '<html lang="pt-br">'
    '<head>'
    '<meta charset="UTF-8">'
    '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
    '<title>SPYNET - Ativacao de Licenca</title>'
    '<link rel="icon" type="image/png" href="/static/logo.png">'
    '<link rel="apple-touch-icon" href="/static/logo.png">'
    '<style>'
    '*{margin:0;padding:0;box-sizing:border-box}'
    'body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;'
    'background:linear-gradient(135deg,#0a0a0a,#1a1a2e,#16213e);'
    'min-height:100vh;display:flex;justify-content:center;align-items:center;padding:16px}'
    '.card{background:rgba(10,10,20,0.95);border-radius:24px;padding:40px 32px;'
    'width:100%;max-width:460px;'
    'box-shadow:0 25px 50px rgba(0,0,0,0.5),0 0 0 1px rgba(0,255,255,0.2);text-align:center}'
    'h1{color:#00ffff;font-size:26px;letter-spacing:3px;margin-bottom:6px}'
    '.sub{color:#666;font-size:12px;letter-spacing:2px;margin-bottom:30px}'
    'label{display:block;text-align:left;color:#00ffff;font-size:12px;'
    'font-weight:600;letter-spacing:1px;margin-bottom:8px}'
    'input{width:100%;padding:14px 16px;background:rgba(20,20,40,0.8);'
    'border:1px solid #333;border-radius:12px;color:#fff;font-size:16px;'
    'letter-spacing:2px;text-align:center;text-transform:uppercase;font-family:monospace}'
    'input:focus{outline:none;border-color:#00ffff;box-shadow:0 0 12px rgba(0,255,255,0.3)}'
    'input::placeholder{color:#444;font-size:14px}'
    'button{width:100%;padding:14px;margin-top:20px;'
    'background:linear-gradient(135deg,#00aaff,#0066cc);'
    'color:white;border:none;border-radius:12px;font-size:16px;'
    'font-weight:bold;cursor:pointer;letter-spacing:2px}'
    '.erro{color:#ff4444;margin-top:16px;font-size:13px;padding:10px;'
    'background:rgba(255,68,68,0.1);border-radius:8px}'
    '.suporte{margin-top:24px;color:#444;font-size:11px}'
    '.suporte a{color:#0af;text-decoration:none}'
    '</style>'
    '</head>'
    '<body>'
    '<div class="card">'
    '<img src="/static/logo.png" alt="SPYNET"'
    ' style="width:90px;height:90px;border-radius:18px;object-fit:contain;'
    'margin:0 auto 16px;box-shadow:0 0 25px rgba(0,170,255,0.4);'
    'background:#0a0a1a;padding:8px;display:block;">'
    '<h1>SPYNET</h1>'
    '<div class="sub">ATIVACAO DE LICENCA</div>'
    '<form action="/ativar" method="POST">'
    '<label>CHAVE DE ATIVACAO</label>'
    '<input type="text" name="chave"'
    ' placeholder="XXXX-XXXX-XXXX-XXXX-XXXX-XXXX"'
    ' maxlength="29" required autocomplete="off"'
    ' value="{{ chave_anterior }}">'
    '<button type="submit">ATIVAR SISTEMA</button>'
    '{% if erro %}<div class="erro">{{ erro }}</div>{% endif %}'
    '</form>'
    '<div class="suporte">'
    'Nao tem chave? <a href="mailto:contato@peterlima.com.br">contato@peterlima.com.br</a>'
    '</div>'
    '</div>'
    '</body>'
    '</html>'
)

@app.route('/ativar', methods=['GET', 'POST'])
def ativar():
    if session.get('chave_validada'):
        return redirect(url_for('login'))
    erro = None
    chave_anterior = ''
    if request.method == 'POST':
        chave_digitada = request.form.get('chave', '').strip()
        chave_anterior = chave_digitada
        ok, resultado = validar_chave(chave_digitada)
        if ok:
            session['chave_validada'] = True
            session['chave']      = resultado['chave']
            session['cliente']    = resultado.get('cliente', '')
            session['plano']      = resultado.get('tipo', '')
            session['expiracao']  = resultado.get('expiracao', '')
            return redirect(url_for('login'))
        else:
            erro = resultado
    return render_template_string(ATIVAR_HTML, erro=erro, chave_anterior=chave_anterior)

@app.route('/')
def index():
    if not session.get('chave_validada'):
        return redirect(url_for('ativar'))
    return redirect(url_for('login'))

@app.route('/login')
def login():
    if not session.get('chave_validada'):
        return redirect(url_for('ativar'))
    return render_template('login.html')

@app.route('/fazer_login', methods=['POST'])
def fazer_login():
    if not session.get('chave_validada'):
        return redirect(url_for('ativar'))
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    if not ADMIN_USER or not ADMIN_PASS:
        return render_template('login.html', erro='Sistema nao configurado.')
    if username == ADMIN_USER and password == ADMIN_PASS:
        session['usuario']    = username
        session['login_time'] = datetime.now().isoformat()
        return redirect(url_for('dashboard'))
    return render_template('login.html', erro='Usuario ou senha incorretos!')

@app.route('/dashboard')
@login_obrigatorio
@chave_obrigatoria
def dashboard():
    return render_template('dashboard.html', usuario=session['usuario'])

@app.route('/sentinel')
@login_obrigatorio
@chave_obrigatoria
def sentinel():
    return render_template('sentinel.html', usuario=session['usuario'])

@app.route('/osint')
@login_obrigatorio
@chave_obrigatoria
def osint():
    return render_template('osint.html', usuario=session['usuario'])

@app.route('/casos')
@login_obrigatorio
@chave_obrigatoria
def casos():
    return render_template('casos.html', usuario=session['usuario'])

@app.route('/sair')
def sair():
    session.clear()
    return redirect(url_for('ativar'))

@app.route('/api/casos', methods=['GET'])
@login_obrigatorio
@chave_obrigatoria
def api_listar_casos():
    return jsonify(carregar_casos())

@app.route('/api/casos', methods=['POST'])
@login_obrigatorio
@chave_obrigatoria
def api_criar_caso():
    data = request.get_json()
    if not data or not data.get('nome'):
        return jsonify({'erro': 'Nome obrigatorio'}), 400
    casos = carregar_casos()
    novo = {
        'id':           int(datetime.now().timestamp() * 1000),
        'nome':         data.get('nome', ''),
        'descricao':    data.get('descricao', 'Sem descricao'),
        'vitima':       data.get('vitima', 'Nao informada'),
        'suspeito':     data.get('suspeito', 'Nao informado'),
        'prioridade':   data.get('prioridade', 'media'),
        'status':       'em_andamento',
        'data_criacao': datetime.now().strftime('%d/%m/%Y %H:%M')
    }
    casos.insert(0, novo)
    salvar_casos(casos)
    return jsonify(novo), 201

@app.route('/api/casos/<int:caso_id>/concluir', methods=['POST'])
@login_obrigatorio
@chave_obrigatoria
def api_concluir_caso(caso_id):
    casos = carregar_casos()
    for caso in casos:
        if caso['id'] == caso_id:
            caso['status'] = 'concluido'
            salvar_casos(casos)
            return jsonify(caso)
    return jsonify({'erro': 'Caso nao encontrado'}), 404

@app.route('/api/estatisticas', methods=['GET'])
@login_obrigatorio
@chave_obrigatoria
def estatisticas():
    casos = carregar_casos()
    return jsonify({
        'total':           len(casos),
        'em_andamento':    len([c for c in casos if c['status'] == 'em_andamento']),
        'concluidos':      len([c for c in casos if c['status'] == 'concluido']),
        'prioridade_alta': len([c for c in casos if c.get('prioridade') == 'alta']),
        'sistema':         'SPYNET Intelligence',
        'versao':          '2.0',
        'status':          'online'
    })

if __name__ == '__main__':
    print("=" * 50)
    print("SPYNET SECURITY SYSTEM - ATIVADO")
    print("=" * 50)
    print("Acesse: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
