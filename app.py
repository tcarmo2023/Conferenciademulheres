import os
from flask import Flask, render_template_string, request, redirect, url_for, send_file, jsonify, session, flash, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
from io import BytesIO
import base64

app = Flask(__name__)

# ✅ CORREÇÃO DEFINITIVA PARA DATABASE_URL
def get_database_url():
    # Tenta pegar do Railway primeiro
    railway_db_url = os.environ.get('DATABASE_URL', '')
    
    if railway_db_url:
        # Corrige formato se necessário
        if railway_db_url.startswith('postgres://'):
            railway_db_url = railway_db_url.replace('postgres://', 'postgresql://', 1)
        return railway_db_url
    
    # Fallback para string local (apenas para desenvolvimento)
    return "sqlite:///local.db"

# ✅ CONFIGURAÇÃO DO BANCO DE DADOS
app.config['SQLALCHEMY_DATABASE_URI'] = get_database_url()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True
}

# ✅ SECRET KEY SEGURA
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'fallback-secret-key-2025-conferencia-mulheres')

# ✅ CONFIGURAÇÃO DE PORTA PARA RAILWAY
port = int(os.environ.get("PORT", 5000))

UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}

db = SQLAlchemy(app)

PIX_KEY = "6d51bb56-3bee-45b1-a26c-2b04c1a6718b"
PAYMENT_AMOUNT = "10.00"
WHATSAPP_NUMBER = "558185641262"
ADMIN_PASSWORD = "CODE@2025"

# URLs das imagens - usando links diretos do GitHub RAW
BORBOLETA_URL = "https://raw.githubusercontent.com/tcarmo2023/conferenciademulheres/3a7f2a22da1c2bf7d200a69bd484d550d86cb5b8/borboleta.png"
BORBOLETA_ANIMADA_URL = "https://raw.githubusercontent.com/tcarmo2023/conferenciademulheres/3a7f2a22da1c2bf7d200a69bd484d550d86cb5b8/borboleta.png"
LOGO_URL = "https://raw.githubusercontent.com/tcarmo2023/conferenciademulheres/cb246a297516723bd90b42cc26d432778ad6354e/logo.jpeg"
QUEM_SOMOS_LOGO = "https://raw.githubusercontent.com/tcarmo2023/conferenciademulheres/cb246a297516723bd90b42cc26d432778ad6354e/Quem%20somos.png"

# URLs dos QR Codes PIX
QR_CODES = {
    "5.00": "https://raw.githubusercontent.com/tcarmo2023/conferenciademulheres/3a7f2a22da1c2bf7d200a69bd484d550d86cb5b8/qrcode-pix.svg",
    "10.00": "https://raw.githubusercontent.com/tcarmo2023/conferenciademulheres/3a7f2a22da1c2bf7d200a69bd484d550d86cb5b8/qrcode-pix_10.png",
    "15.00": "https://raw.githubusercontent.com/tcarmo2023/conferenciademulheres/3a7f2a22da1c2bf7d200a69bd484d550d86cb5b8/qrcode-pix_15.png",
    "20.00": "https://raw.githubusercontent.com/tcarmo2023/conferenciademulheres/3a7f2a22da1c2bf7d200a69bd484d550d86cb5b8/qrcode-pix_20.png",
    "25.00": "https://raw.githubusercontent.com/tcarmo2023/conferenciademulheres/3a7f2a22da1c2bf7d200a69bd484d550d86cb5b8/qrcode-pix_25.png"
}

# ---------------- Models (Eventos e Workshops separados) ----------------
class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    sobrenome = db.Column(db.String(120), nullable=False)
    cpf = db.Column(db.String(20), nullable=False)
    telefone = db.Column(db.String(30), nullable=False)
    evento_id = db.Column(db.Integer, db.ForeignKey('evento.id'))
    paid = db.Column(db.Boolean, default=False)
    status_inscricao = db.Column(db.String(20), default="Pré-inscrito")
    comprovante_filename = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Evento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    data = db.Column(db.String(50))
    horario = db.Column(db.String(50))
    local = db.Column(db.String(200))
    descricao = db.Column(db.Text)
    valor_inscricao = db.Column(db.String(20), default="10.00")
    status = db.Column(db.String(20), default="Aberto")
    agradecimento = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    fotos = db.relationship('FotoEvento', backref='evento', lazy=True, cascade="all,delete-orphan")
    inscricoes = db.relationship('Registration', backref='evento', lazy=True)

class FotoEvento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    evento_id = db.Column(db.Integer, db.ForeignKey('evento.id'), nullable=False)
    filename = db.Column(db.String(300), nullable=False)
    comentario = db.Column(db.Text)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

class Workshop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    data = db.Column(db.String(50))
    horario = db.Column(db.String(50))
    local = db.Column(db.String(200))
    abordagem = db.Column(db.Text)
    status = db.Column(db.String(20), default="Em Breve")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ✅ FUNÇÃO PARA CRIAR TABELAS DE FORMA SEGURA
def create_tables():
    try:
        with app.app_context():
            db.create_all()
            print("✅ Tabelas criadas/verificadas com sucesso!")
            print(f"📊 Database URL: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")  # Mostra apenas parte da URL por segurança
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")

# Chama a função para criar tabelas
create_tables()

# ---------------- Utilities ----------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file_storage):
    filename = secure_filename(file_storage.filename)
    base, ext = os.path.splitext(filename)
    unique_name = f"{base}_{int(datetime.utcnow().timestamp())}{ext}"
    save_path = os.path.join(UPLOAD_FOLDER, unique_name)
    file_storage.save(save_path)
    return unique_name

def get_qr_code_url(valor):
    return QR_CODES.get(valor, QR_CODES["10.00"])

# ---------------- SEGURANÇA ADMIN - CORREÇÃO SIMPLIFICADA ----------------
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged'):
            flash("Acesso negado. Faça login primeiro.", "danger")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ---------------- Base template ----------------
base_css_js = """
<!doctype html>
<html lang="pt-br">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Conferência de Mulheres</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
      :root{ --terra-1: #7a3f15; --terra-2: #c2773a; --terra-3: #f3d9c6; --terra-4: #f6eadf; }
      body { background: #fff; color: #2b2b2b; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; position: relative; overflow-x: hidden; }
      .site-header { background: linear-gradient(90deg,var(--terra-1), var(--terra-2)); color: white; padding: 15px 0; }
      .site-title { font-size: 1.2rem; display:flex; align-items:center; gap:12px; }
      .site-title img { height:56px; width:56px; object-fit:contain; border-radius:8px; background:white; padding:6px; }
      .btn-terra { 
        background: var(--terra-2); 
        color: white; 
        border: none; 
        transition: all 0.3s ease;
        transform: translateY(0);
        box-shadow: 0 4px 6px rgba(194, 119, 58, 0.2);
      }
      .btn-terra:hover { 
        background: var(--terra-1); 
        color: white; 
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(194, 119, 58, 0.3);
      }
      .nav-link { 
        color: white !important; 
        font-weight: 500; 
        transition: all 0.3s ease;
        position: relative;
        padding: 8px 16px;
        border-radius: 6px;
      }
      .nav-link:hover { 
        color: var(--terra-3) !important; 
        background: rgba(255,255,255,0.1);
        transform: translateY(-2px);
      }
      .nav-link::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 50%;
        width: 0;
        height: 2px;
        background: var(--terra-3);
        transition: all 0.3s ease;
        transform: translateX(-50%);
      }
      .nav-link:hover::after {
        width: 80%;
      }
      footer { padding: 20px 0; background:#f8f0ea; margin-top:40px; }
      .qr-img { width:260px; height:260px; border: 2px solid var(--terra-3); border-radius: 10px; padding: 10px; background: white; object-fit:contain; }
      .event-card { border: none; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.08); transition: transform 0.3s ease, box-shadow 0.3s ease; }
      .event-card:hover { transform: translateY(-8px); box-shadow: 0 8px 16px rgba(0,0,0,0.15); }
      .event-img { height: 240px; object-fit: cover; border-top-left-radius: 10px; border-top-right-radius: 10px; }
      .idealizadora-img { width: 150px; height: 150px; border-radius: 50%; object-fit: cover; margin: 0 auto 15px; border: 4px solid var(--terra-3); }
      .pix-info { background: var(--terra-4); padding: 15px; border-radius: 8px; margin: 15px 0; }
      .pix-key { font-family: monospace; background: white; padding: 8px; border-radius: 4px; word-break: break-all; }
      .quem-somos-text { font-size: 1.2rem; line-height: 1.6; }
      
      /* Borboleta animada */
      .borboleta-flutuante {
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 80px;
        height: 80px;
        z-index: 1000;
        animation: flutuar 3s ease-in-out infinite;
        pointer-events: none;
      }
      
      @keyframes flutuar {
        0%, 100% { transform: translateY(0) rotate(0deg); }
        25% { transform: translateY(-10px) rotate(5deg); }
        50% { transform: translateY(-5px) rotate(0deg); }
        75% { transform: translateY(-10px) rotate(-5deg); }
      }
      
      @keyframes fadeInUp {
        from {
          opacity: 0;
          transform: translateY(30px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }
      
      .animate-fade-in-up {
        animation: fadeInUp 0.6s ease-out;
      }
      
      .admin-back-btn {
        margin-bottom: 20px;
      }
      
      .status-preinscrito { color: #856404; background-color: #fff3cd; border-color: #ffeaa7; }
      .status-confirmado { color: #155724; background-color: #d4edda; border-color: #c3e6cb; }
    </style>
  </head>
  <body>
    <img src=\"""" + BORBOLETA_ANIMADA_URL + """\" class="borboleta-flutuante" alt="Borboleta">
    
    <header class="site-header">
      <div class="container">
        <div class="d-flex justify-content-between align-items-center">
          <div class="site-title">
            <img src=\"""" + BORBOLETA_URL + """\" alt="Borboleta" />
            <div>
              <div style="font-weight:700; font-size:1.1rem">Conferência de Mulheres</div>
              <small>Essência que Transforma</small>
            </div>
          </div>

          <button class="navbar-toggler d-md-none" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
            <i class="fas fa-bars"></i>
          </button>

          <nav class="d-none d-md-flex align-items-center">
            <a class="nav-link mx-2" href="{{ url_for('index') }}">Inicial</a>
            <a class="nav-link mx-2" href="{{ url_for('quem_somos') }}">Quem Somos</a>
            <a class="nav-link mx-2" href="{{ url_for('eventos') }}">Eventos</a>
            <a class="nav-link mx-2" href="{{ url_for('inscricao') }}">Inscrição</a>
            <a class="nav-link mx-2" href="{{ url_for('contato') }}">Contato</a>
            {% if session.admin_logged %}
            <a class="nav-link mx-2" href="{{ url_for('admin_dashboard') }}">Área do Administrador</a>
            <a class="nav-link mx-2" href="{{ url_for('admin_logout') }}">Sair</a>
            {% else %}
            <a class="nav-link mx-2" href="{{ url_for('admin_login') }}">Área do Administrador</a>
            {% endif %}
          </nav>
        </div>

        <div class="collapse d-md-none mt-3" id="navbarNav">
          <div class="d-flex flex-column">
            <a class="nav-link py-2" href="{{ url_for('index') }}">Inicial</a>
            <a class="nav-link py-2" href="{{ url_for('quem_somos') }}">Quem Somos</a>
            <a class="nav-link py-2" href="{{ url_for('eventos') }}">Eventos</a>
            <a class="nav-link py-2" href="{{ url_for('inscricao') }}">Inscrição</a>
            <a class="nav-link py-2" href="{{ url_for('contato') }}">Contato</a>
            {% if session.admin_logged %}
            <a class="nav-link py-2" href="{{ url_for('admin_dashboard') }}">Área do Administrador</a>
            <a class="nav-link py-2" href="{{ url_for('admin_logout') }}">Sair</a>
            {% else %}
            <a class="nav-link py-2" href="{{ url_for('admin_login') }}">Área do Administrador</a>
            {% endif %}
          </div>
        </div>
      </div>
    </header>

    <main class="container my-4">
      {% if session.admin_logged and request.path.startswith('/admin') and request.path != '/admin/login' %}
      <div class="admin-back-btn">
        <a href="/admin" class="btn btn-terra">
          <i class="fas fa-arrow-left me-2"></i>Voltar para Área do Administrador
        </a>
      </div>
      {% endif %}
      {{ content|safe }}
    </main>

    <footer>
      <div class="container d-flex justify-content-between align-items-center">
        <div>
          <strong>Conferência de Mulheres</strong><br>
          <small>Direitos reservados</small>
        </div>
        <div>
          <a class="social-btn" href="https://wa.me/55{{ whatsapp_number }}" target="_blank">
            <i class="fab fa-whatsapp"></i>
          </a>
          <a class="social-btn" href="https://www.instagram.com/renovadas0.25?igsh=MXQ3dWxkNnQ2enQ2aQ%3D%3D&utm_source=qr" target="_blank">
            <i class="fab fa-instagram"></i>
          </a>
        </div>
      </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    {{ scripts|safe }}
  </body>
</html>
"""

