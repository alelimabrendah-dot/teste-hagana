from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import secrets
import random
from datetime import datetime
import os
import difflib
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import time

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'chave-temporaria')

# ========== CONFIGURAÇÕES ==========
EMAIL_CONFIG = {
    'sender': os.environ.get('EMAIL_SENDER', ''),
    'password': os.environ.get('EMAIL_PASSWORD', ''),
    'receiver': os.environ.get('EMAIL_RECEIVER', '')
}

# ========== PERGUNTAS DOS TESTES ==========
PERGUNTAS = {
    "Informática Básica": [
        {
            "pergunta": "O que é um CPU?",
            "opcoes": [
                "A) Unidade Central de Processamento - cérebro do computador",
                "B) Memória de armazenamento permanente", 
                "C) Dispositivo de entrada de dados",
                "D) Programa de edição de texto"
            ],
            "resposta_correta": 0
        },
        {
            "pergunta": "Qual programa é usado para planilhas?",
            "opcoes": [
                "A) Word",
                "B) Excel", 
                "C) PowerPoint",
                "D) Photoshop"
            ],
            "resposta_correta": 1
        },
        {
            "pergunta": "O que significa 'URL'?",
            "opcoes": [
                "A) Uniform Resource Locator - localizador de recursos",
                "B) Universal Random Link", 
                "C) User Registration Login",
                "D) Ultra Rapid Link"
            ],
            "resposta_correta": 0
        }
    ],
    "Atendimento ao Cliente": [
        {
            "pergunta": "Qual a primeira coisa a fazer ao atender um cliente?",
            "opcoes": [
                "A) Cumprimentar com educação e se identificar",
                "B) Pedir logo o problema", 
                "C) Transferir para outro setor",
                "D) Colocar em espera"
            ],
            "resposta_correta": 0
        },
        {
            "pergunta": "O cliente está nervoso. O que fazer?",
            "opcoes": [
                "A) Manter a calma e escutar com atenção", 
                "B) Falar mais alto que ele",
                "C) Pedir para ele se acalmar",
                "D) Encerrar a ligação"
            ],
            "resposta_correta": 0
        }
    ]
}

TEXTO_DIGITACAO = "A Haganá Segurança valoriza profissionais comprometidos com a excelência no atendimento e responsabilidade em suas funções. Nossa missão é proporcionar segurança e tranquilidade para nossos clientes."

# ========== ROTAS PRINCIPAIS ==========
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/iniciar_teste', methods=['POST'])
def iniciar_teste():
    nome = request.form.get('nome', '').strip()
    cpf = request.form.get('cpf', '').strip()
    tema = request.form.get('tema', 'Informática Básica')
    
    if not nome or not cpf:
        return "Por favor, preencha todos os campos", 400
    
    # Gerar código único para o candidato
    codigo = f"{nome[:3].upper()}{random.randint(1000,9999)}"
    
    session['candidato'] = {
        'nome': nome,
        'cpf': cpf, 
        'tema': tema,
        'codigo': codigo,
        'inicio': datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }
    
    return redirect(url_for('teste_teorico'))

@app.route('/teste_teorico')
def teste_teorico():
    if 'candidato' not in session:
        return redirect(url_for('index'))
    
    candidato = session['candidato']
    tema = candidato['tema']
    perguntas = PERGUNTAS.get(tema, PERGUNTAS["Informática Básica"])
    
    return render_template('teste_teorico.html', 
                         perguntas=perguntas, 
                         candidato=candidato)

@app.route('/submit_teorico', methods=['POST'])
def submit_teorico():
    if 'candidato' not in session:
        return redirect(url_for('index'))
    
    respostas = request.form.to_dict()
    candidato = session['candidato']
    tema = candidato['tema']
    perguntas = PERGUNTAS.get(tema, PERGUNTAS["Informática Básica"])
    
    # Calcular pontuação
    acertos = 0
    for i, pergunta in enumerate(perguntas):
        resposta_usuario = respostas.get(f'pergunta_{i}')
        if resposta_usuario and int(resposta_usuario) == pergunta['resposta_correta']:
            acertos += 1
    
    percentual = (acertos / len(perguntas)) * 100
    resultado = "APROVADO" if percentual >= 70 else "REPROVADO"
    
    # Salvar resultados
    session['resultado_teorico'] = {
        'acertos': acertos,
        'total': len(perguntas),
        'percentual': percentual,
        'resultado': resultado,
        'timestamp': datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }
    
    return redirect(url_for('resultado_teorico'))

