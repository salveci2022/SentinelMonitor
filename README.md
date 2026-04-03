```markdown
<div align="center">

# 🕵️ SPYNET OSINT ULTIMATE

### *Sistema Profissional de Investigação Digital e Monitoramento*

[![Version](https://img.shields.io/badge/version-2.0-blue.svg)](https://github.com/salveci2022/SentinelMonitor)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-yellow.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/flask-3.0-red.svg)](https://flask.palletsprojects.com)
[![Render](https://img.shields.io/badge/deploy-Render-purple.svg)](https://render.com)

</div>

---

## 📋 ÍNDICE

- [Sobre o Sistema](#sobre-o-sistema)
- [Funcionalidades](#funcionalidades)
- [Demonstração](#demonstração)
- [Para Quem é este Sistema](#para-quem-é-este-sistema)
- [Arquitetura](#arquitetura)
- [Instalação](#instalação)
- [Como Usar](#como-usar)
- [Comandos Telegram](#comandos-telegram)
- [Planos e Preços](#planos-e-preços)
- [Perguntas Frequentes](#perguntas-frequentes)
- [Suporte](#suporte)
- [Licença](#licença)

---

## 🎯 SOBRE O SISTEMA

**SPYNET OSINT Ultimate** é um sistema profissional de investigação digital que reúne em um único lugar todas as ferramentas necessárias para:

- 🔎 **Investigações OSINT** (Open Source Intelligence)
- 🛡️ **Monitoramento em Tempo Real** (screenshot, áudio, keylogger)
- 📁 **Gestão de Casos Investigativos**
- 📄 **Geração de Relatórios Profissionais em PDF**
- 🤖 **Alertas Automáticos via Telegram**

Desenvolvido para **detetives particulares, advogados, empresas de segurança, investigadores e profissionais que precisam de informações precisas e rápidas.**

---

## ⚡ FUNCIONALIDADES

### 🔎 OSINT COMPLETO

| Módulo | Funcionalidades |
|--------|-----------------|
| **🌐 Redes Sociais** | Instagram, Facebook, Twitter, LinkedIn, TikTok, YouTube, GitHub |
| **🏠 Bens Patrimoniais** | Imóveis, Veículos, Empresas, Participações Societárias |
| **📍 Localização** | Endereço por CPF, Telefones, E-mails, Google Maps, Waze |
| **📊 Análise de Crédito** | Score Serasa/SPC, Restrições Bancárias, Protestos, Capacidade de Pagamento |
| **🔓 Dados Vazados** | HaveIBeenPwned, LeakCheck, BreachDirectory, DeHashed |

### 🛡️ MONITORAMENTO EM TEMPO REAL

| Funcionalidade | Detalhe |
|----------------|---------|
| **📸 Screenshot** | Captura automática a cada 5 segundos |
| **🎤 Áudio Ambiente** | Gravação com volume máximo a cada 10 segundos |
| **⌨️ Keylogger** | Captura palavras completas (não letras soltas) |
| **🤖 Telegram** | Envio automático de todas as capturas |

### 📁 GESTÃO DE CASOS

| Funcionalidade | Detalhe |
|----------------|---------|
| **📋 Criar Casos** | Registre novas investigações |
| **📝 Etapas** | Documente cada fase da investigação |
| **📊 Status** | Acompanhamento (Em andamento / Concluído) |
| **🗑️ Limpar Dados** | Remova casos antigos |
| **📄 Exportar PDF** | Relatório profissional pronto para processos |

### 🎨 DESIGN PROFISSIONAL

- ✨ Interface estilo FBI / Agência de Inteligência
- 🌙 Dark Mode para trabalho noturno
- 📱 Responsivo (funciona no celular)
- ⚡ Animações e efeitos visuais

---

## 🖼️ DEMONSTRAÇÃO

### Tela de Login
<div align="center">
<img src="https://via.placeholder.com/800x400/0a0e1a/00ffcc?text=SPYNET+-+Tela+de+Login" alt="Tela de Login" width="80%">
</div>

### Painel Principal
<div align="center">
<img src="https://via.placeholder.com/800x400/0f0c29/00ffcc?text=SPYNET+-+Painel+de+Comando" alt="Painel Principal" width="80%">
</div>

### OSINT Tools
<div align="center">
<img src="https://via.placeholder.com/800x400/302b63/00ffcc?text=SPYNET+-+OSINT+Tools" alt="OSINT Tools" width="80%">
</div>

### Relatório PDF
<div align="center">
<img src="https://via.placeholder.com/800x400/1a1a2e/00ffcc?text=SPYNET+-+Relatório+PDF" alt="Relatório PDF" width="80%">
</div>

---

## 👥 PARA QUEM É ESTE SISTEMA

| Profissional | Benefício |
|--------------|-----------|
| **🕵️ Detetive Particular** | Agiliza investigações em 95%, encontra pessoas em minutos |
| **⚖️ Advogado** | Localiza bens para penhora, encontra devedores |
| **🏢 Escritório de Cobrança** | Localiza devedores e bens para execução |
| **💳 Financeira** | Analisa crédito e risco de clientes |
| **👔 Recursos Humanos** | Verifica antecedentes de candidatos |
| **📰 Jornalista** | Pesquisa fontes e informações |
| **🛡️ Segurança Patrimonial** | Monitora funcionários e investiga fraudes |
| **👨‍👩‍👧 Pais** | Monitora atividades dos filhos na internet |

---

## 🏗️ ARQUITETURA

```
┌─────────────────────────────────────────────────────────────┐
│                      SPYNET OSINT                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐    ┌─────────────────┐               │
│  │   SERVIDOR      │    │   CLIENTE       │               │
│  │   (RENDER)      │◄───│   LOCAL         │               │
│  │                 │    │                 │               │
│  │ • Painel Web    │    │ • Screenshot    │               │
│  │ • OSINT         │    │ • Áudio         │               │
│  │ • Casos         │    │ • Keylogger     │               │
│  │ • PDF           │    │ • Envio para    │               │
│  │                 │    │   servidor      │               │
│  └─────────────────┘    └─────────────────┘               │
│           ▲                        ▲                       │
│           │                        │                       │
│           ▼                        ▼                       │
│  ┌─────────────────┐    ┌─────────────────┐               │
│  │   CELULAR       │    │   COMPUTADOR    │               │
│  │   (acesso)      │    │   (monitorado)  │               │
│  └─────────────────┘    └─────────────────┘               │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              TELEGRAM (Alertas em tempo real)       │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 💻 INSTALAÇÃO