# ------------------ Helpers para renderização dinâmica ------------------
def render_index_content():
    last_event = Evento.query.order_by(Evento.created_at.desc()).first()
    last_workshop = Workshop.query.order_by(Workshop.created_at.desc()).first()

    content = """
      <div class="text-center py-5" style="background:var(--terra-4); border-radius:8px;">
        <h1 class="mb-3" style="color:var(--terra-1)">Conferência de Mulheres 2025</h1>
        <p class="lead">Um encontro divino para mulheres cristãs que desejam renovar sua fé e propósito em Cristo.</p>
        <a href="/inscricao" class="btn btn-terra btn-lg">Inscreva-se</a>
      </div>

      <section class="my-5">
        <h2 class="text-center" style="color:var(--terra-1)">Bem-vinda à Conferência de Mulheres</h2>
        <p class="text-center">Confira abaixo alguns momentos especiais dos nossos eventos:</p>

        <div class="text-center mt-4">
          <h3 style="color:var(--terra-2)">Registros dos Eventos</h3>
          <p>Confira abaixo alguns momentos especiais dos nossos eventos anteriores:</p>
          <div class="row mt-4">
    """

    if last_event:
        if last_event.fotos and len(last_event.fotos) > 0:
            cover = "/static/uploads/" + last_event.fotos[0].filename
        else:
            cover = "https://placehold.co/800x600/f6eadf/c2773a?text=Evento+2025"
        content += f"""
          <div class="col-md-6 mb-4 animate-fade-in-up">
            <div class="card event-card">
              <img src="{cover}" class="event-img" alt="Evento 2025">
              <div class="card-body text-center">
                <h2 style="color:var(--terra-2)">Evento 2025</h2>
                <p>Essência que Transforma<br>Próximo encontro — aguarde mais informações.</p>
                <a class="btn btn-terra" href="/evento/{last_event.id}">Ver</a>
                {"<a class='btn btn-terra ms-2' href='/inscricao'>Inscrever-se</a>" if last_event.status == 'Aberto' else ""}
              </div>
            </div>
          </div>
        """
    else:
        content += """
          <div class="col-md-6 mb-4 animate-fade-in-up">
            <div class="card event-card">
              <img src="https://placehold.co/800x600/f6eadf/c2773a?text=Evento+2025" class="event-img" alt="Evento 2025">
              <div class="card-body text-center">
                <h2 style="color:var(--terra-2)">Evento 2025</h2>
                <p>Essência que Transforma<br>Próximo encontro — aguarde mais informações.</p>
                <a class="btn btn-terra" href="#">Ver</a>
              </div>
            </div>
          </div>
        """

    if last_workshop:
        cover_w = "https://placehold.co/800x600/f6eadf/c2773a?text=" + (last_workshop.titulo.replace(" ", "+"))
        description_w = last_workshop.abordagem if last_workshop.abordagem else "Em Breve"
        content += f"""
          <div class="col-md-6 mb-4 animate-fade-in-up">
            <div class="card event-card">
              <img src="{cover_w}" class="event-img" alt="{last_workshop.titulo}">
              <div class="card-body text-center">
                <h2 style="color:var(--terra-2)">{last_workshop.titulo}</h2>
                <p>{'Em Breve' if last_workshop.status=='Em Breve' else description_w}</p>
                <a class="btn btn-terra" href="/workshop/{last_workshop.id}">Ver</a>
              </div>
            </div>
          </div>
        """
    else:
        content += """
          <div class="col-md-6 mb-4 animate-fade-in-up">
            <div class="card event-card">
              <img src="https://placehold.co/800x600/f6eadf/c2773a?text=Workshop" class="event-img" alt="Workshop">
              <div class="card-body text-center">
                <h2 style="color:var(--terra-2)">Workshop</h2>
                <p>Em Breve</p>
                <a class="btn btn-terra" href="#">Ver</a>
              </div>
            </div>
          </div>
        """

    content += "</div></div></section>"
    return content

# ---------------- Pages (Quem somos, Contato, Inscrição, Eventos list) ----------------
def get_quem_content():
    return """
  <h2 class="mb-4" style="color:var(--terra-1)">Quem Somos</h2>
  <div class="row">
    <div class="col-md-6">
      <p class="quem-somos-text">Somos um grupo de mulheres cristãs que desejam compartilhar o amor de Deus e fortalecer a comunidade feminina na fé.</p>
      <p class="quem-somos-text">Nosso evento foi idealizado para proporcionar um momento de renovação e transformação através da Palavra de Deus, com workshops, palestras e momentos de adoração.</p>
      
      <div class="mt-4">
        <h3 style="color:var(--terra-2)">Siga-nos no Instagram</h3>
        <a href="https://www.instagram.com/renovadas0.25?igsh=MXQ3dWxkNnQ2enQ2aQ%3D%3D&utm_source=qr" target="_blank" class="btn btn-terra">
          <i class="fab fa-instagram me-2"></i> @renovadas0.25
        </a>
      </div>
    </div>
    <div class="col-md-6">
      <img src=\"""" + QUEM_SOMOS_LOGO + """\" class="img-fluid rounded" alt="Quem Somos">
    </div>
  </div>
"""

def get_contato_content():
    return """
  <h2 class="mb-4" style="color:var(--terra-1)">Contato</h2>

  <div class="row">
    <div class="col-md-6">
      <div class="card p-3">
        <div class="card-body">
          <h5 class="card-title" style="color:var(--terra-2)">Entre em Contato</h5>
          <p><i class="fab fa-whatsapp me-2"></i> WhatsApp: +55 81 8564-1262</p>
          <p><i class="fab fa-instagram me-2"></i> Instagram: <a href="https://www.instagram.com/renovadas0.25?igsh=MXQ3dWxkNnQ2enQ2aQ%3D%3D&utm_source=qr" target="_blank">@renovadas0.25</a></p>
          <div class="mt-4">
            <a href="https://wa.me/55""" + WHATSAPP_NUMBER + """" class="btn btn-terra me-2" target="_blank"><i class="fab fa-whatsapp me-1"></i> Enviar Mensagem</a>
            <a href="https://www.instagram.com/renovadas0.25?igsh=MXQ3dWxkNnQ2enQ2aQ%3D%3D&utm_source=qr" class="btn btn-terra" target="_blank"><i class="fab fa-instagram me-1"></i> Seguir no Instagram</a>
          </div>
        </div>
      </div>

      <div class="card mt-3">
        <div class="card-body">
          <h5>Site Desenvolvido por TM Code</h5>
          <p>Contatos do WhatsApp: 
            <a href="https://wa.me/5581995143900" target="_blank" class="text-decoration-none">(81) 99514-3900</a> | 
            <a href="https://wa.me/5581987734133" target="_blank" class="text-decoration-none">(81) 98773-4133</a>
          </p>
          <div class="mt-3">
            <img src=\"""" + LOGO_URL + """\" style="height: 70px;" alt="Logo TM Code" />
          </div>
          <div class="mt-2">
            <a href="https://tmcodeportifolio.netlify.app/" target="_blank" class="btn btn-terra btn-sm">
              <i class="fas fa-external-link-alt me-1"></i> Ver Portfólio
            </a>
          </div>
        </div>
      </div>

    </div>

    <div class="col-md-6">
      <img src="https://placehold.co/600x400/f6eadf/c2773a?text=Contato" class="img-fluid rounded" alt="Contato">
    </div>
  </div>
"""

