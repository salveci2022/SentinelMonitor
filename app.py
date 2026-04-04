from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, jsonify
import requests
import re
import json
from datetime import datetime
import urllib.parse

app = Flask(__name__)
app.secret_key = 'spynet_secret_key_2026'

# Banco de dados simulado
casos = []
monitoramento_ativo = False
logs = []

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

@app.route('/api/monitor/status', methods=['GET'])
def monitor_status():
    global monitoramento_ativo
    return jsonify({'ativo': monitoramento_ativo})

@app.route('/api/monitor/iniciar', methods=['POST'])
def monitor_iniciar():
    global monitoramento_ativo, logs
    monitoramento_ativo = True
    logs.append({'time': datetime.now().strftime('%H:%M:%S'), 'msg': '🟢 Monitoramento iniciado'})
    return jsonify({'status': 'iniciado'})

@app.route('/api/monitor/parar', methods=['POST'])
def monitor_parar():
    global monitoramento_ativo, logs
    monitoramento_ativo = False
    logs.append({'time': datetime.now().strftime('%H:%M:%S'), 'msg': '🔴 Monitoramento parado'})
    return jsonify({'status': 'parado'})

@app.route('/api/monitor/limpar', methods=['POST'])
def monitor_limpar():
    global logs
    logs = []
    return jsonify({'status': 'limpo'})

@app.route('/api/monitor/logs', methods=['GET'])
def get_logs():
    return jsonify(logs[-20:])

# ==============================================
# OSINT REAL - BUSCA NA INTERNET
# ==============================================
@app.route('/osint')
def osint():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('osint.html')

@app.route('/api/osint/buscar', methods=['POST'])
def osint_buscar():
    data = request.get_json()
    query = data.get('query', '')
    tipo = data.get('tipo', 'tudo')
    
    resultados = {
        'google': [],
        'redes_sociais': [],
        'documentos': [],
        'alertas': [],
        'ia_analise': ''
    }
    
    # 1. BUSCA NO GOOGLE (via scraping simulado com DuckDuckGo)
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # Extrair resultados básicos
            links = re.findall(r'https?://[^\s"\']+', response.text)
            resultados['google'] = list(set(links[:5]))  # primeiros 5 links únicos
    except:
        resultados['google'] = ['Erro ao conectar com mecanismo de busca']
    
    # 2. VERIFICAÇÃO DE REDES SOCIAIS
    redes = {
        'Instagram': f'https://www.instagram.com/{query.replace(" ", "")}',
        'Facebook': f'https://www.facebook.com/search/top?q={urllib.parse.quote(query)}',
        'Twitter/X': f'https://twitter.com/search?q={urllib.parse.quote(query)}',
        'LinkedIn': f'https://www.linkedin.com/search/results/all/?keywords={urllib.parse.quote(query)}',
        'TikTok': f'https://www.tiktok.com/search?q={urllib.parse.quote(query)}',
        'YouTube': f'https://www.youtube.com/results?search_query={urllib.parse.quote(query)}'
    }
    
    for rede, url in redes.items():
        resultados['redes_sociais'].append({
            'nome': rede,
            'url': url,
            'encontrado': 'Link para busca'
        })
    
    # 3. BUSCA EM DOCUMENTOS PÚBLICOS
    documentos = [
        {'fonte': 'Google Dorks', 'url': f'https://www.google.com/search?q=filetype:pdf+"{urllib.parse.quote(query)}"'},
        {'fonte': 'Arquivo Público', 'url': f'https://archive.org/search?query={urllib.parse.quote(query)}'},
        {'fonte': 'Processos Judiciais', 'url': f'https://www.jusbrasil.com.br/busca?q={urllib.parse.quote(query)}'},
        {'fonte': 'Diário Oficial', 'url': f'https://pesquisa.in.gov.br/imprensa/jsp/visualiza/index.jsp?q={urllib.parse.quote(query)}'}
    ]
    resultados['documentos'] = documentos
    
    # 4. ALERTAS DE SEGURANÇA
    resultados['alertas'] = [
        {'nivel': '⚠️ Info', 'descricao': f'Realizar verificação cruzada do termo: {query}'},
        {'nivel': '🔍 Dica', 'descricao': 'Utilize aspas duplas para busca exata ("texto")'},
        {'nivel': '📌 Sugestão', 'descricao': 'Verifique também em fontes locais e regionais'}
    ]
    
    # 5. ANÁLISE DA IA
    if '@' in query:
        resultados['ia_analise'] = f'E-mail detectado: {query}. Recomenda-se verificar em haveibeenpwned.com e buscar associações em redes sociais.'
    elif re.match(r'^[0-9]{11}$', query):
        resultados['ia_analise'] = f'CPF detectado: {query[:3]}.{query[3:6]}.{query[6:9]}-{query[9:]} - Verificar em consultas públicas.'
    elif re.match(r'^[0-9]{10,11}$', query):
        resultados['ia_analise'] = f'Telefone detectado: {query}. Verificar em WhatsApp, Telegram e redes sociais.'
    else:
        resultados['ia_analise'] = f'Analisando "{query}" - Busque também por variações do nome, apelidos e combinações com cidades.'
    
    return jsonify(resultados)

# ==============================================
# CASOS
# ==============================================
@app.route('/casos')
def casos_page():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('casos.html')

@app.route('/api/casos/listar', methods=['GET'])
def listar_casos():
    return jsonify(casos)

@app.route('/api/casos/criar', methods=['POST'])
def criar_caso():
    data = request.get_json()
    novo_caso = {
        'id': len(casos) + 1,
        'nome': data.get('nome'),
        'descricao': data.get('descricao'),
        'vítima': data.get('vitima'),
        'agressor': data.get('agressor'),
        'status': 'em_andamento',
        'data_criacao': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'prioridade': data.get('prioridade', 'media'),
        'tipo': data.get('tipo', 'violencia')
    }
    casos.append(novo_caso)
    return jsonify(novo_caso)

@app.route('/api/casos/atualizar/<int:id>', methods=['PUT'])
def atualizar_caso(id):
    data = request.get_json()
    for caso in casos:
        if caso['id'] == id:
            caso['status'] = data.get('status', caso['status'])
            return jsonify(caso)
    return jsonify({'erro': 'Caso não encontrado'}), 404

@app.route('/api/estatisticas', methods=['GET'])
def estatisticas():
    total = len(casos)
    em_andamento = len([c for c in casos if c['status'] == 'em_andamento'])
    concluidos = len([c for c in casos if c['status'] == 'concluido'])
    prioridade_alta = len([c for c in casos if c.get('prioridade') == 'alta'])
    
    return jsonify({
        'total': total,
        'em_andamento': em_andamento,
        'concluidos': concluidos,
        'prioridade_alta': prioridade_alta
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
    app.run(debug=True, host='0.0.0.0', port=5000)