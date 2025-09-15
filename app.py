# app.py
import os
from flask import Flask, render_template_string, request, redirect, url_for, send_file, jsonify, session, flash, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
from io import BytesIO
import base64

# ---------------- CONFIG ----------------
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///registrations.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'troque_essa_chave_para_producao')

UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

db = SQLAlchemy(app)

PIX_KEY = "6d51bb56-3bee-45b1-a26c-2b04c1a6718b"
PAYMENT_AMOUNT = "5.00"
WHATSAPP_NUMBER = "558185641262"
ADMIN_PASSWORD = "CODE@2025"

# URLs das imagens
BORBOLETA_URL = "/static/images/borboleta.png"
QR_URL = "/static/images/qrcode-pix.svg"
LOGO_URL = "/static/images/logo.jpeg"
QUEM_SOMOS_LOGO = "/static/images/Quem somos.png"

# ---------------- Models (Eventos e Workshops separados) ----------------
class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    sobrenome = db.Column(db.String(120), nullable=False)
    cpf = db.Column(db.String(20), nullable=False)
    telefone = db.Column(db.String(30), nullable=False)
    paid = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Evento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    data = db.Column(db.String(50))
    horario = db.Column(db.String(50))
    local = db.Column(db.String(200))
    descricao = db.Column(db.Text)
    status = db.Column(db.String(20), default="Aberto")  # Aberto / Fechado
    agradecimento = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    fotos = db.relationship('FotoEvento', backref='evento', lazy=True, cascade="all,delete-orphan")

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
    status = db.Column(db.String(20), default="Em Breve")  # Em Breve / Aberto
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# ---------------- Utilities ----------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file_storage):
    """Salva file_storage em static/uploads e retorna nome salvo."""
    filename = secure_filename(file_storage.filename)
    base, ext = os.path.splitext(filename)
    unique_name = f"{base}_{int(datetime.utcnow().timestamp())}{ext}"
    save_path = os.path.join(UPLOAD_FOLDER, unique_name)
    file_storage.save(save_path)
    return unique_name