def get_inscricao_content():
    eventos = Evento.query.order_by(Evento.status.desc(), Evento.created_at.desc()).all()
    
    if not eventos:
        return """
        <h2 class="mb-4" style="color:var(--terra-1)">Inscrição - Conferência de Mulheres</h2>
        <div class="alert alert-info">
          <h4>Nenhum evento disponível no momento</h4>
          <p>Em breve teremos novos eventos. Fique atenta às nossas redes sociais!</p>
        </div>
        """
    
    eventos_abertos = [e for e in eventos if e.status == 'Aberto']
    eventos_encerrados = [e for e in eventos if e.status == 'Fechado']
    
    if len(eventos_abertos) == 1:
        evento_selecionado = eventos_abertos[0]
        return get_inscricao_form(evento_selecionado)
    else:
        return get_selecao_evento_content(eventos_abertos, eventos_encerrados)

def get_selecao_evento_content(eventos_abertos, eventos_encerrados):
    content = """
    <h2 class="mb-4" style="color:var(--terra-1)">Inscrição - Conferência de Mulheres</h2>
    <div class="card p-4 mb-4">
      <h4 style="color:var(--terra-2)">Selecione o Evento</h5>
      <p>Escolha abaixo o evento para o qual deseja se inscrever:</p>
    """
    
    if eventos_abertos:
        content += """
        <div class="mb-4">
          <h5 style="color:var(--terra-2)">Eventos com Inscrições Abertas</h5>
          <div class="row">
        """
        for evento in eventos_abertos:
            content += f"""
            <div class="col-md-6 mb-3">
              <div class="card event-card">
                <div class="card-body">
                  <h5>{evento.titulo}</h5>
                  <p><strong>Data:</strong> {evento.data or 'A definir'}</p>
                  <p><strong>Horário:</strong> {evento.horario or 'A definir'}</p>
                  <p><strong>Local:</strong> {evento.local or 'A definir'}</p>
                  <p><strong>Valor:</strong> R$ {evento.valor_inscricao or '10.00'}</p>
                  <a href="/inscricao/{evento.id}" class="btn btn-terra">Inscrever-se</a>
                </div>
              </div>
            </div>
            """
        content += "</div></div>"
    
    if eventos_encerrados:
        content += """
        <div class="mb-4">
          <h5 style="color:var(--terra-2)">Eventos Encerrados</h5>
          <div class="row">
        """
        for evento in eventos_encerrados:
            content += f"""
            <div class="col-md-6 mb-3">
              <div class="card event-card">
                <div class="card-body">
                  <h5>{evento.titulo}</h5>
                  <p><strong>Data:</strong> {evento.data or 'A definir'}</p>
                  <p><strong>Status:</strong> <span class="badge bg-secondary">Encerrado</span></p>
                  <p><strong>Local:</strong> {evento.local or 'A definir'}</p>
                  <a href="/evento/{evento.id}" class="btn btn-outline-secondary">Ver Detalhes</a>
                </div>
              </div>
            </div>
            """
        content += "</div></div>"
    
    content += "</div>"
    return content

def get_inscricao_form(evento):
    valor_inscricao = evento.valor_inscricao or PAYMENT_AMOUNT
    qr_code_url = get_qr_code_url(valor_inscricao)
    
    return f"""
  <h2 class="mb-4" style="color:var(--terra-1)">Inscrição - {evento.titulo}</h2>

  <div class="card p-4 mb-4">
    <div class="mb-4">
      <h4 style="color:var(--terra-2)">Informações do Evento</h4>
      <p><strong>Evento:</strong> {evento.titulo}</p>
      <p><strong>Data:</strong> {evento.data or 'A definir'}</p>
      <p><strong>Horário:</strong> {evento.horario or 'A definir'}</p>
      <p><strong>Local:</strong> {evento.local or 'A definir'}</p>
      <p><strong>Descrição:</strong> {evento.descricao or 'Em breve mais informações'}</p>
    </div>

    <div id="dadosPessoais">
      <h4 style="color:var(--terra-2)">Dados Pessoais</h4>
      <form id="preInscricaoForm" method="POST" action="/submit_pre_inscricao" enctype="multipart/form-data">
        <input type="hidden" name="evento_id" value="{evento.id}">
        <div class="row">
          <div class="col-md-6 mb-3">
            <label class="form-label">Nome</label>
            <input name="nome" class="form-control" required>
          </div>
          <div class="col-md-6 mb-3">
            <label class="form-label">Sobrenome</label>
            <input name="sobrenome" class="form-control" required>
          </div>
          <div class="col-md-6 mb-3">
            <label class="form-label">CPF</label>
            <input name="cpf" class="form-control" required placeholder="000.000.000-00">
          </div>
          <div class="col-md-6 mb-3">
            <label class="form-label">Telefone (WhatsApp)</label>
            <input name="telefone" class="form-control" required placeholder="(00) 00000-0000">
          </div>
        </div>

        <div class="mb-3 p-3" style="background-color: var(--terra-4); border-radius: 8px;">
          <strong>Valor da inscrição: R$ {valor_inscricao}</strong>
        </div>

        <button type="submit" class="btn btn-terra btn-lg">Pré-Inscrição</button>
      </form>
    </div>

    <div id="pagamentoSection" style="display: none;">
      <div class="alert alert-info mt-4">
        <h5>Agora, escaneie o QR Code ou copie a chave Pix para efetuar o pagamento.</h5>
      </div>

      <div class="row mt-4">
        <div class="col-md-6">
          <div class="pix-info">
            <p>Valor a ser pago: <strong>R$ {valor_inscricao}</strong></p>
            <p>Chave Pix: <span class="pix-key">{PIX_KEY}</span></p>
            <button class="btn btn-sm btn-outline-secondary mt-2" onclick="copyPixKey()">
              <i class="fas fa-copy me-1"></i> Copiar Chave
            </button>
          </div>
          <img class="qr-img mt-3" src="{qr_code_url}" alt="QR Code Pix">
        </div>
        
        <div class="col-md-6">
          <form id="comprovanteForm" method="POST" action="/upload_comprovante" enctype="multipart/form-data">
            <input type="hidden" name="pre_inscricao_id" id="preInscricaoId">
            <div class="mb-3">
              <label class="form-label">Envie o comprovante de pagamento</label>
              <input type="file" name="comprovante" class="form-control" accept=".png,.jpg,.jpeg,.gif,.webp,.pdf" required>
              <small class="text-muted">Formatos aceitos: PNG, JPG, JPEG, GIF, WEBP, PDF (tamanho máximo: 5MB)</small>
            </div>
            <button type="submit" class="btn btn-success btn-lg">
              <i class="fas fa-upload me-2"></i> Enviar Comprovante
            </button>
          </form>
        </div>
      </div>
    </div>

    <div id="confirmacaoSection" style="display: none;">
      <div class="alert alert-success mt-4">
        <h5>Parabéns, sua pré-inscrição foi confirmada! Em breve entraremos em contato para validar sua inscrição.</h5>
      </div>
      
      <div class="text-center mt-4">
        <a href="https://chat.whatsapp.com/ICWsAlDkaFZ7vmcZme0Myr?mode=ems_wa_t" target="_blank" class="btn btn-success btn-lg">
          <i class="fab fa-whatsapp me-2"></i> Entrar no grupo do WhatsApp Renovadas
        </a>
      </div>
    </div>
  </div>
"""

inscricao_scripts = """
<script>
  function copyPixKey() {
    const pixKey = '""" + PIX_KEY + """';
    navigator.clipboard.writeText(pixKey).then(function() {
      alert('Chave PIX copiada para a área de transferência!');
    }, function(err) {
      console.error('Erro ao copiar chave: ', err);
    });
  }

  document.getElementById('preInscricaoForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    
    fetch('/submit_pre_inscricao', {
      method: 'POST',
      body: formData
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        document.getElementById('dadosPessoais').style.display = 'none';
        document.getElementById('pagamentoSection').style.display = 'block';
        document.getElementById('preInscricaoId').value = data.inscricao_id;
      } else {
        alert('Erro ao realizar pré-inscrição: ' + data.message);
      }
    })
    .catch(error => {
      console.error('Error:', error);
      alert('Erro ao realizar pré-inscrição');
    });
  });

  document.getElementById('comprovanteForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    
    fetch('/upload_comprovante', {
      method: 'POST',
      body: formData
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        document.getElementById('pagamentoSection').style.display = 'none';
        document.getElementById('confirmacaoSection').style.display = 'block';
      } else {
        alert('Erro ao enviar comprovante: ' + data.message);
      }
    })
    .catch(error => {
      console.error('Error:', error);
      alert('Erro ao enviar comprovante');
    });
  });
</script>
"""