### 🔧 Opção 1: Servidor Online (Recomendado para clientes)

```bash
# 1. Acesse o link
https://seu-dominio.onrender.com

# 2. Faça login
Senha: spynet2026

# 3. Pronto! Sistema funcionando
```

### 🖥️ Opção 2: Instalação Local (Para desenvolvimento)

```bash
# 1. Clone o repositório
git clone https://github.com/salveci2022/SentinelMonitor.git
cd SentinelMonitor

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Execute o sistema
python app.py

# 4. Acesse no navegador
http://localhost:5000
```

### 📦 Opção 3: Cliente Local (Para monitoramento)

```bash
# 1. Baixe o cliente local
# 2. Instale as dependências
pip install pyautogui sounddevice soundfile pynput requests numpy

# 3. Execute
python cliente_local.py

# 4. O monitoramento começa automaticamente
```

---

## 🎮 COMO USAR

### 🔐 Login

| Campo | Valor |
|-------|-------|
| **Senha** | `spynet2026` |

### 🔎 OSINT Tools

1. Clique em **"OSINT Tools"** no menu
2. Escolha o tipo de busca:
   - **Redes Sociais**: Digite nome, username, email ou telefone
   - **Bens Patrimoniais**: Digite CPF ou CNPJ
   - **Localização**: Digite endereço ou CEP
   - **Análise de Crédito**: Digite CPF
   - **Dados Vazados**: Digite email
3. Clique em **"BUSCAR"**
4. Os links serão gerados automaticamente

### 📁 Gestão de Casos

1. Clique em **"Novo Caso"**
2. Preencha os dados:
   - Tipo de caso
   - Cliente
   - Investigado
   - Objetivo
3. Clique em **"Criar Caso"**
4. Adicione etapas conforme a investigação avança
5. Ao final, gere o **PDF** do relatório