@app.route('/resultado_teorico')
def resultado_teorico():
    if 'candidato' not in session or 'resultado_teorico' not in session:
        return redirect(url_for('index'))
    
    return render_template('resultado_teorico.html',
                         candidato=session['candidato'],
                         resultado=session['resultado_teorico'])

@app.route('/teste_digitacao')
def teste_digitacao():
    if 'candidato' not in session:
        return redirect(url_for('index'))
    
    return render_template('teste_digitacao.html',
                         texto=TEXTO_DIGITACAO,
                         candidato=session['candidato'])

@app.route('/submit_digitacao', methods=['POST'])
def submit_digitacao():
    if 'candidato' not in session:
        return redirect(url_for('index'))
    
    texto_digitado = request.form.get('texto_digitado', '').strip()
    tempo_gasto = request.form.get('tempo_gasto', '0')
    
    # Calcular precisão
    sequencia = difflib.SequenceMatcher(None, TEXTO_DIGITACAO.lower(), texto_digitado.lower())
    precisao = sequencia.ratio() * 100
    
    # Salvar resultados
    session['resultado_digitacao'] = {
        'precisao': precisao,
        'tempo_gasto': tempo_gasto,
        'timestamp': datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }
    
    # Enviar e-mail com resultados completos
    enviar_email_resultados()
    
    return redirect(url_for('resultado_digitacao'))

@app.route('/resultado_digitacao')
def resultado_digitacao():
    if 'candidato' not in session or 'resultado_digitacao' not in session:
        return redirect(url_for('index'))
    
    return render_template('resultado_digitacao.html',
                         candidato=session['candidato'],
                         resultado=session['resultado_digitacao'])

# ========== FUNÇÃO ENVIAR E-MAIL ==========
def enviar_email_resultados():
    try:
        if not all([EMAIL_CONFIG['sender'], EMAIL_CONFIG['password'], EMAIL_CONFIG['receiver']]):
            print("Configurações de e-mail não encontradas")
            return False
        
        candidato = session.get('candidato', {})
        teorico = session.get('resultado_teorico', {})
        digitacao = session.get('resultado_digitacao', {})
        
        # Criar mensagem
        subject = f"Resultado Teste - {candidato.get('nome', 'Candidato')}"
        
        body = f"""
        RESULTADO DO TESTE - HAGANÁ SEGURANÇA
        
        DADOS DO CANDIDATO:
        Nome: {candidato.get('nome', 'N/A')}
        CPF: {candidato.get('cpf', 'N/A')}
        Código: {candidato.get('codigo', 'N/A')}
        Data/Hora: {candidato.get('inicio', 'N/A')}
        
        TESTE TEÓRICO ({candidato.get('tema', 'N/A')}):
        Acertos: {teorico.get('acertos', 0)}/{teorico.get('total', 0)}
        Percentual: {teorico.get('percentual', 0):.1f}%
        Resultado: {teorico.get('resultado', 'N/A')}
        
        TESTE DE DIGITAÇÃO:
        Precisão: {digitacao.get('precisao', 0):.1f}%
        Tempo Gasto: {digitacao.get('tempo_gasto', 0)} segundos
        
        ---
        Enviado automaticamente pelo Sistema de Testes
        """
        
        # Configurar e-mail
        msg = MimeMultipart()
        msg['From'] = EMAIL_CONFIG['sender']
        msg['To'] = EMAIL_CONFIG['receiver']
        msg['Subject'] = subject
        msg.attach(MimeText(body, 'plain'))
        
        # Enviar
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_CONFIG['sender'], EMAIL_CONFIG['password'])
        server.send_message(msg)
        server.quit()
        
        print("E-mail enviado com sucesso!")
        return True
        
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")
        return False

if __name__ == '__main__':
    app.run(debug=True)