print_tpl = """
<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Comprovante de Inscrição</title>
  <style>
    body{font-family:Arial,Helvetica,sans-serif; padding:20px;}
    .card{border:1px solid #ddd;padding:18px;border-radius:8px;max-width:700px;margin:auto;}
    h1{color:#7a3f15}
    .qr{width:180px;height:180px; border: 2px solid #f3d9c6; border-radius: 8px; padding: 8px; background: white;}
    .instructions{margin-top:12px;padding:10px;background:#f6eadf;border-radius:6px}
    .pix-info { background: #f6eadf; padding: 12px; border-radius: 6px; margin: 12px 0; }
    .pix-key { font-family: monospace; background: white; padding: 6px; border-radius: 4px; word-break: break-all; }
    @media print{ .no-print{display:none} }
  </style>
</head>
<body>
  <div class="card">
    <h1>Comprovante de Inscrição</h1>
    <p><strong>Evento:</strong> {{ event_title }}</p>
    <p><strong>Nome:</strong> {{ reg.nome }} {{ reg.sobrenome }}</p>
    <p><strong>CPF:</strong> {{ reg.cpf }}</p>
    <p><strong>Telefone:</strong> {{ reg.telefone }}</p>
    <p><strong>Valor:</strong> R$ {{ payment_amount }}</p>
    <p><strong>Data do cadastro:</strong> {{ reg.created_at.strftime('%d/%m/%Y %H:%M') }}</p>

    <div class="pix-info">
      <p><strong>Informações do PIX:</strong></p>
      <p>Valor: R$ {{ payment_amount }}</p>
      <p>Chave: <span class="pix-key">{{ pix_key }}</span></p>
    </div>

    <div style="display:flex;gap:20px;align-items:center;margin-top:12px;">
      <img src="{{ qr_code_url }}" class="qr" alt="QR Code Pix">
      <div>
        <div style="font-weight:700">Pagamento de Inscrição Realizada</div>
        <div class="instructions">
          Baixe ou tire print desta tela para apresentar no dia do evento.
        </div>
      </div>
    </div>

    <div class="mt-4 p-3" style="background-color: #f0f8f0; border-radius: 8px;">
      <h6>Entre no Grupo do WhatsApp - Transformadas</h6>
      <p>Entre no nosso grupo para receber todas as informações sobre o evento:</p>
      <a href="https://chat.whatsapp.com/ICWsAlDkaFZ7vmcZme0Myr?mode=ems_wa_t" target="_blank" class="btn btn-success">
        <i class="fab fa-whatsapp me-2"></i> Entrar no Grupo
      </a>
    </div>

    <div style="margin-top:14px;">
      <button onclick="window.print()" class="no-print">Imprimir / Salvar</button>
    </div>
  </div>
</body>
</html>
"""

# ---------------- Routes principais ----------------
@app.route('/')
def index():
    content = render_index_content()
    return render_template_string(base_css_js.replace("{{ content|safe }}", content),
                                  whatsapp_number=WHATSAPP_NUMBER,
                                  scripts="")

@app.route('/quem-somos')
def quem_somos():
    content = get_quem_content()
    return render_template_string(base_css_js.replace("{{ content|safe }}", content),
                                  whatsapp_number=WHATSAPP_NUMBER,
                                  scripts="")

@app.route('/eventos')
def eventos():
    eventos = Evento.query.order_by(Evento.created_at.desc()).all()
    content = "<h2 style='color:var(--terra-1)'>Eventos Cadastrados</h2><div class='row'>"
    if not eventos:
        content += "<div class='col-12'><p>Nenhum evento cadastrado.</p></div>"
    else:
        for ev in eventos:
            content += f"""
            <div class='col-md-6 mb-4 animate-fade-in-up'>
              <div class='card event-card'>
                <div class='card-body'>
                  <h5>{ev.titulo} <small class='text-muted'>({ev.status})</small></h5>
                  <p><strong>Data:</strong> {ev.data or ''} <strong>Horário:</strong> {ev.horario or ''}</p>
                  <p><strong>Valor da inscrição:</strong> R$ {ev.valor_inscricao or PAYMENT_AMOUNT}</p>
                  <p>{ (ev.descricao or '')[:180] }</p>
                  <a class='btn btn-terra' href='/evento/{ev.id}'>Abrir</a>
                </div>
              </div>
            </div>
            """
    content += "</div>"
    return render_template_string(base_css_js.replace("{{ content|safe }}", content),
                                  whatsapp_number=WHATSAPP_NUMBER,
                                  scripts="")

@app.route('/contato')
def contato():
    content = get_contato_content()
    return render_template_string(base_css_js.replace("{{ content|safe }}", content),
                                  whatsapp_number=WHATSAPP_NUMBER,
                                  scripts="")

@app.route('/inscricao')
@app.route('/inscricao/<int:evento_id>')
def inscricao(evento_id=None):
    if evento_id:
        evento = Evento.query.get_or_404(evento_id)
        if evento.status != 'Aberto':
            flash("Este evento não está com inscrições abertas.", "warning")
            return redirect(url_for('inscricao'))
        content = get_inscricao_form(evento)
    else:
        content = get_inscricao_content()
    
    return render_template_string(base_css_js.replace("{{ content|safe }}", content),
                                  whatsapp_number=WHATSAPP_NUMBER,
                                  scripts=inscricao_scripts)

# ---------------- NOVAS ROTAS PARA PRÉ-INSCRIÇÃO ----------------
@app.route('/submit_pre_inscricao', methods=['POST'])
def submit_pre_inscricao():
    try:
        nome = request.form.get('nome', '').strip()
        sobrenome = request.form.get('sobrenome', '').strip()
        cpf = request.form.get('cpf', '').strip()
        telefone = request.form.get('telefone', '').strip()
        evento_id = request.form.get('evento_id')
        
        if not (nome and sobrenome and cpf and telefone):
            return jsonify(success=False, message="Preencha todos os campos"), 400
        
        evento = None
        if evento_id:
            evento = Evento.query.get(evento_id)
            if not evento or evento.status != 'Aberto':
                return jsonify(success=False, message="Evento não encontrado ou inscrições encerradas"), 400
        
        # Verificar se já existe inscrição com este CPF para o mesmo evento
        existing_reg = Registration.query.filter_by(cpf=cpf, evento_id=evento_id).first()
        if existing_reg:
            return jsonify(success=False, message="Já existe uma inscrição com este CPF para este evento"), 400
        
        reg = Registration(
            nome=nome, 
            sobrenome=sobrenome, 
            cpf=cpf, 
            telefone=telefone, 
            evento_id=evento_id,
            status_inscricao="Pré-inscrito"
        )
        db.session.add(reg)
        db.session.commit()
        
        return jsonify(success=True, inscricao_id=reg.id)
    
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, message="Erro interno do servidor"), 500

@app.route('/upload_comprovante', methods=['POST'])
def upload_comprovante():
    try:
        inscricao_id = request.form.get('pre_inscricao_id')
        comprovante = request.files.get('comprovante')
        
        if not inscricao_id:
            return jsonify(success=False, message="ID da inscrição não fornecido"), 400
        
        if not comprovante or comprovante.filename == '':
            return jsonify(success=False, message="Nenhum arquivo selecionado"), 400
        
        if not allowed_file(comprovante.filename):
            return jsonify(success=False, message="Tipo de arquivo não permitido"), 400
        
        # Verificar tamanho do arquivo (limite de 5MB)
        comprovante.seek(0, 2)  # Ir para o final do arquivo
        file_size = comprovante.tell()
        comprovante.seek(0)  # Voltar para o início
        if file_size > 5 * 1024 * 1024:  # 5MB
            return jsonify(success=False, message="Arquivo muito grande. Tamanho máximo: 5MB"), 400
        
        reg = Registration.query.get(inscricao_id)
        if not reg:
            return jsonify(success=False, message="Inscrição não encontrada"), 404
        
        # Salvar o comprovante
        filename = save_uploaded_file(comprovante)
        reg.comprovante_filename = filename
        db.session.commit()
        
        return jsonify(success=True)
    
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, message="Erro interno do servidor"), 500

@app.route('/confirm_payment', methods=['POST'])
def confirm_payment():
    data = request.get_json()
    reg_id = data.get('reg_id')
    reg = Registration.query.get(reg_id)
    if not reg:
        return jsonify(success=False), 404
    reg.paid = True
    db.session.commit()
    return jsonify(success=True, nome=reg.nome + " " + reg.sobrenome, cpf=reg.cpf, whatsapp=WHATSAPP_NUMBER)

@app.route('/print_confirmation/<int:reg_id>')
def print_confirmation(reg_id):
    reg = Registration.query.get_or_404(reg_id)
    evento = Evento.query.get(reg.evento_id) if reg.evento_id else None
    valor_inscricao = evento.valor_inscricao if evento else PAYMENT_AMOUNT
    qr_code_url = get_qr_code_url(valor_inscricao)
    event_title = evento.titulo if evento else "Conferência de Mulheres"
    
    return render_template_string(print_tpl,
                                  reg=reg,
                                  payment_amount=valor_inscricao,
                                  pix_key=PIX_KEY,
                                  event_title=event_title,
                                  qr_code_url=qr_code_url)

