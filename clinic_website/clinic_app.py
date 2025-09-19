import os
import io, csv
import uuid
from datetime import datetime
from functools import wraps
import imghdr
try:
  import magic as filemagic  # python-magic, optional but stronger
except Exception:
  filemagic = None
from itsdangerous import URLSafeTimedSerializer, BadData

# Helpful dependency errors for users who haven't installed requirements
try:
  from dotenv import load_dotenv
except Exception:
  load_dotenv = None

try:
  from flask import Flask, request, redirect, url_for, session, jsonify, flash, send_file
  from flask_sqlalchemy import SQLAlchemy
  from werkzeug.security import generate_password_hash, check_password_hash
  from werkzeug.utils import secure_filename
  from flask import render_template
except Exception as e:
  missing = str(e)
  print("A required package is missing:", missing)
  print("Please run: python -m pip install -r requirements.txt")
  raise

# Load .env automatically if python-dotenv is available
if load_dotenv:
  load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FH_SECRET', 'change-this-in-prod')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///clinic_full.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -------------------- Models --------------------
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(40))
    password_hash = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Staff(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(120))
  email = db.Column(db.String(120), unique=True, nullable=False)
  password_hash = db.Column(db.String(200))
  role = db.Column(db.String(40), default='staff')  # 'staff' or 'doctor' or 'admin'
  created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'))
    patient = db.relationship('Patient', backref='appointments')
    date = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.String(300))
    status = db.Column(db.String(40), default='requested')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Vitals(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'))
    patient = db.relationship('Patient', backref='vitals')
    systolic = db.Column(db.Integer)
    diastolic = db.Column(db.Integer)
    glucose = db.Column(db.Float)
    note = db.Column(db.String(300))
    measured_at = db.Column(db.DateTime, default=datetime.utcnow)

class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    slug = db.Column(db.String(200), unique=True)
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Testimonial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(120))
    text = db.Column(db.String(600))
    featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class FAQ(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    q = db.Column(db.String(400))
    a = db.Column(db.String(1000))


class PatientFile(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'))
  patient = db.relationship('Patient', backref='files')
  filename = db.Column(db.String(300))
  original_name = db.Column(db.String(300))
  uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)


class AuditLog(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  actor = db.Column(db.String(200))
  action = db.Column(db.String(400))
  created_at = db.Column(db.DateTime, default=datetime.utcnow)

# create db if not exists
with app.app_context():
    db.create_all()

# Templates have been moved to templates/ directory. We use Flask's render_template below.

BOOK = """
{% extends 'base.html' %}
{% block content %}
  <h2 class="text-2xl font-bold mt-6">Book an appointment</h2>
  <form action="/book" method="post" class="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3 bg-white p-4 rounded shadow">
    <input name="name" placeholder="Full name" required class="border p-2 rounded" />
    <input name="email" placeholder="Email" type="email" required class="border p-2 rounded" />
    <input name="phone" placeholder="Phone" class="border p-2 rounded" />
    <input name="date" placeholder="YYYY-MM-DD HH:MM" required class="border p-2 rounded" />
    <textarea name="reason" placeholder="Reason for visit" class="border p-2 rounded col-span-full"></textarea>
    <button class="bg-[color:var(--primary)] text-white px-4 py-2 rounded">Request appointment</button>
  </form>
{% endblock %}
"""

LOGIN = """
{% extends 'base.html' %}
{% block content %}
  <h2 class="text-2xl font-bold mt-6">Patient Login</h2>
  <form action="/login" method="post" class="mt-4 grid grid-cols-1 gap-3 max-w-md bg-white p-4 rounded shadow">
    <input name="email" placeholder="Email" type="email" required class="border p-2 rounded" />
    <input name="password" placeholder="Password" type="password" required class="border p-2 rounded" />
    <button class="bg-[color:var(--primary)] text-white px-4 py-2 rounded">Login</button>
  </form>
  <p class="text-sm text-gray-500 mt-2">If you need an account, please contact the clinic.</p>
{% endblock %}
"""

SIGNUP = """
{% extends 'base.html' %}
{% block content %}
  <h2 class="text-2xl font-bold mt-6">Sign up disabled</h2>
  <div class="mt-4 p-4 bg-white rounded shadow">Account creation is currently disabled. Please contact the clinic to create an account or use Patient Login.</div>
{% endblock %}
"""

DASHBOARD = """
{% extends 'base.html' %}
{% block content %}
  <h2 class="text-2xl font-bold mt-6">Hello, {{ patient.name.split(' ')[0] }}</h2>
  <div class="mt-4 grid md:grid-cols-3 gap-4">
    <div class="bg-white rounded shadow p-4 col-span-2">
      <h3 class="font-semibold">Your Vitals</h3>
      <canvas id="bpChart" height="120"></canvas>
      <canvas id="glucoseChart" height="120" class="mt-4"></canvas>
      <div class="mt-4">
        <a href="/export/vitals/{{ patient.id }}" class="text-sm underline">Export readings (CSV)</a>
      </div>
    </div>
    <div class="bg-white rounded shadow p-4">
      <h3 class="font-semibold">Log new reading</h3>
      <form action="/vitals" method="post" class="mt-3 grid gap-2">
        <input name="systolic" placeholder="Systolic" type="number" required class="border p-2 rounded" />
        <input name="diastolic" placeholder="Diastolic" type="number" required class="border p-2 rounded" />
        <input name="glucose" placeholder="Glucose mg/dL" type="number" step="0.1" class="border p-2 rounded" />
        <textarea name="note" placeholder="Optional note" class="border p-2 rounded"></textarea>
        <button class="bg-[color:var(--primary)] text-white px-3 py-2 rounded">Save reading</button>
      </form>
    </div>
  </div>

  <script>
    async function fetchData(){
      const resp = await fetch('/api/vitals/{{ patient.id }}');
      const data = await resp.json();
      return data;
    }
    fetchData().then(data=>{
      const times = data.map(r=>new Date(r.measured_at).toLocaleString());
      const systolic = data.map(r=>r.systolic);
      const diastolic = data.map(r=>r.diastolic);
      const glucose = data.map(r=>r.glucose);

      const ctx1 = document.getElementById('bpChart');
      new Chart(ctx1, {type: 'line', data: {labels: times, datasets: [{label:'Systolic', data: systolic, tension:0.3},{label:'Diastolic', data: diastolic, tension:0.3}]}, options:{interaction:{mode:'index',intersect:false}}});

      const ctx2 = document.getElementById('glucoseChart');
      new Chart(ctx2, {type: 'bar', data: {labels: times, datasets: [{label:'Glucose mg/dL', data: glucose}]}, options:{scales:{y:{beginAtZero:true}}}});
    }).catch(err=>console.error(err));
  </script>
{% endblock %}
"""

BLOG = """
{% extends 'base.html' %}
{% block content %}
  <h2 class="text-2xl font-bold mt-6">Blog & Tips</h2>
  <div class="mt-4 grid md:grid-cols-2 gap-4">
    {% for p in posts %}
      <div class="bg-white rounded shadow p-4">
        <h3 class="font-semibold"><a href="/blog/{{ p.slug }}">{{ p.title }}</a></h3>
        <div class="text-sm text-gray-600 mt-2">{{ p.content[:150] }}...</div>
      </div>
    {% endfor %}
  </div>
{% endblock %}
"""

TESTIMONIALS = """
{% extends 'base.html' %}
{% block content %}
  <h2 class="text-2xl font-bold mt-6">What Our Patients Say</h2>
  <div class="mt-4 grid md:grid-cols-2 gap-4">
    {% for t in testimonials %}
      <div class="bg-white rounded shadow p-4">
        <div class="italic">"{{ t.text }}"</div>
        <div class="mt-3 text-sm font-semibold">— {{ t.author }}</div>
      </div>
    {% endfor %}
  </div>
{% endblock %}
"""

ADMIN_LOGIN = """
{% extends 'base.html' %}
{% block content %}
  <h2 class="text-2xl font-bold mt-6">Admin Login</h2>
  <form action="/admin/login" method="post" class="mt-4 max-w-md bg-white p-4 rounded shadow">
    <input name="password" placeholder="Admin password" type="password" required class="border p-2 rounded" />
    <button class="bg-[color:var(--primary)] text-white px-4 py-2 rounded mt-2">Login</button>
  </form>
{% endblock %}
"""

ADMIN_DASH = """
{% extends 'base.html' %}
{% block content %}
  <h2 class="text-2xl font-bold mt-6">Admin</h2>
  <div class="mt-4 grid md:grid-cols-2 gap-4">
    <div class="bg-white rounded shadow p-4">
      <h3 class="font-semibold">Appointments</h3>
      <ul class="mt-2 text-sm">
        {% for a in appts %}
          <li>{{ a.date }} — {{ a.patient.name }} — {{ a.status }}</li>
        {% endfor %}
      </ul>
    </div>
    <div class="bg-white rounded shadow p-4">
      <h3 class="font-semibold">Content</h3>
      <div><a href="/admin/new-post" class="underline">New blog post</a></div>
      <div class="mt-2"><a href="/admin/new-faq" class="underline">Add FAQ</a></div>
    </div>
  </div>
{% endblock %}
"""

# Put templates into a DictLoader so we can use {% extends 'base.html' %}
from flask import url_for, get_flashed_messages


@app.context_processor
def inject_common():
  phone = os.environ.get('CLINIC_PHONE', '+1234567890')
  # whatsapp requires digits without + for wa.me URL
  wa_num = os.environ.get('CLINIC_WHATSAPP', phone)
  wa_clean = ''.join([c for c in wa_num if c.isdigit()])
  return {
    'now': datetime.utcnow(),
    'doctor_name': os.environ.get('DOCTOR_NAME', 'Amit Patel, MD'),
    'doctor_bio': os.environ.get('DOCTOR_BIO', 'My mission is to help patients live healthy lives with diabetes and hypertension...'),
    'doctor_title': os.environ.get('DOCTOR_TITLE', 'Endocrinologist & Hypertension Specialist'),
    'clinic_phone': phone,
    'clinic_whatsapp': wa_clean,
    'clinic_email': os.environ.get('CLINIC_EMAIL', 'clinic@example.com')
  }


# -------------------- Helpers --------------------
def admin_required(f):
  @wraps(f)
  def decorated(*args, **kwargs):
    # Allow the legacy ADMIN_PASS flag (session['is_admin']) or a Staff user with role 'admin'
    if not (session.get('is_admin') or session.get('staff_role') == 'admin'):
      return redirect(url_for('admin_login'))
    return f(*args, **kwargs)
  return decorated

# -------------------- Routes --------------------
@app.route('/')
def home():
  # Prefer to show featured testimonials on the homepage; fall back to most recent.
  try:
    t = Testimonial.query.filter_by(featured=True).order_by(Testimonial.created_at.desc()).limit(5).all()
    if not t:
      t = Testimonial.query.order_by(Testimonial.created_at.desc()).limit(5).all()
  except Exception:
    # If the DB schema doesn't have 'featured' yet (older databases), fall back safely.
    t = Testimonial.query.order_by(Testimonial.created_at.desc()).limit(5).all()
  return render_template('home.html', title='Home', testimonials=t)

@app.route('/services')
def services():
  return render_template('services.html', title='Services')

@app.route('/resources')
def resources():
  faqs = FAQ.query.all()
  return render_template('resources.html', title='Resources', faqs=faqs)

@app.route('/download/sample-diet.pdf')
def sample_pdf():
    buf = io.BytesIO()
    buf.write(b"Diet & Lifestyle Guidelines (placeholder). Replace with real PDF file in production.")
    buf.seek(0)
    return send_file(buf, download_name='diet-guidelines.txt', as_attachment=True)

@app.route('/book', methods=['GET', 'POST'])
def book():
  if request.method == 'POST':
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    doctor = request.form.get('doctor') or request.args.get('doctor')
    date_str = request.form.get('date')
    reason = request.form.get('reason')
    try:
      date = datetime.fromisoformat(date_str)
    except Exception:
      flash('Invalid date format. Use YYYY-MM-DD HH:MM (24h).')
      return redirect(url_for('book'))
    patient = Patient.query.filter_by(email=email).first()
    if not patient:
      patient = Patient(name=name or email.split('@')[0], email=email, phone=phone)
      db.session.add(patient)
      db.session.commit()
    # include requested doctor in the reason for simple tracking
    if doctor:
      reason = f"Doctor: {doctor} — {reason}"
    appt = Appointment(patient=patient, date=date, reason=reason)
    db.session.add(appt)
    db.session.commit()
    gcal_text = f"{patient.name} appointment - {reason}"
    gcal_time = date.strftime('%Y%m%dT%H%M00')
    gcal_link = (
      f"https://www.google.com/calendar/render?action=TEMPLATE&text={gcal_text}"
      f"&dates={gcal_time}/{gcal_time}&details={reason}"
    )
    flash('Appointment requested — confirmation shown below')
    return (
      f"<p>Requested. <a href='{gcal_link}' target='_blank'>Add to Google Calendar</a></p>"
      f"<p><a href='/'>Back home</a></p>"
    )
  # Pass any prefill doctor name through to the form
  prefill_doctor = request.args.get('doctor')
  return render_template('book.html', title='Book', prefill_doctor=prefill_doctor)

# Signup route removed by request. Account creation is disabled for now.

@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    email = request.form.get('email')
    password = request.form.get('password')
    p = Patient.query.filter_by(email=email).first()
    if not p or not p.password_hash or not check_password_hash(p.password_hash, password):
      flash('Invalid credentials')
      return redirect(url_for('login'))
    session['patient_email'] = p.email
    session['patient_id'] = p.id
    flash('Logged in')
    return redirect(url_for('dashboard'))
  return render_template('login.html', title='Login')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out')
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if not session.get('patient_email'):
        flash('Please login to view your dashboard.')
        return redirect(url_for('login'))
    patient = Patient.query.filter_by(email=session['patient_email']).first()
    return render_template('dashboard.html', patient=patient, title='Dashboard')

@app.route('/vitals', methods=['POST'])
def vitals():
    if not session.get('patient_email'):
        flash('Please login to save vitals.')
        return redirect(url_for('login'))
    patient = Patient.query.filter_by(email=session['patient_email']).first()
    systolic = request.form.get('systolic')
    diastolic = request.form.get('diastolic')
    glucose = request.form.get('glucose')
    note = request.form.get('note')
    v = Vitals(patient=patient, systolic=int(systolic), diastolic=int(diastolic), glucose=float(glucose) if glucose else None, note=note)
    db.session.add(v)
    db.session.commit()
    flash('Reading saved')
    return redirect(url_for('dashboard'))

@app.route('/api/vitals/<int:patient_id>')
def api_vitals(patient_id):
    pts = Vitals.query.filter_by(patient_id=patient_id).order_by(Vitals.measured_at.asc()).all()
    out = []
    for p in pts:
        out.append({
            'id': p.id,
            'systolic': p.systolic,
            'diastolic': p.diastolic,
            'glucose': p.glucose,
            'note': p.note,
            'measured_at': p.measured_at.isoformat()
        })
    return jsonify(out)

@app.route('/export/vitals/<int:patient_id>')
def export_vitals(patient_id):
    pts = Vitals.query.filter_by(patient_id=patient_id).order_by(Vitals.measured_at.asc()).all()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['measured_at','systolic','diastolic','glucose','note'])
    for p in pts:
        cw.writerow([p.measured_at.isoformat(), p.systolic, p.diastolic, p.glucose, p.note])
    mem = io.BytesIO()
    mem.write(si.getvalue().encode('utf-8'))
    mem.seek(0)
    return send_file(mem, download_name='vitals.csv', as_attachment=True)

@app.route('/blog')
def blog():
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template('blog.html', posts=posts, title='Blog')

@app.route('/blog/<slug>')
def blog_post(slug):
    p = BlogPost.query.filter_by(slug=slug).first_or_404()
    return f"<h1>{p.title}</h1><div>{p.content}</div><p><a href='/blog'>Back</a></p>"

@app.route('/testimonials')
def testimonials():
    t = Testimonial.query.order_by(Testimonial.created_at.desc()).all()
    return render_template('testimonials.html', testimonials=t, title='Testimonials')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
  if request.method == 'POST':
    pw = request.form.get('password')
    admin_pass = os.environ.get('ADMIN_PASS', 'admin')
    if pw == admin_pass:
      session['is_admin'] = True
      return redirect(url_for('admin'))
    flash('Incorrect admin password')
  return render_template('admin_login.html')


# -------------------- Staff auth & dashboard --------------------
def staff_required(f):
  @wraps(f)
  def decorated(*args, **kwargs):
    if not session.get('staff_email') and not session.get('is_admin'):
      return redirect(url_for('staff_login'))
    return f(*args, **kwargs)
  return decorated


@app.route('/staff/login', methods=['GET', 'POST'])
def staff_login():
  if request.method == 'POST':
    email = request.form.get('email')
    password = request.form.get('password')
    s = Staff.query.filter_by(email=email).first()
    if not s or not s.password_hash or not check_password_hash(s.password_hash, password):
      flash('Invalid staff credentials')
      return redirect(url_for('staff_login'))
    session['staff_email'] = s.email
    session['staff_id'] = s.id
    session['staff_role'] = s.role
    flash('Staff logged in')
    return redirect(url_for('staff_dashboard'))
  return render_template('staff_login.html')


@app.route('/staff/logout')
def staff_logout():
  # clear staff session but preserve patient session if impersonating
  session.pop('staff_email', None)
  session.pop('staff_id', None)
  session.pop('staff_role', None)
  flash('Staff logged out')
  return redirect(url_for('home'))


@app.route('/staff')
@staff_required
def staff_dashboard():
  staff = None
  if session.get('staff_email'):
    staff = Staff.query.filter_by(email=session['staff_email']).first()
  patients = Patient.query.order_by(Patient.created_at.desc()).limit(50).all()
  return render_template('staff_dash.html', staff=staff, patients=patients)


@app.route('/staff/file-token/<int:file_id>')
@staff_required
def staff_file_token(file_id):
  pf = PatientFile.query.get_or_404(file_id)
  s = get_serializer()
  token = s.dumps({'file_id': pf.id})
  link = url_for('download_file', file_id=pf.id, token=token, _external=True)
  # record audit
  al = AuditLog(actor=session.get('staff_email') or 'staff', action=f'Generated download token for file {pf.id}')
  db.session.add(al)
  db.session.commit()
  return f'Signed link (valid 1 hour): {link}'


# Allowed extensions and size limit (bytes)
ALLOWED_EXT = {'pdf','jpg','jpeg','png','txt','doc','docx'}
MAX_FILE_BYTES = 8 * 1024 * 1024  # 8MB

def allowed_file(filename):
  if '.' not in filename:
    return False
  ext = filename.rsplit('.',1)[1].lower()
  return ext in ALLOWED_EXT


def get_serializer():
  return URLSafeTimedSerializer(app.config['SECRET_KEY'])


def send_alert(subject, body):
  # Simple SMTP alert if environment vars are present; otherwise no-op
  host = os.environ.get('SMTP_HOST')
  if not host:
    return False
  try:
    import smtplib
    from email.message import EmailMessage
    port = int(os.environ.get('SMTP_PORT', 587))
    user = os.environ.get('SMTP_USER')
    pwd = os.environ.get('SMTP_PASS')
    to = os.environ.get('ALERT_EMAIL')
    if not to:
      return False
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = user or 'noreply@example.com'
    msg['To'] = to
    msg.set_content(body)
    s = smtplib.SMTP(host, port, timeout=10)
    s.starttls()
    if user and pwd:
      s.login(user, pwd)
    s.send_message(msg)
    s.quit()
    return True
  except Exception as e:
    print('Alert send failed:', e)
    return False

@app.route('/admin')
@admin_required
def admin():
  appts = Appointment.query.order_by(Appointment.date.asc()).all()
  patients = Patient.query.order_by(Patient.created_at.desc()).all()
  return render_template('admin_dash.html', appts=appts, patients=patients)


@app.route('/admin/new-patient', methods=['GET', 'POST'])
@admin_required
def new_patient():
  if request.method == 'POST':
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    pw = request.form.get('password') or 'changeme'
    if Patient.query.filter_by(email=email).first():
      flash('Patient with this email already exists')
      return redirect(url_for('admin'))
    p = Patient(name=name, email=email, phone=phone, password_hash=generate_password_hash(pw))
    db.session.add(p)
    db.session.commit()
    flash('Patient created — share credentials securely')
    return redirect(url_for('admin'))
  return "<form method='post'>Name: <input name='name'/><br/>Email: <input name='email'/><br/>Phone: <input name='phone'/><br/>Password: <input name='password'/><br/><button>Create</button></form>"


@app.route('/admin/upload/<int:patient_id>', methods=['GET', 'POST'])
@staff_required
def upload_file(patient_id):
  p = Patient.query.get_or_404(patient_id)
  if request.method == 'POST':
    f = request.files.get('file')
    if not f:
      flash('No file uploaded')
      return redirect(url_for('admin'))
    if not allowed_file(f.filename):
      flash('File type not allowed')
      return redirect(url_for('admin'))
    # read first chunk to enforce size limit without streaming to disk first
    data = f.read()
    if len(data) > MAX_FILE_BYTES:
      flash('File too large (max 8 MB)')
      return redirect(url_for('admin'))
    # reset stream position
    f.stream.seek(0)
    orig_name = f.filename
    safe = secure_filename(orig_name)
    # simple MIME checks: images via imghdr, PDFs by header
    ext = orig_name.rsplit('.',1)[-1].lower() if '.' in orig_name else ''
    if ext in ('jpg','jpeg','png'):
      kind = imghdr.what(None, h=data)
      if not kind:
        flash('Uploaded image appears invalid')
        return redirect(url_for('admin'))
    if ext == 'pdf':
      if not data[:4] == b'%PDF':
        flash('Uploaded PDF appears invalid')
        return redirect(url_for('admin'))
    uid = uuid.uuid4().hex
    stored_name = f"{uid}_{safe}"
    # store under instance/uploads/<patient_id>/
    updir = os.path.join(os.path.dirname(__file__), 'instance', 'uploads', str(patient_id))
    os.makedirs(updir, exist_ok=True)
    dest = os.path.join(updir, stored_name)
    f.save(dest)
    pf = PatientFile(patient=p, filename=stored_name, original_name=orig_name)
    db.session.add(pf)
    # audit log
    actor = session.get('staff_email') or session.get('patient_email') or 'system'
    # try stronger MIME detection if python-magic is available
    suspicious = False
    mimetype = None
    try:
      if filemagic:
        mimetype = filemagic.from_buffer(data, mime=True)
        # basic checks: if extension says image/pdf but detected mime differs, mark suspicious
        if ext in ('jpg','jpeg','png') and not mimetype.startswith('image/'):
          suspicious = True
        if ext == 'pdf' and mimetype != 'application/pdf':
          suspicious = True
    except Exception:
      mimetype = None

    al = AuditLog(actor=actor, action=f"Uploaded file {orig_name} for patient {p.id} (mimetype={mimetype}){' [SUSPICIOUS]' if suspicious else ''}")
    db.session.add(al)
    db.session.commit()
    if suspicious:
      send_alert('Suspicious upload detected', f"Staff {actor} uploaded suspicious file {orig_name} for patient {p.id} (mimetype={mimetype})")
      flash('File uploaded — marked suspicious and alerted to admins')
    else:
      flash('File uploaded')
    return redirect(url_for('admin'))
  return f"<form method='post' enctype='multipart/form-data'>Upload for {p.name}: <input type='file' name='file'/> <button>Upload</button></form>"


@app.route('/patient/files')
def patient_files():
  if not session.get('patient_email'):
    flash('Please login to view files')
    return redirect(url_for('login'))
  patient = Patient.query.filter_by(email=session['patient_email']).first()
  files = PatientFile.query.filter_by(patient_id=patient.id).order_by(PatientFile.uploaded_at.desc()).all()
  return render_template('patient_files.html', files=files, patient=patient)


@app.route('/patient/files/<int:file_id>/download')
def download_file(file_id):
  pf = PatientFile.query.get_or_404(file_id)
  # ensure only the patient or admin can download
  # Allow download if:
  # - the requester is the patient owning the file, OR
  # - the requester is staff/admin, OR
  # - a valid signed token is provided as ?token=...
  authorised = False
  if session.get('patient_email'):
    patient = Patient.query.filter_by(email=session['patient_email']).first()
    if patient and patient.id == pf.patient_id:
      authorised = True
  if session.get('is_admin') or session.get('staff_email'):
    authorised = True
  token = request.args.get('token')
  if not authorised and token:
    s = get_serializer()
    try:
      data = s.loads(token, max_age=3600)
      # token payload should be {'file_id': <id>}
      if isinstance(data, dict) and data.get('file_id') == pf.id:
        authorised = True
    except BadData:
      authorised = False
  if not authorised:
    flash('Not authorised')
    return redirect(url_for('login'))
  import os
  path = os.path.join(os.path.dirname(__file__), 'instance', 'uploads', str(pf.patient_id), pf.filename)
  return send_file(path, download_name=pf.original_name, as_attachment=True)


@app.route('/staff/impersonate/<int:patient_id>')
@staff_required
def impersonate_patient(patient_id):
  p = Patient.query.get_or_404(patient_id)
  # set patient session so staff can view dashboard/files
  session['patient_email'] = p.email
  session['patient_id'] = p.id
  # mark who is impersonating for auditing
  session['impersonated_by'] = session.get('staff_email')
  al = AuditLog(actor=session.get('staff_email') or 'staff', action=f"Impersonated patient {p.id}")
  db.session.add(al)
  db.session.commit()
  flash(f'Now impersonating {p.name} — remember to stop when finished')
  return redirect(url_for('dashboard'))


@app.route('/staff/stop-impersonation')
@staff_required
def stop_impersonation():
  # remove patient session that was set by impersonation
  impersonator = session.pop('impersonated_by', None)
  session.pop('patient_email', None)
  session.pop('patient_id', None)
  al = AuditLog(actor=impersonator or session.get('staff_email') or 'staff', action='Stopped impersonation')
  db.session.add(al)
  db.session.commit()
  flash('Stopped impersonation')
  return redirect(url_for('staff_dashboard'))

@app.route('/admin/new-post', methods=['GET', 'POST'])
@admin_required
def new_post():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        slug = title.lower().replace(' ', '-')
        p = BlogPost(title=title, slug=slug, content=content)
        db.session.add(p)
        db.session.commit()
        flash('Post added')
        return redirect(url_for('admin'))
    return "<form method='post'>Title: <input name='title' /><br/>Content:<br/><textarea name='content'></textarea><br/><button>Save</button></form>"

@app.route('/admin/new-faq', methods=['GET', 'POST'])
@admin_required
def new_faq():
    if request.method == 'POST':
        q = request.form.get('q')
        a = request.form.get('a')
        f = FAQ(q=q, a=a)
        db.session.add(f)
        db.session.commit()
        flash('FAQ added')
        return redirect(url_for('admin'))
    return "<form method='post'>Q: <input name='q' /><br/>A:<br/><textarea name='a'></textarea><br/><button>Save</button></form>"


@app.route('/admin/new-staff', methods=['GET', 'POST'])
@admin_required
def new_staff():
  if request.method == 'POST':
    name = request.form.get('name')
    email = request.form.get('email')
    role = request.form.get('role') or 'staff'
    pw = request.form.get('password') or 'changeme'
    if Staff.query.filter_by(email=email).first():
      flash('Staff with this email already exists')
      return redirect(url_for('admin'))
    s = Staff(name=name, email=email, role=role, password_hash=generate_password_hash(pw))
    db.session.add(s)
    db.session.commit()
    flash('Staff account created')
    return redirect(url_for('admin'))
  return "<form method='post'>Name: <input name='name'/><br/>Email: <input name='email'/><br/>Role: <input name='role' value='staff'/><br/>Password: <input name='password'/><br/><button>Create</button></form>"


@app.route('/admin/audit')
@admin_required
def admin_audit():
  entries = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
  return render_template('admin_audit.html', entries=entries)


@app.route('/admin/staff')
@admin_required
def admin_staff():
  staff = Staff.query.order_by(Staff.created_at.desc()).all()
  return render_template('admin_staff.html', staff=staff)


@app.route('/admin/staff/edit/<int:staff_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_staff(staff_id):
  s = Staff.query.get_or_404(staff_id)
  if request.method == 'POST':
    s.name = request.form.get('name')
    s.email = request.form.get('email')
    s.role = request.form.get('role')
    pw = request.form.get('password')
    if pw:
      s.password_hash = generate_password_hash(pw)
    db.session.commit()
    flash('Staff updated')
    return redirect(url_for('admin_staff'))
  return render_template('admin_edit_staff.html', staff=s)


@app.route('/admin/staff/delete/<int:staff_id>', methods=['POST'])
@admin_required
def admin_delete_staff(staff_id):
  s = Staff.query.get_or_404(staff_id)
  db.session.delete(s)
  db.session.commit()
  flash('Staff deleted')
  return redirect(url_for('admin_staff'))


@app.route('/admin/patients')
@admin_required
def admin_patients():
  patients = Patient.query.order_by(Patient.created_at.desc()).all()
  return render_template('admin_patients.html', patients=patients)


@app.route('/admin/patient/edit/<int:patient_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_patient(patient_id):
  p = Patient.query.get_or_404(patient_id)
  if request.method == 'POST':
    p.name = request.form.get('name')
    p.email = request.form.get('email')
    p.phone = request.form.get('phone')
    pw = request.form.get('password')
    if pw:
      p.password_hash = generate_password_hash(pw)
    db.session.commit()
    # audit
    al = AuditLog(actor=session.get('staff_email') or 'admin', action=f'Edited patient {p.id} by admin')
    db.session.add(al)
    db.session.commit()
    flash('Patient updated')
    return redirect(url_for('admin_patients'))
  return render_template('admin_edit_patient.html', patient=p)


@app.route('/admin/patient/delete/<int:patient_id>', methods=['POST'])
@admin_required
def admin_delete_patient(patient_id):
  p = Patient.query.get_or_404(patient_id)
  db.session.delete(p)
  db.session.commit()
  al = AuditLog(actor=session.get('staff_email') or 'admin', action=f'Deleted patient {patient_id} by admin')
  db.session.add(al)
  db.session.commit()
  flash('Patient deleted')
  return redirect(url_for('admin_patients'))

@app.route('/telehealth')
def telehealth():
    return "<h2>Telehealth</h2><p>To book a video visit, use the appointment booking page and choose 'telehealth' in the reason. Zoom link will be sent in confirmation (placeholder).</p>"

@app.route('/risk-quiz', methods=['GET', 'POST'])
def risk_quiz():
    if request.method == 'POST':
        age = int(request.form.get('age', 0))
        bmi = float(request.form.get('bmi', 0))
        score = 0
        if age > 45: score += 1
        if bmi > 30: score += 1
        if request.form.get('family') == 'yes': score += 1
        level = 'Low' if score == 0 else ('Moderate' if score == 1 else 'High')
        return f"<h2>Risk: {level}</h2><p><a href='/resources'>Back</a></p>"
    return """<form method='post'>Age: <input name='age' /><br/>BMI: <input name='bmi' /><br/>Family history? <select name='family'><option value='no'>No</option><option value='yes'>Yes</option></select><br/><button>Check</button></form>"""


@app.route('/about')
def about():
  return render_template('about.html', title='About')

if __name__ == '__main__':
    app.run(debug=True)