### 🛡️ Monitoramento (Cliente Local)

1. Execute o `cliente_local.py` no computador alvo
2. O monitoramento começa automaticamente:
   - Screenshot a cada 5 segundos
   - Áudio a cada 10 segundos
   - Keylogger em tempo real
3. Os dados são enviados para:
   - Telegram (se configurado)
   - Servidor online (se configurado)

---

## 🤖 COMANDOS TELEGRAM

| Comando | Função |
|---------|--------|
| `/start` | Inicia monitoramento |
| `/stop` | Pausa monitoramento |
| `/status` | Ver status atual |
| `/screenshot` | Capturar screenshot agora |
| `/audio` | Gravar áudio agora |
| `/logs` | Enviar log de teclas |
| `/clear` | Limpar logs |
| `/help` | Listar comandos |

---

## 💰 PLANOS E PREÇOS

| Plano | Funcionalidades | Preço |
|-------|-----------------|-------|
| **🔍 BÁSICO** | • OSINT Completo<br>• Gestão de Casos<br>• Relatórios PDF<br>• Acesso Web/Celular | **R$ 97/mês** |
| **🛡️ PROFISSIONAL** | • Tudo do Básico<br>• Monitoramento em Tempo Real<br>• Telegram Alerts<br>• Cliente Local | **R$ 197/mês** |
| **🏢 EMPRESARIAL** | • Tudo do Profissional<br>• Múltiplos usuários<br>• Suporte prioritário<br>• Treinamento | **R$ 497/mês** |
| **💎 VITALÍCIO** | • Tudo incluído<br>• Pagamento único<br>• Atualizações vitalícias | **R$ 1.497** |

---

## ❓ PERGUNTAS FREQUENTES

### 🤔 O sistema funciona no celular?

**Sim!** Todo o painel OSINT é responsivo e funciona perfeitamente no celular. O monitoramento (screenshot/áudio/keylogger) precisa rodar no computador.

### 🔒 É legal usar o monitoramento?

**Depende do uso:** 
- ✅ Próprio computador: legal
- ✅ Filho menor de idade: legal (responsabilidade dos pais)
- ✅ Funcionário (com aviso): legal
- ❌ Cônjuge sem permissão: crime
- ❌ Terceiros sem autorização: crime

### 📊 Quanto tempo leva uma investigação?

Com o SPYNET, uma investigação que levaria 6 horas manualmente, leva **cerca de 12 minutos** (95% mais rápido).

### 🔐 Meus dados estão seguros?

**Sim!** O sistema roda localmente ou no seu servidor. Nenhum dado é compartilhado com terceiros.

### 💳 Quais formas de pagamento?

Aceitamos PIX, cartão de crédito, boleto e transferência bancária.

### 🆘 Como funciona o suporte?

Suporte via:
- 📧 E-mail: suporte@spynet.com
- 📱 Telegram: @spynet_suporte
- 💬 WhatsApp: (11) 99999-9999

---

## 📞 SUPORTE

| Canal | Contato |
|-------|---------|
| **Telegram** | [@spynet_suporte](https://t.me/spynet_suporte) |
| **WhatsApp** | (11) 99999-9999 |
| **E-mail** | suporte@spynet.com |
| **Site** | www.spynet.com |

---

## 📄 LICENÇA

Este software é licenciado sob a **MIT License** - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

## ⚠️ AVISO LEGAL

Este sistema é fornecido para fins profissionais e legais. O usuário é **totalmente responsável** pelo uso das informações obtidas.

- ✅ Use apenas em conformidade com a LGPD (Lei 13.709/2018)
- ✅ Obtenha autorização quando necessário
- ✅ Não utilize para fins ilícitos

**O não cumprimento destas diretrizes pode resultar em penalidades civis e criminais.**

---

<div align="center">

## 🚀 COMEÇAR AGORA

### [🌐 ACESSAR SISTEMA](https://seu-dominio.onrender.com) | [📞 FALAR COM SUPORTE](https://t.me/spynet_suporte) | [📥 BAIXAR CLIENTE](https://github.com/salveci2022/SentinelMonitor/releases)

---

**Desenvolvido com 🕵️ por SPYNET Security**

*Sistema de Inteligência e Investigação Digital*

</div>
```