# ---------------- Evento page ----------------
@app.route('/evento/<int:evento_id>')
def ver_evento(evento_id):
    ev = Evento.query.get_or_404(evento_id)
    photos = ev.fotos
    gallery_html = f"""
      <h2 style="color:var(--terra-1)">{ev.titulo} <small class="text-muted">({ev.status})</small></h2>
      <p><strong>Data:</strong> {ev.data or ''} <strong>Horário:</strong> {ev.horario or ''}</p>
      <p><strong>Local:</strong> {ev.local or ''}</p>
      <p><strong>Valor da inscrição:</strong> R$ {ev.valor_inscricao or PAYMENT_AMOUNT}</p>
      <p>{ev.descricao or ''}</p>
      <hr />
    """
    if ev.status == 'Aberto':
        gallery_html += "<div class='alert alert-info'>Inscrições abertas.</div>"
        gallery_html += f"<a class='btn btn-terra mb-3' href='/inscricao/{ev.id}'>Inscrever-se</a>"
    else:
        gallery_html += "<div class='alert alert-secondary'>Evento encerrado. Agradecimento:</div>"
        if ev.agradecimento:
            gallery_html += f"<div class='p-3 mb-3' style='background:#f6eadf;border-radius:8px'>{ev.agradecimento}</div>"

    gallery_html += "<div class='row mt-4'>"
    if not photos:
        gallery_html += "<div class='col-12'><p>Nenhuma foto cadastrada para este evento.</p></div>"
    else:
        for p in photos:
            gallery_html += f"""
            <div class="col-md-4 mb-3 animate-fade-in-up">
              <div class="card event-card">
                <img src="/static/uploads/{p.filename}" class="img-fluid" style="height:220px;object-fit:cover;border-radius:8px" />
                <div class="card-body">
                  <p>{p.comentario or ''}</p>
                </div>
              </div>
            </div>
            """
    gallery_html += "</div>"
    return render_template_string(base_css_js.replace("{{ content|safe }}", gallery_html),
                                  whatsapp_number=WHATSAPP_NUMBER,
                                  scripts="")

# ---------------- Workshop page ----------------
@app.route('/workshop/<int:workshop_id>')
def ver_workshop(workshop_id):
    wk = Workshop.query.get_or_404(workshop_id)
    html = f"""
      <h2 style="color:var(--terra-1)">{wk.titulo} <small class="text-muted">({wk.status})</small></h2>
      <p><strong>Data:</strong> {wk.data or ''} <strong>Horário:</strong> {wk.horario or ''}</p>
      <p><strong>Local:</strong> {wk.local or ''}</p>
      <h4>Abordagem</h4>
      <p>{wk.abordagem or 'Em breve'}</p>
    """
    return render_template_string(base_css_js.replace("{{ content|safe }}", html),
                                  whatsapp_number=WHATSAPP_NUMBER,
                                  scripts="")