# ---------------- Base template (usa URLs diretas) ----------------
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
      body { background: #fff; color: #2b2b2b; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
      .site-header { background: linear-gradient(90deg,var(--terra-1), var(--terra-2)); color: white; padding: 15px 0; }
      .site-title { font-size: 1.2rem; display:flex; align-items:center; gap:12px; }
      .site-title img { height:56px; width:56px; object-fit:contain; border-radius:8px; background:white; padding:6px; }
      .btn-terra { background: var(--terra-2); color: white; border: none; }
      .btn-terra:hover { background: var(--terra-1); color: white; }
      footer { padding: 20px 0; background:#f8f0ea; margin-top:40px; }
      .qr-img { width:260px; height:260px; border: 2px solid var(--terra-3); border-radius: 10px; padding: 10px; background: white; object-fit:contain; }
      .event-card { border: none; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.08); transition: transform 0.25s; }
      .event-card:hover { transform: translateY(-6px); }
      .event-img { height: 240px; object-fit: cover; border-top-left-radius: 10px; border-top-right-radius: 10 page; }
      .idealizadora-img { width: 150px; height: 150px; border-radius: 50%; object-fit: cover; margin: 0 auto 15px; border: 4px solid var(--terra-3); }
      .pix-info { background: var(--terra-4); padding: 15px; border-radius: 8px; margin: 15px 0; }
      .pix-key { font-family: monospace; background: white; padding: 8px; border-radius: 4px; word-break: break-all; }
      .nav-link { color: white !important; font-weight: 500; }
      .nav-link:hover { color: var(--terra-3) !important; }
      .quem-somos-text { font-size: 1.2rem; line-height: 1.6; }
    </style>
  </head>
  <body>
    <header class="site-header">
      <div class="container">
        <div class="d-flex justify-content-between align-items-center">
          <div class="site-title">
            <img src=\"""" + BORBOLETA_URL + """\" alt="Borboleta" />
            <div>
              <div style="font-weight:700; font-size:1.1rem">Conferência de Mulheres</div>
              <small>Mulheres Transformadas</small>
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
            <a class="nav-link mx-2" href="{{ url_for('admin_login') }}">Área do Administrador</a>
          </nav>
        </div>

        <div class="collapse d-md-none mt-3" id="navbarNav">
          <div class="d-flex flex-column">
            <a class="nav-link py-2" href="{{ url_for('index') }}">Inicial</a>
            <a class="nav-link py-2" href="{{ url_for('quem_somos') }}">Quem Somos</a>
            <a class="nav-link py-2" href="{{ url_for('eventos') }}">Eventos</a>
            <a class="nav-link py-2" href="{{ url_for('inscricao') }}">Inscrição</a>
            <a class="nav-link py-2" href="{{ url_for('contato') }}">Contato</a>
            <a class="nav-link py-2" href="{{ url_for('admin_login') }}">Área do Administrador</a>
          </div>
        </div>
      </div>
    </header>

    <main class="container my-4">
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
          <a class="social-btn" href="https://www.instagram.com/transformadas.25" target="_blank">
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
    # pega último evento (o mais recente) e último workshop
    last_event = Evento.query.order_by(Evento.created_at.desc()).first()
    last_workshop = Workshop.query.order_by(Workshop.created_at.desc()).first()

    # Cards: Evento 2025 (usa last_event), Workshop (usa last_workshop)
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

    # Evento card - MODIFICAÇÃO AQUI: Sempre mostrar "Evento 2025" no título
    if last_event:
        # se evento fechado e tiver fotos, capa = primeira foto; se aberto - placeholder
        if last_event.fotos and len(last_event.fotos) > 0:
            cover = "/static/uploads/" + last_event.fotos[0].filename
        else:
            cover = "https://placehold.co/800x600/f6eadf/c2773a?text=Evento+2025"
        content += """
          <div class="col-md-6 mb-4">
            <div class="card event-card">
              <img src=\"""" + cover + """\" class="event-img" alt="Evento 2025">
              <div class="card-body text-center">
                <h2 style="color:var(--terra-2)">Evento 2025</h2>
                <p>Mulheres Transformadas<br>Próximo encontro — aguarde mais informações.</p>
                <a class="btn btn-terra" href=\"/evento/""" + str(last_event.id) + """\">Ver</a>
                """ + ("<a class='btn btn-terra ms-2' href='/inscricao'>Inscrever-se</a>" if last_event.status == 'Aberto' else "") + """
              </div>
            </div>
          </div>
        """
    else:
        # placeholder evento 2025
        content += """
          <div class="col-md-6 mb-4">
            <div class="card event-card">
              <img src="https://placehold.co/800x600/f6eadf/c2773a?text=Evento+2025" class="event-img" alt="Evento 2025">
              <div class="card-body text-center">
                <h2 style="color:var(--terra-2)">Evento 2025</h2>
                <p>Mulheres Transformadas<br>Próximo encontro — aguarde mais informações.</p>
                <a class="btn btn-terra" href="#">Ver</a>
              </div>
            </div>
          </div>
        """

    # Workshop card
    if last_workshop:
        cover_w = "https://placehold.co/800x600/f6eadf/c2773a?text=" + (last_workshop.titulo.replace(" ", "+"))
        status_line = last_workshop.status
        description_w = last_workshop.abordagem if last_workshop.abordagem else "Em Breve"
        content += """
          <div class="col-md-6 mb-4">
            <div class="card event-card">
              <img src=\"""" + cover_w + """\" class="event-img" alt=\"""" + last_workshop.titulo + """\">
              <div class="card-body text-center">
                <h2 style="color:var(--terra-2)">""" + last_workshop.titulo + """</h2>
                <p>""" + ('Em Breve' if last_workshop.status=='Em Breve' else description_w) + """</p>
                <a class="btn btn-terra" href=\"/workshop/""" + str(last_workshop.id) + """\">Ver</a>
              </div>
            </div>
          </div>
        """
    else:
        # placeholder workshop
        content += """
          <div class="col-md-6 mb-4">
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
        <a href="https://www.instagram.com/transformadas.25/#" target="_blank" class="btn btn-terra">
          <i class="fab fa-instagram me-2"></i> @transformadas.25
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
          <p><i class="fab fa-instagram me-2"></i> Instagram: <a href="https://www.instagram.com/transformadas.25" target="_blank">@transformadas.25</a></p>
          <div class="mt-4">
            <a href="https://wa.me/55""" + WHATSAPP_NUMBER + """" class="btn btn-terra me-2" target="_blank"><i class="fab fa-whatsapp me-1"></i> Enviar Mensagem</a>
            <a href="https://www.instagram.com/transformadas.25" class="btn btn-terra" target="_blank"><i class="fab fa-instagram me-1"></i> Seguir no Instagram</a>
          </div>
        </div>
      </div>

      <div class="card mt-3">
        <div class="card-body">
          <h5>Site Desenvolvido por TM Code</h5>
          <p>Contatos do WhatsApp: (81) 99514-3900  |  (81) 98773-4133</p>
          <div class="mt-3">
            <img src=\"""" + LOGO_URL + """\" style="height: 70px;" alt="Logo TM Code" />
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
    return """
  <h2 class="mb-4" style="color:var(--terra-1)">Inscrição - Conferência de Mulheres</h2>

  <div class="card p-4 mb-4">
    <div class="mb-4">
      <h4 style="color:var(--terra-2)">Informações do Evento</h4>
      <p><strong>Data:</strong> 06/12/2025</p>
      <p><strong>Horário:</strong> 16hs às 21hs</p>
      <p><strong>Local:</strong> A definir</p>
    </div>

    <form id="regForm" method="POST" action="/submit_inscricao">
      <h4 style="color:var(--terra-2)">Dados Pessoais</h4>
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
          <label class="form-label">Telefone</label>
          <input name="telefone" class="form-control" required placeholder="(00) 00000-0000">
        </div>
      </div>

      <div class="mb-3 p-3" style="background-color: var(--terra-4); border-radius: 8px;">
        <strong>Valor da inscrição: R$ """ + PAYMENT_AMOUNT + """</strong>
      </div>

      <button type="submit" class="btn btn-terra btn-lg">Efetuar pagamento</button>
    </form>
  </div>

  <!-- modal do QR -->
  <div class="modal fade" id="qrModal" tabindex="-1">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content p-3">
        <div class="modal-header">
          <h5 class="modal-title">Pagamento via PIX</h5>
          <button class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body text-center">
          <div class="pix-info">
            <p>Valor a ser pago: <strong>R$ """ + PAYMENT_AMOUNT + """</strong></p>
            <p>Chave Pix: <span class="pix-key">""" + PIX_KEY + """</span></p>
          </div>

          <p>Escaneie o QR Code abaixo para realizar o pagamento:</p>
          <img id="qrImage" class="qr-img" src=\"""" + QR_URL + """\" alt="QR Code Pix">

          <div class="mt-3">
            <button id="confirmPayBtn" class="btn btn-success">Confirmar pagamento</button>
          </div>
          
          <div class="mt-4 p-3" style="background-color: #f0f8f0; border-radius: 8px;">
            <h6>Entre no Grupo do WhatsApp - Transformadas</h6>
            <p>Após confirmar o pagamento, entre no nosso grupo para receber todas as informações:</p>
            <a href="https://chat.whatsapp.com/ICWsAlDkaFZ7vmcZme0Myr?mode=ems_wa_t" target="_blank" class="btn btn-success">
              <i class="fab fa-whatsapp me-2"></i> Entrar no Grupo
            </a>
          </div>
        </div>
      </div>
    </div>
  </div>
"""

inscricao_scripts = """
<script>
  document.addEventListener('DOMContentLoaded', function(){
    const params = new URLSearchParams(window.location.search);
    const show_qr = params.get('show_qr');
    const reg_id = params.get('id');
    if (show_qr === '1' && reg_id){
      var qrModal = new bootstrap.Modal(document.getElementById('qrModal'));
      qrModal.show();

      document.getElementById('confirmPayBtn').onclick = function(){
        fetch("/confirm_payment", {
          method: "POST",
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ reg_id: reg_id })
        })
        .then(r => r.json())
        .then(resp => {
          if (resp.success){
            var w = window.open("/print_confirmation/" + reg_id, "_blank");
            var msg = encodeURIComponent("Confirmação de inscrição: Nome: " + resp.nome + " CPF: " + resp.cpf + " - Pagamento confirmado.");
            var wa = "https://wa.me/" + resp.whatsapp + "?text=" + msg;
            window.open(wa, "_blank");
            qrModal.hide();
            setTimeout(()=>{ window.location = "/inscricao"; }, 800);
          } else {
            alert("Erro ao confirmar pagamento.");
          }
        })
        .catch(e => { console.error(e); alert("Erro de rede."); });
      };
    }
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
      <img src=\"""" + QR_URL + """\" class="qr" alt="QR Code Pix">
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
    # lista todos eventos
    eventos = Evento.query.order_by(Evento.created_at.desc()).all()
    content = "<h2 style='color:var(--terra-1)'>Eventos Cadastrados</h2><div class='row'>"
    if not eventos:
        content += "<div class='col-12'><p>Nenhum evento cadastrado.</p></div>"
    else:
        for ev in eventos:
            content += """
            <div class='col-md-6 mb-4'>
              <div class='card event-card'>
                <div class='card-body'>
                  <h5>""" + ev.titulo + """ <small class='text-muted'>(""" + ev.status + """)</small></h5>
                  <p><strong>Data:</strong> """ + (ev.data or '') + """ <strong>Horário:</strong> """ + (ev.horario or '') + """</p>
                  <p>""" + ((ev.descricao or '')[:180]) + """</p>
                  <a class='btn btn-terra' href='/evento/""" + str(ev.id) + """'>Abrir</a>
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
def inscricao():
    content = get_inscricao_content()
    return render_template_string(base_css_js.replace("{{ content|safe }}", content),
                                  whatsapp_number=WHATSAPP_NUMBER,
                                  scripts=inscricao_scripts)

@app.route('/submit_inscricao', methods=['POST'])
def submit_inscricao():
    nome = request.form.get('nome', '').strip()
    sobrenome = request.form.get('sobrenome', '').strip()
    cpf = request.form.get('cpf', '').strip()
    telefone = request.form.get('telefone', '').strip()
    if not (nome and sobrenome and cpf and telefone):
        return "Preencha todos os campos", 400
    reg = Registration(nome=nome, sobrenome=sobrenome, cpf=cpf, telefone=telefone)
    db.session.add(reg)
    db.session.commit()
    return redirect(url_for('inscricao') + f"?show_qr=1&id={reg.id}")

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
    return render_template_string(print_tpl,
                                  reg=reg,
                                  payment_amount=PAYMENT_AMOUNT,
                                  pix_key=PIX_KEY,
                                  event_title="Conferência de Mulheres")

# ---------------- Evento page (galeria / agradecimento) ----------------
@app.route('/evento/<int:evento_id>')
def ver_evento(evento_id):
    ev = Evento.query.get_or_404(evento_id)
    photos = ev.fotos
    gallery_html = """
      <h2 style="color:var(--terra-1)">""" + ev.titulo + """ <small class="text-muted">(""" + ev.status + """)</small></h2>
      <p><strong>Data:</strong> """ + (ev.data or '') + """ <strong>Horário:</strong> """ + (ev.horario or '') + """</p>
      <p><strong>Local:</strong> """ + (ev.local or '') + """</p>
      <p>""" + (ev.descricao or '') + """</p>
      <hr />
    """
    if ev.status == 'Aberto':
        gallery_html += "<div class='alert alert-info'>Inscrições abertas.</div>"
        gallery_html += "<a class='btn btn-terra mb-3' href='/inscricao'>Inscrever-se</a>"
    else:
        gallery_html += "<div class='alert alert-secondary'>Evento encerrado. Agradecimento:</div>"
        if ev.agradecimento:
            gallery_html += "<div class='p-3 mb-3' style='background:#f6eadf;border-radius:8px'>" + ev.agradecimento + "</div>"

    gallery_html += "<div class='row mt-4'>"
    if not photos:
        gallery_html += "<div class='col-12'><p>Nenhuma foto cadastrada para este evento.</p></div>"
    else:
        for p in photos:
            gallery_html += """
            <div class="col-md-4 mb-3">
              <div class="card">
                <img src=\"/static/uploads/""" + p.filename + """\" class="img-fluid" style="height:220px;object-fit:cover;border-radius:8px" />
                <div class="card-body">
                  <p>""" + (p.comentario or '') + """</p>
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
    html = """
      <h2 style="color:var(--terra-1)">""" + wk.titulo + """ <small class="text-muted">(""" + wk.status + """)</small></h2>
      <p><strong>Data:</strong> """ + (wk.data or '') + """ <strong>Horário:</strong> """ + (wk.horario or '') + """</p>
      <p><strong>Local:</strong> """ + (wk.local or '') + """</p>
      <h4>Abordagem</h4>
      <p>""" + (wk.abordagem or 'Em breve') + """</p>
    """
    return render_template_string(base_css_js.replace("{{ content|safe }}", html),
                                  whatsapp_number=WHATSAPP_NUMBER,
                                  scripts="")

# ---------------- ADMIN (login, dashboard com 4 cards) ----------------
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        pwd = request.form.get('password', '')
        if pwd == ADMIN_PASSWORD:
            session['admin_logged'] = True
            flash("Acesso concedido.", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Senha incorreta.", "danger")
            return redirect(url_for('admin_login'))
    content = """
      <h2 style="color:var(--terra-1)">Área do Administrador</h2>
      <div class="card p-4">
        <form method="POST">
          <div class="mb-3"><label class="form-label">Senha</label><input name="password" type="password" class="form-control" required></div>
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
    # dashboard com 4 cards: Novo Evento / Ajuste de Evento / Novo Workshop / Excluir Evento / Participantes
    open_events = Evento.query.filter_by(status='Aberto').order_by(Evento.created_at.desc()).all()
    all_events = Evento.query.order_by(Evento.created_at.desc()).all()
    all_workshops = Workshop.query.order_by(Workshop.created_at.desc()).all()
    participants = Registration.query.filter_by(paid=True).order_by(Registration.created_at.desc()).all()
    
    content = """
      <h2 style="color:var(--terra-1)">Painel do Administrador</h2>
      <div class="row">
        <div class="col-md-4">
          <div class="card p-3 mb-3">
            <h5>Novo Evento</h5>
            <p>Cadastrar novo evento (será Aberto por padrão).</p>
            <a class="btn btn-terra" href="/admin/evento/novo">Criar Evento</a>
          </div>
        </div>
        <div class="col-md-4">
          <div class="card p-3 mb-3">
            <h5>Ajuste de Evento</h5>
            <p>Fechar evento (adicionar fotos e agradecimento).</p>
            <a class="btn btn-terra" href="/admin/evento/ajuste">Ajustar Evento</a>
          </div>
        </div>
        <div class="col-md-4">
          <div class="card p-3 mb-3">
            <h5>Novo Workshop</h5>
            <p>Cadastrar workshop (status inicial: Em Breve).</p>
            <a class="btn btn-terra" href="/admin/workshop/novo">Criar Workshop</a>
          </div>
        </div>
        <div class="col-md-4">
          <div class="card p-3 mb-3">
            <h5>Excluir Evento/Workshop</h5>
            <p>Excluir eventos ou workshops existentes.</p>
            <a class="btn btn-terra" href="/admin/excluir">Gerenciar Exclusões</a>
          </div>
        </div>
        <div class="col-md-4">
          <div class="card p-3 mb-3">
            <h5>Participantes</h5>
            <p>Visualizar lista de participantes confirmados.</p>
            <a class="btn btn-terra" href="/admin/participantes">Ver Participantes</a>
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
            content += """
            <div class="col-md-6 mb-3">
              <div class="card p-2">
                <h5>""" + ev.titulo + """</h5>
                <p>""" + (ev.data or '') + """ - """ + (ev.horario or '') + """</p>
                <div>
                  <a class="btn btn-sm btn-outline-terra" href=\"/evento/""" + str(ev.id) + """\">Ver</a>
                  <a class="btn btn-sm btn-terra" href=\"/admin/evento/""" + str(ev.id) + """/fechar\">Fechar Evento</a>
                </div>
              </div>
            </div>
            """
    content += "</div>"
    return render_template_string(base_css_js.replace("{{ content|safe }}", content),
                                  whatsapp_number=WHATSAPP_NUMBER,
                                  scripts="")

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
        if not titulo:
            flash("Título obrigatório.", "danger")
            return redirect(url_for('admin_novo_evento'))
        ev = Evento(titulo=titulo, data=data, horario=horario, local=local, descricao=descricao, status='Aberto')
        db.session.add(ev)
        db.session.commit()
        flash("Evento criado.", "success")
        return redirect(url_for('admin_dashboard'))
    content = """
      <h3 style="color:var(--terra-1)">Novo Evento</h3>
      <div class="card p-3">
        <form method="POST">
          <div class="mb-2"><label>Título</label><input name="titulo" class="form-control" required></div>
          <div class="mb-2"><label>Data</label><input name="data" class="form-control"></div>
          <div class="mb-2"><label>Horário</label><input name="horario" class="form-control"></div>
          <div class="mb-2"><label>Local</label><input name="local" class="form-control"></div>
          <div class="mb-2"><label>Descrição</label><textarea name="descricao" class="form-control"></textarea></div>
          <button class="btn btn-terra">Criar Evento</button>
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
        content += "<div class='card p-3'><p>Não há eventos abertos para ajuste.</p></div>"
    else:
        content += "<div class='row'>"
        for ev in open_events:
            content += """
            <div class='col-md-6 mb-3'>
              <div class='card p-3'>
                <h5>""" + ev.titulo + """</h5>
                <p>""" + (ev.data or '') + """ - """ + (ev.horario or '') + """</p>
                <p>""" + ((ev.descricao or '')[:160]) + """</p>
                <a class='btn btn-terra' href='/admin/evento/""" + str(ev.id) + """/fechar'>Fechar Evento (adicionar fotos/agradecimento)</a>
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
    if request.method == 'POST':
        # receber arquivos e agradecimento
        files = request.files.getlist('fotos')
        agradecimento = request.form.get('agradecimento', '').strip()
        valid_files = [f for f in files if f and allowed_file(f.filename)]
        if len(valid_files) < 5:
            flash("Para fechar o evento é necessário enviar no mínimo 5 fotos.", "danger")
            return redirect(url_for('admin_ajuste_evento_closing', evento_id=evento_id))
        # salvar fotos
        saved = []
        for f in valid_files:
            fname = save_uploaded_file(f)
            fe = FotoEvento(evento_id=evento_id, filename=fname, comentario=request.form.get('comentario', '').strip())
            db.session.add(fe)
            saved.append(fname)
        # atualizar evento
        ev.status = 'Fechado'
        ev.agradecimento = agradecimento
        db.session.commit()
        flash(f"Evento '{ev.titulo}' fechado e {len(saved)} fotos adicionadas.", "success")
        return redirect(url_for('admin_dashboard'))

    content = """
      <h3 style="color:var(--terra-1)">Fechar Evento: """ + ev.titulo + """</h3>
      <div class="card p-3">
        <form method="POST" enctype="multipart/form-data">
          <div class="mb-2">
            <label>Escolha as fotos (mínimo 5)</label>
            <input type="file" name="fotos" multiple class="form-control" accept="image/*" required>
          </div>
          <div class="mb-2">
            <label>Comentário para as fotos (opcional)</label>
            <textarea name="comentario" class="form-control"></textarea>
          </div>
          <div class="mb-2">
            <label>Agradecimento (texto que aparecerá quando o evento estiver fechado)</label>
            <textarea name="agradecimento" class="form-control" required></textarea>
          </div>
          <button class="btn btn-terra">Fechar Evento e Salvar Fotos</button>
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
        wk = Workshop(titulo=titulo, data=data, horario=horario, local=local, abordagem=abordagem, status='Em Breve')
        db.session.add(wk)
        db.session.commit()
        flash("Workshop criado (status: Em Breve).", "success")
        return redirect(url_for('admin_dashboard'))
    content = """
      <h3 style="color:var(--terra-1)">Novo Workshop</h3>
      <div class="card p-3">
        <form method="POST">
          <div class="mb-2"><label>Título</label><input name="titulo" class="form-control" required></div>
          <div class="mb-2"><label>Data</label><input name="data" class="form-control"></div>
          <div class="mb-2"><label>Horário</label><input name="horario" class="form-control"></div>
          <div class="mb-2"><label>Local</label><input name="local" class="form-control"></div>
          <div class="mb-2"><label>Abordagem</label><textarea name="abordagem" class="form-control"></textarea></div>
          <button class="btn btn-terra">Criar Workshop</button>
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
                # Primeiro exclui as fotos associadas
                FotoEvento.query.filter_by(evento_id=id_item).delete()
                # Depois exclui o evento
                db.session.delete(evento)
                db.session.commit()
                flash("Evento excluído com sucesso.", "success")
        elif tipo == 'workshop':
            workshop = Workshop.query.get(id_item)
            if workshop:
                db.session.delete(workshop)
                db.session.commit()
                flash("Workshop excluído com sucesso.", "success")
        
        return redirect(url_for('admin_excluir'))
    
    eventos = Evento.query.order_by(Evento.created_at.desc()).all()
    workshops = Workshop.query.order_by(Workshop.created_at.desc()).all()
    
    content = """
      <h3 style="color:var(--terra-1)">Excluir Eventos/Workshops</h3>
      <div class="alert alert-warning">
        <strong>Atenção:</strong> Esta ação é irreversível. Todos os dados do evento/workshop serão permanentemente excluídos.
      </div>
      
      <div class="row">
        <div class="col-md-6">
          <h4>Eventos</h4>
    """
    
    if not eventos:
        content += "<p>Nenhum evento cadastrado.</p>"
    else:
        for evento in eventos:
            content += """
            <div class="card mb-3">
              <div class="card-body">
                <h5>""" + evento.titulo + """</h5>
                <p><strong>Status:</strong> """ + evento.status + """</p>
                <p><strong>Data:</strong> """ + (evento.data or 'Não definida') + """</p>
                <form method="POST" onsubmit="return confirm('Tem certeza que deseja excluir este evento? Esta ação não pode ser desfeita.');">
                  <input type="hidden" name="tipo" value="evento">
                  <input type="hidden" name="id" value=\"""" + str(evento.id) + """\">
                  <button type="submit" class="btn btn-danger">Excluir Evento</button>
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
        content += "<p>Nenhum workshop cadastrado.</p>"
    else:
        for workshop in workshops:
            content += """
            <div class="card mb-3">
              <div class="card-body">
                <h5>""" + workshop.titulo + """</h5>
                <p><strong>Status:</strong> """ + workshop.status + """</p>
                <p><strong>Data:</strong> """ + (workshop.data or 'Não definida') + """</p>
                <form method="POST" onsubmit="return confirm('Tem certeza que deseja excluir este workshop? Esta ação não pode ser desfeita.');">
                  <input type="hidden" name="tipo" value="workshop">
                  <input type="hidden" name="id" value=\"""" + str(workshop.id) + """\">
                  <button type="submit" class="btn btn-danger">Excluir Workshop</button>
                </form>
              </div>
            </div>
            """
    
    content += """
        </div>
      </div>
    """
    
    return render_template_string(base_css_js.replace("{{ content|safe }}", content),
                                  whatsapp_number=WHATSAPP_NUMBER,
                                  scripts="")

# ---------------- Admin: Lista de Participantes ----------------
@app.route('/admin/participantes')
@admin_required
def admin_participantes():
    participantes = Registration.query.filter_by(paid=True).order_by(Registration.created_at.desc()).all()
    
    content = """
      <h3 style="color:var(--terra-1)">Lista de Participantes Confirmados</h3>
      <div class="mb-3">
        <a href="/admin/exportar_participantes" class="btn btn-terra">Exportar Lista (CSV)</a>
      </div>
      
      <div class="card">
        <div class="card-body">
          <div class="table-responsive">
            <table class="table table-striped">
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>CPF</th>
                  <th>Telefone</th>
                  <th>Data de Inscrição</th>
                </tr>
              </thead>
              <tbody>
    """
    
    if not participantes:
        content += """
          <tr>
            <td colspan="4" class="text-center">Nenhum participante confirmado ainda.</td>
          </tr>
        """
    else:
        for p in participantes:
            content += """
            <tr>
              <td>""" + p.nome + " " + p.sobrenome + """</td>
              <td>""" + p.cpf + """</td>
              <td>""" + p.telefone + """</td>
              <td>""" + p.created_at.strftime('%d/%m/%Y %H:%M') + """</td>
            </tr>
            """
    
    content += """
              </tbody>
            </table>
          </div>
        </div>
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
    
    participantes = Registration.query.filter_by(paid=True).order_by(Registration.created_at).all()
    
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Nome', 'Sobrenome', 'CPF', 'Telefone', 'Data de Inscrição'])
    
    for p in participantes:
        cw.writerow([p.nome, p.sobrenome, p.cpf, p.telefone, p.created_at.strftime('%d/%m/%Y %H:%M')])
    
    output = si.getvalue()
    si.close()
    
    return send_file(
        BytesIO(output.encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='participantes_confirmados.csv'
    )

# ---------------- Optional: editar/deletar (simples) ----------------
@app.route('/admin/workshop/<int:workshop_id>/editar', methods=['GET', 'POST'])
@admin_required
def admin_editar_workshop(workshop_id):
    wk = Workshop.query.get_or_404(workshop_id)
    if request.method == 'POST':
        wk.titulo = request.form.get('titulo', wk.titulo)
        wk.data = request.form.get('data', wk.data)
        wk.horario = request.form.get('horario', wk.horario)
        wk.local = request.form.get('local', wk.local)
        wk.abordagem = request.form.get('abordagem', wk.abordagem)
        wk.status = request.form.get('status', wk.status)
        db.session.commit()
        flash("Workshop atualizado.", "success")
        return redirect(url_for('admin_dashboard'))
    content = """
      <h3 style="color:var(--terra-1)">Editar Workshop</h3>
      <div class="card p-3">
        <form method="POST">
          <div class="mb-2"><label>Título</label><input name="titulo" value=\"""" + wk.titulo + """\" class="form-control" required></div>
          <div class="mb-2"><label>Data</label><input name="data" value=\"""" + (wk.data or '') + """\" class="form-control"></div>
          <div class="mb-2"><label>Horário</label><input name="horario" value=\"""" + (wk.horario or '') + """\" class="form-control"></div>
          <div class="mb-2"><label>Local</label><input name="local" value=\"""" + (wk.local or '') + """\" class="form-control"></div>
          <div class="mb-2"><label>Abordagem</label><textarea name="abordagem" class="form-control">""" + (wk.abordagem or '') + """</textarea></div>
          <div class="mb-2"><label>Status</label>
            <select name="status" class="form-control">
              <option value="Em Breve" """ + ("selected" if wk.status=="Em Breve" else "") + """>Em Breve</option>
              <option value="Aberto" """ + ("selected" if wk.status=="Aberto" else "") + """>Aberto</option>
            </select>
          </div>
          <button class="btn btn-terra">Salvar</button>
        </form>
      </div>
    """
    return render_template_string(base_css_js.replace("{{ content|safe }}", content),
                                  whatsapp_number=WHATSAPP_NUMBER,
                                  scripts="")

# ---------------- Exec ----------------
if __name__ == '__main__':
    app.run(debug=True)