# ---------------- ADMIN Routes (PROTEGIDAS) ----------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_logged'):
        return redirect(url_for('admin_dashboard'))
        
    if request.method == 'POST':
        pwd = request.form.get('password', '')
        if pwd == ADMIN_PASSWORD:
            session['admin_logged'] = True
            session.permanent = True
            flash("Acesso concedido.", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Senha incorreta.", "danger")
            return redirect(url_for('admin_login'))
    
    content = """
      <h2 style="color:var(--terra-1)">Área do Administrador</h2>
      <div class="card p-4">
        <form method="POST">
          <div class="mb-3">
            <label class="form-label">Senha</label>
            <input name="password" type="password" class="form-control" required>
          </div>
          <button class="btn btn-terra">Entrar</button>
        </form>
      </div>
    """
    return render_template_string(base_css_js.replace("{{ content|safe }}", content),
                                  whatsapp_number=WHATSAPP_NUMBER,
                                  scripts="")

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged', None)
    flash("Desconectado.", "info")
    return redirect(url_for('index'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    open_events = Evento.query.filter_by(status='Aberto').order_by(Evento.created_at.desc()).all()
    
    content = """
      <h2 style="color:var(--terra-1)">Painel do Administrador</h2>
      <div class="row">
        <div class="col-md-4">
          <div class="card p-3 mb-3 event-card">
            <h5>Novo Evento</h5>
            <p>Cadastrar novo evento (será Aberto por padrão).</p>
            <a class="btn btn-terra" href="/admin/evento/novo">Criar Evento</a>
          </div>
        </div>
        <div class="col-md-4">
          <div class="card p-3 mb-3 event-card">
            <h5>Ajuste de Evento</h5>
            <p>Fechar evento (adicionar fotos e agradecimento).</p>
            <a class="btn btn-terra" href="/admin/evento/ajuste">Ajustar Evento</a>
          </div>
        </div>
        <div class="col-md-4">
          <div class="card p-3 mb-3 event-card">
            <h5>Novo Workshop</h5>
            <p>Cadastrar workshop (status inicial: Em Breve).</p>
            <a class="btn btn-terra" href="/admin/workshop/novo">Criar Workshop</a>
          </div>
        </div>
        <div class="col-md-4">
          <div class="card p-3 mb-3 event-card">
            <h5>Excluir Evento/Workshop</h5>
            <p>Excluir eventos ou workshops existentes.</p>
            <a class="btn btn-terra" href="/admin/excluir">Gerenciar Exclusões</a>
          </div>
        </div>
        <div class="col-md-4">
          <div class="card p-3 mb-3 event-card">
            <h5>Participantes</h5>
            <p>Visualizar lista de participantes confirmados.</p>
            <a class="btn btn-terra" href="/admin/participantes">Ver Participantes</a>
          </div>
        </div>
        <div class="col-md-4">
          <div class="card p-3 mb-3 event-card">
            <h5>Pré-Inscrições</h5>
            <p>Gerenciar pré-inscrições e confirmar pagamentos.</p>
            <a class="btn btn-terra" href="/admin/pre_inscricoes">Ver Pré-Inscrições</a>
          </div>
        </div>
      </div>
      <hr />
      <h4>Eventos Abertos</h4>
      <div class="row">
    """

    if not open_events:
        content += "<div class='col-12'><p>Sem eventos abertos.</p></div>"
    else:
        for ev in open_events:
            content += f"""
            <div class="col-md-6 mb-3 animate-fade-in-up">
              <div class="card p-2 event-card">
                <h5>{ev.titulo}</h5>
                <p>{ev.data or ''} - {ev.horario or ''}</p>
                <p><strong>Valor da inscrição:</strong> R$ {ev.valor_inscricao or PAYMENT_AMOUNT}</p>
                <div>
                  <a class="btn btn-sm btn-outline-terra" href="/evento/{ev.id}">Ver</a>
                  <a class="btn btn-sm btn-terra" href="/admin/evento/{ev.id}/fechar">Fechar Evento</a>
                </div>
              </div>
            </div>
            """
    content += "</div>"
    return render_template_string(base_css_js.replace("{{ content|safe }}", content),
                                  whatsapp_number=WHATSAPP_NUMBER,
                                  scripts="")

# ---------------- NOVA ROTA: ADMIN - Lista de Pré-Inscrições ----------------
@app.route('/admin/pre_inscricoes')
@admin_required
def admin_pre_inscricoes():
    pre_inscricoes = Registration.query.order_by(Registration.created_at.desc()).all()
    
    content = """
      <h2 style="color:var(--terra-1)">Lista de Pré-Inscrições</h2>
      <div class="card">
        <div class="card-body">
    """
    
    if not pre_inscricoes:
        content += """
          <div class="text-center py-4">
            <h5>Nenhuma pré-inscrição encontrada</h5>
            <p class="text-muted">As pré-inscrições aparecerão aqui quando os usuários se inscreverem.</p>
          </div>
        """
    else:
        content += """
          <div class="table-responsive">
            <table class="table table-striped table-hover">
              <thead class="table-dark">
                <tr>
                  <th>Nome Completo</th>
                  <th>CPF</th>
                  <th>Telefone</th>
                  <th>Evento</th>
                  <th>Status</th>
                  <th>Comprovante</th>
                  <th>Pagamento Confirmado</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
        """
        
        for inscricao in pre_inscricoes:
            evento_nome = inscricao.evento.titulo if inscricao.evento and inscricao.evento.titulo else "Não Especificado"
            status_class = "status-confirmado" if inscricao.status_inscricao == "Inscrição Confirmada" else "status-preinscrito"
            
            comprovante_html = "Não enviado"
            if inscricao.comprovante_filename:
                comprovante_url = f"/static/uploads/{inscricao.comprovante_filename}"
                comprovante_html = f'<a href="{comprovante_url}" target="_blank" class="btn btn-sm btn-outline-primary">Ver Comprovante</a>'
            
            checkbox_html = f"""
            <input type="checkbox" class="form-check-input confirm-pagamento" 
                   data-inscricao-id="{inscricao.id}" 
                   {'checked' if inscricao.status_inscricao == 'Inscrição Confirmada' else ''}>
            """
            
            # ✅ MENSAGEM DO WHATSAPP MELHORADA
            nome_evento = evento_nome if evento_nome != "Não Especificado" else "Conferência de Mulheres"
            mensagem_whatsapp = f"""🎉 Parabéns! Sua inscrição foi confirmada com sucesso.

Você agora faz parte da {nome_evento} ✨

Prepare o coração, pois será um tempo especial de renovação, comunhão e presença de Deus.

Nos vemos em breve! 💜"""
            
            whatsapp_link = f"https://wa.me/55{inscricao.telefone.replace(' ', '').replace('(', '').replace(')', '').replace('-', '')}"
            whatsapp_url = f"{whatsapp_link}?text={mensagem_whatsapp.replace(chr(10), '%0A')}"
            
            acoes_html = f"""
            <div class="btn-group-vertical" role="group">
                <a href="{whatsapp_url}" target="_blank" class="btn btn-sm btn-success {'disabled' if inscricao.status_inscricao != 'Inscrição Confirmada' else ''}">
                    <i class="fab fa-whatsapp"></i> Enviar Mensagem
                </a>
                <button class="btn btn-sm btn-danger excluir-participante" data-inscricao-id="{inscricao.id}" data-nome="{inscricao.nome} {inscricao.sobrenome}">
                    <i class="fas fa-trash"></i> Excluir
                </button>
            </div>
            """
            
            content += f"""
                <tr>
                  <td>{inscricao.nome} {inscricao.sobrenome}</td>
                  <td>{inscricao.cpf}</td>
                  <td>{inscricao.telefone}</td>
                  <td>{evento_nome}</td>
                  <td><span class="badge {status_class}">{inscricao.status_inscricao}</span></td>
                  <td>{comprovante_html}</td>
                  <td>{checkbox_html}</td>
                  <td>{acoes_html}</td>
                </tr>
            """
        
        content += """
              </tbody>
            </table>
          </div>
        """
    
    content += """
        </div>
      </div>
      
      <div class="mt-3">
        <a href="/admin" class="btn btn-terra">
          <i class="fas fa-arrow-left me-1"></i> Voltar para Área do Administrador
        </a>
      </div>
    """
    
    scripts = """
    <script>
      document.addEventListener('DOMContentLoaded', function() {
        // ✅ CONFIRMAR PAGAMENTO
        const checkboxes = document.querySelectorAll('.confirm-pagamento');
        
        checkboxes.forEach(checkbox => {
          checkbox.addEventListener('change', function() {
            const inscricaoId = this.getAttribute('data-inscricao-id');
            const isConfirmed = this.checked;
            
            fetch('/admin/confirmar_pagamento', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                inscricao_id: inscricaoId,
                confirmado: isConfirmed
              })
            })
            .then(response => response.json())
            .then(data => {
              if (data.success) {
                location.reload();
              } else {
                alert('Erro ao confirmar pagamento: ' + data.message);
                this.checked = !isConfirmed;
              }
            })
            .catch(error => {
              console.error('Error:', error);
              alert('Erro ao confirmar pagamento');
              this.checked = !isConfirmed;
            });
          });
        });

        // ✅ EXCLUIR PARTICIPANTE
        const botoesExcluir = document.querySelectorAll('.excluir-participante');
        
        botoesExcluir.forEach(botao => {
          botao.addEventListener('click', function() {
            const inscricaoId = this.getAttribute('data-inscricao-id');
            const nomeParticipante = this.getAttribute('data-nome');
            
            if (confirm(`ATENÇÃO! Tem certeza que deseja excluir permanentemente a inscrição de ${nomeParticipante}?\\n\\nEsta ação não pode ser desfeita!`)) {
              fetch('/admin/excluir_participante', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                  inscricao_id: inscricaoId
                })
              })
              .then(response => response.json())
              .then(data => {
                if (data.success) {
                  alert('Participante excluído com sucesso!');
                  location.reload();
                } else {
                  alert('Erro ao excluir participante: ' + data.message);
                }
              })
              .catch(error => {
                console.error('Error:', error);
                alert('Erro ao excluir participante');
              });
            }
          });
        });
      });
    </script>
    """
    
    return render_template_string(base_css_js.replace("{{ content|safe }}", content),
                                  whatsapp_number=WHATSAPP_NUMBER,
                                  scripts=scripts)

# ---------------- NOVA ROTA: ADMIN - Confirmar Pagamento ----------------
@app.route('/admin/confirmar_pagamento', methods=['POST'])
@admin_required
def admin_confirmar_pagamento():
    try:
        data = request.get_json()
        inscricao_id = data.get('inscricao_id')
        confirmado = data.get('confirmado')
        
        if not inscricao_id:
            return jsonify(success=False, message="ID da inscrição não fornecido"), 400
        
        inscricao = Registration.query.get(inscricao_id)
        if not inscricao:
            return jsonify(success=False, message="Inscrição não encontrada"), 404
        
        if confirmado:
            inscricao.status_inscricao = "Inscrição Confirmada"
            inscricao.paid = True
            flash(f"Pagamento confirmado para {inscricao.nome} {inscricao.sobrenome}", "success")
        else:
            inscricao.status_inscricao = "Pré-inscrito"
            inscricao.paid = False
            flash(f"Status revertido para pré-inscrição para {inscricao.nome} {inscricao.sobrenome}", "info")
        
        db.session.commit()
        
        return jsonify(success=True)
    
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, message="Erro interno do servidor"), 500

# ---------------- NOVA ROTA: EXCLUIR PARTICIPANTE ----------------
@app.route('/admin/excluir_participante', methods=['POST'])
@admin_required
def admin_excluir_participante():
    try:
        data = request.get_json()
        inscricao_id = data.get('inscricao_id')
        
        if not inscricao_id:
            return jsonify(success=False, message="ID da inscrição não fornecido"), 400
        
        inscricao = Registration.query.get(inscricao_id)
        if not inscricao:
            return jsonify(success=False, message="Inscrição não encontrada"), 404
        
        nome_participante = f"{inscricao.nome} {inscricao.sobrenome}"
        
        # Excluir o participante
        db.session.delete(inscricao)
        db.session.commit()
        
        flash(f"Participante {nome_participante} excluído com sucesso!", "success")
        return jsonify(success=True)
    
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, message="Erro interno do servidor"), 500

# ---------------- Admin: Novo Evento ----------------
@app.route('/admin/evento/novo', methods=['GET', 'POST'])
@admin_required
def admin_novo_evento():
    if request.method == 'POST':
        titulo = request.form.get('titulo', '').strip()
        data = request.form.get('data', '').strip()
        horario = request.form.get('horario', '').strip()
        local = request.form.get('local', '').strip()
        descricao = request.form.get('descricao', '').strip()
        valor_inscricao = request.form.get('valor_inscricao', '10.00').strip()
        
        if not titulo:
            flash("Título obrigatório.", "danger")
            return redirect(url_for('admin_novo_evento'))
        
        ev = Evento(
            titulo=titulo, 
            data=data, 
            horario=horario, 
            local=local, 
            descricao=descricao, 
            valor_inscricao=valor_inscricao, 
            status='Aberto'
        )
        db.session.add(ev)
        db.session.commit()
        flash("Evento criado com sucesso!", "success")
        return redirect(url_for('admin_dashboard'))
    
    content = """
      <h3 style="color:var(--terra-1)">Novo Evento</h3>
      <div class="card p-3">
        <form method="POST">
          <div class="mb-2">
            <label class="form-label">Título do Evento *</label>
            <input name="titulo" class="form-control" required placeholder="Ex: Conferência de Mulheres 2025">
          </div>
          <div class="mb-2">
            <label class="form-label">Data</label>
            <input name="data" type="date" class="form-control" placeholder="DD/MM/AAAA">
          </div>
          <div class="mb-2">
            <label class="form-label">Horário</label>
            <input name="horario" class="form-control" placeholder="Ex: 16h às 21h">
          </div>
          <div class="mb-2">
            <label class="form-label">Local</label>
            <input name="local" class="form-control" placeholder="Local do evento">
          </div>
          <div class="mb-2">
            <label class="form-label">Valor da Inscrição (R$) *</label>
            <input name="valor_inscricao" type="number" step="0.01" class="form-control" value="10.00" required>
          </div>
          <div class="mb-2">
            <label class="form-label">Descrição</label>
            <textarea name="descricao" class="form-control" rows="4" placeholder="Descrição detalhada do evento..."></textarea>
          </div>
          <button class="btn btn-terra">Criar Evento</button>
          <a href="/admin" class="btn btn-secondary ms-2">Cancelar</a>
        </form>
      </div>
    """
    return render_template_string(base_css_js.replace("{{ content|safe }}", content),
                                  whatsapp_number=WHATSAPP_NUMBER,
                                  scripts="")

# ---------------- Admin: Ajuste de Evento (lista / fechar) ----------------
@app.route('/admin/evento/ajuste', methods=['GET'])
@admin_required
def admin_ajuste_evento():
    open_events = Evento.query.filter_by(status='Aberto').order_by(Evento.created_at.desc()).all()
    content = "<h3 style='color:var(--terra-1)'>Ajuste de Evento (Fechar)</h3>"
    
    if not open_events:
        content += """
        <div class='card p-4 text-center'>
            <h5>Nenhum evento aberto para ajuste</h5>
            <p>Todos os eventos estão fechados ou não há eventos cadastrados.</p>
            <a href="/admin/evento/novo" class="btn btn-terra">Criar Novo Evento</a>
        </div>
        """
    else:
        content += "<div class='row'>"
        for ev in open_events:
            content += f"""
            <div class='col-md-6 mb-3 animate-fade-in-up'>
              <div class='card p-3 event-card'>
                <h5>{ev.titulo}</h5>
                <p><strong>Data:</strong> {ev.data or 'Não definida'}</p>
                <p><strong>Horário:</strong> {ev.horario or 'Não definido'}</p>
                <p><strong>Local:</strong> {ev.local or 'Não definido'}</p>
                <p><strong>Valor da inscrição:</strong> R$ {ev.valor_inscricao or PAYMENT_AMOUNT}</p>
                <p class='text-muted'>{ (ev.descricao or 'Sem descrição')[:100] }...</p>
                <a class='btn btn-terra' href='/admin/evento/{ev.id}/fechar'>Fechar Evento (adicionar fotos/agradecimento)</a>
              </div>
            </div>
            """
        content += "</div>"
    
    return render_template_string(base_css_js.replace("{{ content|safe }}", content),
                                  whatsapp_number=WHATSAPP_NUMBER,
                                  scripts="")

@app.route('/admin/evento/<int:evento_id>/fechar', methods=['GET', 'POST'])
@admin_required
def admin_ajuste_evento_closing(evento_id):
    ev = Evento.query.get_or_404(evento_id)
    
    if ev.status == 'Fechado':
        flash("Este evento já está fechado.", "warning")
        return redirect(url_for('admin_ajuste_evento'))
    
    if request.method == 'POST':
        files = request.files.getlist('fotos')
        agradecimento = request.form.get('agradecimento', '').strip()
        comentario_geral = request.form.get('comentario', '').strip()
        
        valid_files = [f for f in files if f and allowed_file(f.filename)]
        
        if len(valid_files) < 5:
            flash("Para fechar o evento é necessário enviar no mínimo 5 fotos.", "danger")
            return redirect(url_for('admin_ajuste_evento_closing', evento_id=evento_id))
        
        if not agradecimento:
            flash("O texto de agradecimento é obrigatório.", "danger")
            return redirect(url_for('admin_ajuste_evento_closing', evento_id=evento_id))
        
        saved_files = []
        for f in valid_files:
            try:
                fname = save_uploaded_file(f)
                fe = FotoEvento(
                    evento_id=evento_id, 
                    filename=fname, 
                    comentario=comentario_geral
                )
                db.session.add(fe)
                saved_files.append(fname)
            except Exception as e:
                flash(f"Erro ao salvar arquivo {f.filename}: {str(e)}", "danger")
                continue
        
        ev.status = 'Fechado'
        ev.agradecimento = agradecimento
        db.session.commit()
        
        flash(f"Evento '{ev.titulo}' fechado com sucesso! {len(saved_files)} fotos adicionadas.", "success")
        return redirect(url_for('admin_dashboard'))

    content = f"""
      <h3 style="color:var(--terra-1)">Fechar Evento: {ev.titulo}</h3>
      <div class="card p-3">
        <form method="POST" enctype="multipart/form-data">
          <div class="alert alert-info">
            <h6>Instruções para fechar o evento:</h6>
            <ul class="mb-0">
              <li>Selecione no mínimo 5 fotos do evento</li>
              <li>Escreva uma mensagem de agradecimento para os participantes</li>
              <li>Após o fechamento, o evento aparecerá como "Encerrado" para o público</li>
            </ul>
          </div>
          
          <div class="mb-3">
            <label class="form-label">Fotos do Evento (Mínimo 5) *</label>
            <input type="file" name="fotos" multiple class="form-control" accept="image/*" required>
            <small class="text-muted">Selecione várias fotos mantendo a tecla CTRL pressionada</small>
          </div>
          
          <div class="mb-3">
            <label class="form-label">Comentário para as fotos (opcional)</label>
            <textarea name="comentario" class="form-control" rows="2" placeholder="Ex: Momentos especiais do nosso encontro..."></textarea>
          </div>
          
          <div class="mb-3">
            <label class="form-label">Mensagem de Agradecimento *</label>
            <textarea name="agradecimento" class="form-control" rows="5" required placeholder="Escreva uma mensagem especial de agradecimento para os participantes..."></textarea>
            <small class="text-muted">Esta mensagem será exibida na página do evento após o fechamento</small>
          </div>
          
          <div class="d-flex gap-2">
            <button type="submit" class="btn btn-terra">Fechar Evento e Salvar Fotos</button>
            <a href="/admin/evento/ajuste" class="btn btn-secondary">Cancelar</a>
          </div>
        </form>
      </div>
    """
    return render_template_string(base_css_js.replace("{{ content|safe }}", content),
                                  whatsapp_number=WHATSAPP_NUMBER,
                                  scripts="")

# ---------------- Admin: Novo Workshop ----------------
@app.route('/admin/workshop/novo', methods=['GET', 'POST'])
@admin_required
def admin_novo_workshop():
    if request.method == 'POST':
        titulo = request.form.get('titulo', '').strip()
        data = request.form.get('data', '').strip()
        horario = request.form.get('horario', '').strip()
        local = request.form.get('local', '').strip()
        abordagem = request.form.get('abordagem', '').strip()
        
        if not titulo:
            flash("Título obrigatório.", "danger")
            return redirect(url_for('admin_novo_workshop'))
        
        wk = Workshop(
            titulo=titulo, 
            data=data, 
            horario=horario, 
            local=local, 
            abordagem=abordagem, 
            status='Em Breve'
        )
        db.session.add(wk)
        db.session.commit()
        flash("Workshop criado com sucesso! (Status: Em Breve)", "success")
        return redirect(url_for('admin_dashboard'))
    
    content = """
      <h3 style="color:var(--terra-1)">Novo Workshop</h3>
      <div class="card p-3">
        <form method="POST">
          <div class="mb-2">
            <label class="form-label">Título do Workshop *</label>
            <input name="titulo" class="form-control" required placeholder="Ex: Workshop de Autoconhecimento">
          </div>
          <div class="mb-2">
            <label class="form-label">Data</label>
            <input name="data" type="date" class="form-control">
          </div>
          <div class="mb-2">
            <label class="form-label">Horário</label>
            <input name="horario" class="form-control" placeholder="Ex: 14h às 17h">
          </div>
          <div class="mb-2">
            <label class="form-label">Local</label>
            <input name="local" class="form-control" placeholder="Local do workshop">
          </div>
          <div class="mb-2">
            <label class="form-label">Abordagem/Descrição</label>
            <textarea name="abordagem" class="form-control" rows="4" placeholder="Descreva a abordagem e conteúdo do workshop..."></textarea>
          </div>
          <button class="btn btn-terra">Criar Workshop</button>
          <a href="/admin" class="btn btn-secondary ms-2">Cancelar</a>
        </form>
      </div>
    """
    return render_template_string(base_css_js.replace("{{ content|safe }}", content),
                                  whatsapp_number=WHATSAPP_NUMBER,
                                  scripts="")

# ---------------- Admin: Excluir Eventos/Workshops ----------------
@app.route('/admin/excluir', methods=['GET', 'POST'])
@admin_required
def admin_excluir():
    if request.method == 'POST':
        tipo = request.form.get('tipo')
        id_item = request.form.get('id')
        
        if tipo == 'evento':
            evento = Evento.query.get(id_item)
            if evento:
                FotoEvento.query.filter_by(evento_id=id_item).delete()
                Registration.query.filter_by(evento_id=id_item).delete()
                db.session.delete(evento)
                db.session.commit()
                flash("Evento excluído com sucesso!", "success")
            else:
                flash("Evento não encontrado.", "danger")
                
        elif tipo == 'workshop':
            workshop = Workshop.query.get(id_item)
            if workshop:
                db.session.delete(workshop)
                db.session.commit()
                flash("Workshop excluído com sucesso!", "success")
            else:
                flash("Workshop não encontrado.", "danger")
        
        return redirect(url_for('admin_excluir'))
    
    eventos = Evento.query.order_by(Evento.created_at.desc()).all()
    workshops = Workshop.query.order_by(Workshop.created_at.desc()).all()
    
    content = """
      <h3 style="color:var(--terra-1)">Excluir Eventos/Workshops</h3>
      <div class="alert alert-warning">
        <strong><i class="fas fa-exclamation-triangle me-2"></i>Atenção:</strong> Esta ação é irreversível. 
        Todos os dados do evento/workshop (incluindo fotos e inscrições) serão permanentemente excluídos.
      </div>
      
      <div class="row">
        <div class="col-md-6">
          <h4>Eventos</h4>
    """
    
    if not eventos:
        content += """
          <div class="card p-4 text-center">
            <p class="mb-0">Nenhum evento cadastrado.</p>
          </div>
        """
    else:
        for evento in eventos:
            num_fotos = len(evento.fotos)
            num_inscricoes = len(evento.inscricoes)
            content += f"""
            <div class="card mb-3 animate-fade-in-up">
              <div class="card-body">
                <h5>{evento.titulo}</h5>
                <p><strong>Status:</strong> <span class="badge bg-{'success' if evento.status=='Aberto' else 'secondary'}">{evento.status}</span></p>
                <p><strong>Data:</strong> {evento.data or 'Não definida'}</p>
                <p><strong>Fotos:</strong> {num_fotos} | <strong>Inscrições:</strong> {num_inscricoes}</p>
                <form method="POST" onsubmit="return confirm('ATENÇÃO: Esta ação excluirá permanentemente o evento, {num_fotos} fotos e {num_inscricoes} inscrições. Tem certeza?');">
                  <input type="hidden" name="tipo" value="evento">
                  <input type="hidden" name="id" value="{evento.id}">
                  <button type="submit" class="btn btn-danger btn-sm">
                    <i class="fas fa-trash me-1"></i> Excluir Evento
                  </button>
                </form>
              </div>
            </div>
            """
    
    content += """
        </div>
        <div class="col-md-6">
          <h4>Workshops</h4>
    """
    
    if not workshops:
        content += """
          <div class="card p-4 text-center">
            <p class="mb-0">Nenhum workshop cadastrado.</p>
          </div>
        """
    else:
        for workshop in workshops:
            content += f"""
            <div class="card mb-3 animate-fade-in-up">
              <div class="card-body">
                <h5>{workshop.titulo}</h5>
                <p><strong>Status:</strong> <span class="badge bg-{'warning' if workshop.status=='Em Breve' else 'success'}">{workshop.status}</span></p>
                <p><strong>Data:</strong> {workshop.data or 'Não definida'}</p>
                <form method="POST" onsubmit="return confirm('Tem certeza que deseja excluir permanentemente este workshop?');">
                  <input type="hidden" name="tipo" value="workshop">
                  <input type="hidden" name="id" value="{workshop.id}">
                  <button type="submit" class="btn btn-danger btn-sm">
                    <i class="fas fa-trash me-1"></i> Excluir Workshop
                  </button>
                </form>
              </div>
            </div>
            """
    
    content += """
        </div>
      </div>
      
      <div class="mt-4">
        <a href="/admin" class="btn btn-terra">
          <i class="fas fa-arrow-left me-1"></i> Voltar ao Painel
        </a>
      </div>
    """
    
    return render_template_string(base_css_js.replace("{{ content|safe }}", content),
                                  whatsapp_number=WHATSAPP_NUMBER,
                                  scripts="")

# ---------------- Admin: Lista de Participantes ----------------
@app.route('/admin/participantes')
@admin_required
def admin_participantes():
    participantes = Registration.query.filter_by(status_inscricao="Inscrição Confirmada").order_by(Registration.created_at.desc()).all()
    total_confirmados = len(participantes)
    
    eventos_com_inscricoes = {}
    for p in participantes:
        if p.evento_id:
            evento_titulo = p.evento.titulo if p.evento else "Evento Não Especificado"
            if evento_titulo not in eventos_com_inscricoes:
                eventos_com_inscricoes[evento_titulo] = 0
            eventos_com_inscricoes[evento_titulo] += 1
    
    content = f"""
      <h3 style="color:var(--terra-1)">Lista de Participantes Confirmados</h3>
      
      <div class="row mb-4">
        <div class="col-md-6">
          <div class="card bg-success text-white">
            <div class="card-body text-center">
              <h4>{total_confirmados}</h4>
              <p class="mb-0">Total de Confirmados</p>
            </div>
          </div>
        </div>
        <div class="col-md-6">
          <div class="card bg-primary text-white">
            <div class="card-body">
              <h6>Distribuição por Evento:</h6>
              {"".join([f'<small>{evento}: {qtd}</small><br>' for evento, qtd in eventos_com_inscricoes.items()]) or "<small>Nenhum evento específico</small>"}
            </div>
          </div>
        </div>
      </div>
      
      <div class="mb-3">
        <a href="/admin/exportar_participantes" class="btn btn-terra">
          <i class="fas fa-download me-2"></i> Exportar Lista (CSV)
        </a>
      </div>
      
      <div class="card">
        <div class="card-body">
    """
    
    if not participantes:
        content += """
          <div class="text-center py-4">
            <h5>Nenhum participante confirmado ainda</h5>
            <p class="text-muted">Os participantes aparecerão aqui após confirmarem o pagamento.</p>
          </div>
        """
    else:
        content += """
          <div class="table-responsive">
            <table class="table table-striped table-hover">
              <thead class="table-dark">
                <tr>
                  <th>Nome Completo</th>
                  <th>CPF</th>
                  <th>Telefone</th>
                  <th>Evento</th>
                  <th>Data de Inscrição</th>
                </tr>
              </thead>
              <tbody>
        """
        
        for p in participantes:
            evento_nome = p.evento.titulo if p.evento and p.evento.titulo else "Não Especificado"
            content += f"""
                <tr>
                  <td>{p.nome} {p.sobrenome}</td>
                  <td>{p.cpf}</td>
                  <td>{p.telefone}</td>
                  <td>{evento_nome}</td>
                  <td>{p.created_at.strftime('%d/%m/%Y %H:%M')}</td>
                </tr>
            """
        
        content += """
              </tbody>
            </table>
          </div>
        """
    
    content += """
        </div>
      </div>
      
      <div class="mt-3">
        <a href="/admin" class="btn btn-terra">
          <i class="fas fa-arrow-left me-1"></i> Voltar para Área do Administrador
        </a>
      </div>
    """
    
    return render_template_string(base_css_js.replace("{{ content|safe }}", content),
                                  whatsapp_number=WHATSAPP_NUMBER,
                                  scripts="")

# ---------------- Admin: Exportar participantes para CSV ----------------
@app.route('/admin/exportar_participantes')
@admin_required
def exportar_participantes():
    import csv
    from io import StringIO
    
    participantes = Registration.query.filter_by(status_inscricao="Inscrição Confirmada").order_by(Registration.created_at).all()
    
    si = StringIO()
    cw = csv.writer(si, delimiter=';')
    cw.writerow(['Nome', 'Sobrenome', 'CPF', 'Telefone', 'Evento', 'Data de Inscrição'])
    
    for p in participantes:
        evento_nome = p.evento.titulo if p.evento and p.evento.titulo else "Não Especificado"
        cw.writerow([
            p.nome, 
            p.sobrenome, 
            p.cpf, 
            p.telefone, 
            evento_nome, 
            p.created_at.strftime('%d/%m/%Y %H:%M')
        ])
    
    output = si.getvalue()
    si.close()
    
    from datetime import datetime
    filename = f"participantes_confirmados_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    
    return send_file(
        BytesIO(output.encode('utf-8-sig')),
        mimetype='text/csv; charset=utf-8-sig',
        as_attachment=True,
        download_name=filename
    )

# ---------------- Admin: Editar Workshop ----------------
@app.route('/admin/workshop/<int:workshop_id>/editar', methods=['GET', 'POST'])
@admin_required
def admin_editar_workshop(workshop_id):
    wk = Workshop.query.get_or_404(workshop_id)
    
    if request.method == 'POST':
        wk.titulo = request.form.get('titulo', wk.titulo).strip()
        wk.data = request.form.get('data', wk.data).strip()
        wk.horario = request.form.get('horario', wk.horario).strip()
        wk.local = request.form.get('local', wk.local).strip()
        wk.abordagem = request.form.get('abordagem', wk.abordagem).strip()
        wk.status = request.form.get('status', wk.status)
        
        if not wk.titulo:
            flash("Título é obrigatório.", "danger")
            return redirect(url_for('admin_editar_workshop', workshop_id=workshop_id))
        
        db.session.commit()
        flash("Workshop atualizado com sucesso!", "success")
        return redirect(url_for('admin_dashboard'))
    
    content = f"""
      <h3 style="color:var(--terra-1)">Editar Workshop</h3>
      
      <div class="card p-3">
        <form method="POST">
          <div class="mb-3">
            <label class="form-label">Título do Workshop *</label>
            <input name="titulo" class="form-control" value="{wk.titulo}" required>
          </div>
          
          <div class="row">
            <div class="col-md-4">
              <div class="mb-3">
                <label class="form-label">Data</label>
                <input name="data" type="date" class="form-control" value="{wk.data or ''}">
              </div>
            </div>
            <div class="col-md-4">
              <div class="mb-3">
                <label class="form-label">Horário</label>
                <input name="horario" class="form-control" value="{wk.horario or ''}" placeholder="Ex: 14h às 17h">
              </div>
            </div>
            <div class="col-md-4">
              <div class="mb-3">
                <label class="form-label">Status</label>
                <select name="status" class="form-control">
                  <option value="Em Breve" {"selected" if wk.status=="Em Breve" else ""}>Em Breve</option>
                  <option value="Aberto" {"selected" if wk.status=="Aberto" else ""}>Aberto</option>
                </select>
              </div>
            </div>
          </div>
          
          <div class="mb-3">
            <label class="form-label">Local</label>
            <input name="local" class="form-control" value="{wk.local or ''}">
          </div>
          
          <div class="mb-3">
            <label class="form-label">Abordagem/Descrição</label>
            <textarea name="abordagem" class="form-control" rows="5">{wk.abordagem or ''}</textarea>
          </div>
          
          <div class="d-flex gap-2">
            <button type="submit" class="btn btn-terra">
              <i class="fas fa-save me-1"></i> Salvar Alterações
            </button>
            <a href="/admin" class="btn btn-secondary">Cancelar</a>
            <a href="/workshop/{workshop_id}" target="_blank" class="btn btn-outline-primary ms-auto">
              <i class="fas fa-eye me-1"></i> Visualizar Página
            </a>
          </div>
        </form>
      </div>
      
      <div class="mt-3">
        <div class="card">
          <div class="card-body">
            <h6>Informações do Workshop:</h6>
            <p><strong>Criado em:</strong> {wk.created_at.strftime('%d/%m/%Y às %H:%M')}</p>
            <p><strong>ID:</strong> {wk.id}</p>
          </div>
        </div>
      </div>
    """
    
    return render_template_string(base_css_js.replace("{{ content|safe }}", content),
                                  whatsapp_number=WHATSAPP_NUMBER,
                                  scripts="")

# ---------------- Error Handlers ----------------
@app.errorhandler(404)
def page_not_found(e):
    content = """
    <div class="text-center py-5">
        <h1 style="color:var(--terra-1)">Página Não Encontrada</h1>
        <p class="lead">A página que você está procurando não existe.</p>
        <a href="/" class="btn btn-terra">Voltar à Página Inicial</a>
    </div>
    """
    return render_template_string(base_css_js.replace("{{ content|safe }}", content),
                                  whatsapp_number=WHATSAPP_NUMBER,
                                  scripts=""), 404

@app.errorhandler(403)
def forbidden(e):
    content = """
    <div class="text-center py-5">
        <h1 style="color:var(--terra-1)">Acesso Negado</h1>
        <p class="lead">Você não tem permissão para acessar esta página.</p>
        <a href="/" class="btn btn-terra">Voltar à Página Inicial</a>
    </div>
    """
    return render_template_string(base_css_js.replace("{{ content|safe }}", content),
                                  whatsapp_number=WHATSAPP_NUMBER,
                                  scripts=""), 403

@app.errorhandler(500)
def internal_server_error(e):
    content = """
    <div class="text-center py-5">
        <h1 style="color:var(--terra-1)">Erro Interno do Servidor</h1>
        <p class="lead">Ocorreu um erro inesperado. Tente novamente mais tarde.</p>
        <a href="/" class="btn btn-terra">Voltar à Página Inicial</a>
    </div>
    """
    return render_template_string(base_css_js.replace("{{ content|safe }}", content),
                                  whatsapp_number=WHATSAPP_NUMBER,
                                  scripts=""), 500

# ---------------- Exec ----------------
if __name__ == '__main__':
    print("🔄 Iniciando aplicação Flask...")
    print(f"📊 DATABASE_URL configurada: {'✅ SIM' if app.config['SQLALCHEMY_DATABASE_URI'] else '❌ NÃO'}")
    print(f"🔑 SECRET_KEY: {'✅ Configurada' if os.environ.get('FLASK_SECRET_KEY') else '❌ Não configurada'}")
    print(f"🚀 Porta: {port}")
    
    try:
        app.run(debug=False, host='0.0.0.0', port=port)
    except Exception as e:
        print(f"💥 Erro ao iniciar: {e}")
