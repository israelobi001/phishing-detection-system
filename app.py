import hashlib
import qrcode
from flask import Flask
from flask import send_file, Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Image 
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import io
from datetime import datetime
from reportlab.lib.utils import ImageReader

# BLOCKCHAIN IMPORTS
from blockchain import initialize_blockchain
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Configuration ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_super_secret_and_unique_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///certificate_auth.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'
login_manager.login_message = "Please log in to access this page."

# Initialize blockchain (will be None if not configured)
blockchain = initialize_blockchain()

# --- Database Models ---
class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    matric_number = db.Column(db.String(20), unique=True, nullable=False)
    date_of_award = db.Column(db.String(50))
    year_of_graduation = db.Column(db.String(10))
    honors = db.Column(db.String(50))
    course_of_study = db.Column(db.String(100), nullable=False, default='Computer Science')
    certificate_hash = db.Column(db.String(100), unique=True, nullable=False)
    certificate_path = db.Column(db.String(255))
    # Blockchain fields
    blockchain_tx_hash = db.Column(db.String(100))
    blockchain_block_number = db.Column(db.Integer)
    on_blockchain = db.Column(db.Boolean, default=False)


def create_default_admin():
    """Creates a default admin if none exists."""
    username = 'admin'
    password = 'securepassword123'
    
    if Admin.query.filter_by(username=username).first() is None:
        admin_user = Admin(username=username)
        admin_user.set_password(password)
        db.session.add(admin_user)
        db.session.commit()
        print(f"Default Admin user '{username}' created successfully!")
    else:
        print(f"Default Admin user '{username}' already exists.")

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))


# --- PDF Generation Function ---
def generate_certificate_pdf(student_data, certificate_hash):
    """
    Generates a professional PDF certificate styled like the sample image.
    Minimalist design with cream background, gold border, centered typography,
    BOUESTI logo, and QR verification code.
    """

    # Define file path
    pdf_filename = f"{student_data['matric_number'].replace('/', '_')}_{certificate_hash[:8]}.pdf"
    file_path = os.path.join('certificates', pdf_filename)

    # Create PDF canvas
    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4  # 595 x 842 points

    # --- COLORS ---
    COLOR_GOLD = colors.HexColor('#C7A008')
    COLOR_BLACK = colors.black
    COLOR_CREAM = colors.HexColor('#FBF7EC')

    # --- BACKGROUND ---
    c.setFillColor(COLOR_CREAM)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # --- BORDER (ornate gold style imitation) ---
    outer_margin = 40
    c.setStrokeColor(COLOR_GOLD)
    c.setLineWidth(3)
    c.rect(outer_margin, outer_margin, width - 2*outer_margin, height - 2*outer_margin, stroke=1, fill=0)

    inner_margin = 52
    c.setLineWidth(1)
    c.rect(inner_margin, inner_margin, width - 2*inner_margin, height - 2*inner_margin, stroke=1, fill=0)

    # --- UNIVERSITY LOGO ---
    logo_path = os.path.join('static', 'images', 'logo.webp')
    if os.path.exists(logo_path):
        logo_size = 70
        c.drawImage(logo_path, width/2 - logo_size/2, height - 150, width=logo_size, height=logo_size, mask='auto')

    # --- UNIVERSITY NAME ---
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(COLOR_BLACK)
    c.drawCentredString(width/2, height - 165, 
        "BAMIDELE OLUMILUA UNIVERSITY OF EDUCATION, SCIENCE AND")
    c.drawCentredString(width/2, height - 200, 
        "TECHNOLOGY, IKERE-EKITI")
    # --- CERTIFICATE TITLE ---
    y = height - 230
    c.setFont("Times-Bold", 24)
    c.setFillColor(COLOR_BLACK)
    c.drawCentredString(width/2, y, "CERTIFICATE OF AWARD")

    # --- SUBTITLE ---
    y -= 45
    c.setFont("Helvetica", 11)
    c.drawCentredString(width/2, y, "THIS CERTIFIES THAT")

    # --- STUDENT NAME ---
    y -= 40
    c.setFont("Times-Bold", 22)
    c.drawCentredString(width/2, y, student_data['full_name'].title())

    # --- BODY TEXT ---
    y -= 35
    c.setFont("Helvetica", 11)
    c.drawCentredString(width/2, y, 
        "having fulfilled all the requirements of the University and has been awarded the degree of")

    # --- DEGREE DETAILS ---
    y -= 45

    course_lower = student_data['course_of_study'].lower()
    if "engineering" in course_lower:
        degree_title = "BACHELOR OF ENGINEERING"
    elif any(word in course_lower for word in ["computer", "mathematics", "science", "physics", "chemistry"]):
        degree_title = "BACHELOR OF SCIENCE"
    elif any(word in course_lower for word in ["education", "teaching"]):
        degree_title = "BACHELOR OF EDUCATION"
    elif any(word in course_lower for word in ["arts", "history", "language"]):
        degree_title = "BACHELOR OF ARTS"
    else:
        degree_title = "BACHELOR OF SCIENCE"

    c.setFont("Times-Bold", 16)
    c.drawCentredString(width/2, y, degree_title)

    y -= 25
    c.setFont("Times-Bold", 14)
    c.drawCentredString(width/2, y, student_data['course_of_study'].upper())

    # --- HONOURS ---
    y -= 20
    c.setFont("Helvetica", 11)
    c.drawCentredString(width/2, y, f"with {student_data['honors']} Honours")

    # --- MATRIC NUMBER ---
    y -= 35
    c.setFont("Helvetica", 10)
    c.drawCentredString(width/2, y, f"Matric No. {student_data['matric_number']}")

    # --- DATE ---
    y -= 50
    try:
        date_obj = datetime.strptime(student_data['date_of_award'], '%Y-%m-%d')
        formatted_date = date_obj.strftime('%d %B, %Y')
    except:
        formatted_date = student_data['date_of_award']

    c.setFont("Helvetica", 10)
    c.drawString(100, y, formatted_date)
    # --- REAL SIGNATURE IMAGE ---
    signature_path = os.path.join('static', 'images', 'vc_signature.png')
    if os.path.exists(signature_path):
        sig_width = 120   # adjust size
        sig_height = 50   # adjust size
        sig_x = width/2 - sig_width/2
        sig_y = y - 35    # place just above the line
        c.drawImage(signature_path, sig_x, sig_y, sig_width, sig_height, mask='auto')

    # --- SIGNATURE LINE ---
    c.setStrokeColor(COLOR_BLACK)
    c.setLineWidth(1)
    c.line(width/2 - 60, y - 40, width/2 + 60, y - 40)
    c.setFont("Helvetica", 9)
    c.drawCentredString(width/2, y - 55, "VICE-CHANCELLOR")

    # --- QR CODE ---
    qr_data = url_for('verify_certificate', hash=certificate_hash, _external=True)
    qr_buffer = io.BytesIO()
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=3,
        border=1,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
    img_qr.save(qr_buffer, 'PNG')
    qr_buffer.seek(0)

    qr_size = 70
    qr_x = width - 130
    qr_y = y - 60
    c.drawImage(ImageReader(qr_buffer), qr_x, qr_y, qr_size, qr_size)

    # --- QR LABEL ---
    c.setFont("Helvetica", 7)
    c.setFillColor(COLOR_BLACK)
    c.drawCentredString(qr_x + qr_size/2, qr_y - 10, "Scan to Verify")

    # --- CERTIFICATE FOOTER ID ---
    c.setFont("Helvetica", 6)
    c.setFillColor(colors.HexColor('#666666'))
    c.drawCentredString(width/2, 45, f"Certificate ID: {certificate_hash[:20].upper()}")

    c.save()
    return file_path



# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/verify', methods=['GET', 'POST'])
def verify_certificate():
    hash_value = None
    
    if request.method == 'GET' and 'hash' in request.args:
        hash_value = request.args.get('hash').strip()
    elif request.method == 'POST':
        hash_value = request.form.get('certificate_hash').strip()
    
    if hash_value:
        if len(hash_value) == 64:
            # Check database first
            student = Student.query.filter_by(certificate_hash=hash_value).first()
            
            # Also check blockchain
            blockchain_result = None
            if blockchain:
                blockchain_result = blockchain.verify_certificate_on_blockchain(hash_value)
            
            return render_template('verification_results.html', 
                                 student=student,
                                 blockchain_result=blockchain_result)
        else:
            student = None
            blockchain_result = None
            return render_template('verification_results.html', 
                                 student=student,
                                 blockchain_result=blockchain_result)
    
    return render_template('verify_certificate.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard_home'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        admin = Admin.query.filter_by(username=username).first()

        if admin and admin.check_password(password):
            login_user(admin, remember=True)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard_home'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('admin_login.html')

@app.route('/dashboard')
@login_required 
def dashboard_home():
    total_certificates = db.session.query(Student).count()
    blockchain_certificates = db.session.query(Student).filter_by(on_blockchain=True).count()
    
    blockchain_total = 0
    if blockchain:
        blockchain_total = blockchain.get_total_certificates()
    
    return render_template(
        'dashboard_overview.html',
        total_certificates=total_certificates,
        blockchain_certificates=blockchain_certificates,
        blockchain_total=blockchain_total,
        blockchain_enabled=blockchain is not None
    )

@app.route('/download/<int:student_id>')
@login_required
def download_certificate(student_id):
    student = Student.query.get_or_404(student_id)
    file_path = student.certificate_path
    
    if not os.path.exists(file_path):
        flash('Error: Certificate file not found on the server.', 'danger')
        return redirect(url_for('view_certificates'))
    
    return send_file(
        file_path, 
        mimetype='application/pdf', 
        as_attachment=True,
        download_name=os.path.basename(file_path)
    )

@app.route('/delete_certificate/<int:student_id>', methods=['POST'])
@login_required
def delete_certificate(student_id):
    student = Student.query.get_or_404(student_id)
    
    try:
        db.session.delete(student)
        db.session.commit()
        flash(f'Record for {student.full_name} (ID: {student_id}) successfully deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting record: {e}', 'danger')
    
    return redirect(url_for('view_certificates'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/upload_certificate', methods=['GET', 'POST'])
@login_required
def upload_certificate_page():
    if request.method == 'POST':
        full_name = request.form.get('full_name').strip()
        matric_number = request.form.get('matric_number').strip()
        year_of_graduation = request.form.get('year_of_graduation').strip()
        date_of_award = request.form.get('date_of_award').strip()
        honors = request.form.get('honors').strip()
        course_of_study = request.form.get('course_of_study').strip()

        if not all([full_name, matric_number, year_of_graduation, date_of_award, honors, course_of_study]):
            flash('Error: All fields are required!', 'danger')
            return redirect(url_for('upload_certificate_page'))
        
        if Student.query.filter_by(matric_number=matric_number).first():
            flash(f'Error: Certificate for Matric No. {matric_number} already exists.', 'danger')
            return redirect(url_for('upload_certificate_page'))

        data_string = f"{full_name}|{matric_number}|{year_of_graduation}|{date_of_award}|{honors}|{course_of_study}"
        certificate_hash = hashlib.sha256(data_string.encode('utf-8')).hexdigest()
        
        student_data = {
            'full_name': full_name,
            'matric_number': matric_number,
            'year_of_graduation': year_of_graduation,
            'date_of_award': date_of_award,
            'honors': honors,
            'course_of_study': course_of_study,
        }

        certificate_path = generate_certificate_pdf(student_data, certificate_hash)

        new_student = Student(
            full_name=full_name,
            matric_number=matric_number,
            year_of_graduation=year_of_graduation,
            date_of_award=date_of_award,
            honors=honors,
            course_of_study=course_of_study,
            certificate_hash=certificate_hash,
            certificate_path=certificate_path
        )

        try:
            db.session.add(new_student)
            db.session.commit()
            
            # Store on blockchain after database save
            if blockchain:
                flash('Certificate saved to database. Storing on blockchain...', 'info')
                blockchain_result = blockchain.store_certificate_on_blockchain(
                    certificate_hash,
                    matric_number
                )
                
                if blockchain_result['success']:
                    # Update student record with blockchain info
                    new_student.blockchain_tx_hash = blockchain_result['tx_hash']
                    new_student.blockchain_block_number = blockchain_result['block_number']
                    new_student.on_blockchain = True
                    db.session.commit()
                    
                    flash(f'✅ Certificate stored on blockchain! Tx: {blockchain_result["tx_hash"][:10]}...', 'success')
                else:
                    flash(f'⚠️ Blockchain storage failed: {blockchain_result["error"]}. Certificate saved in database only.', 'warning')
            else:
                flash('Certificate saved successfully! (Blockchain not configured)', 'success')
            
            return redirect(url_for('upload_success_page', hash_value=certificate_hash))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Database Error: Could not save certificate data. {e}', 'danger')
            return redirect(url_for('upload_certificate_page'))

    return render_template('upload_certificate.html')

@app.route('/upload_success/<hash_value>')
@login_required
def upload_success_page(hash_value):
    student = Student.query.filter_by(certificate_hash=hash_value).first_or_404()
    qr_data = url_for('verify_certificate', hash=student.certificate_hash, _external=True)
    
    return render_template('upload_success.html', student=student, qr_data=qr_data)

@app.route('/qr/<data>')
def generate_qr(data):
    buffer = io.BytesIO()
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H, 
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(buffer, 'PNG')
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='image/png',
        as_attachment=False,
        download_name='qr_code.png'
    )

@app.route('/view_certificates')
@login_required
def view_certificates():
    selected_course = request.args.get('course', '')
    selected_year = request.args.get('year', '')
    
    query = Student.query
    
    if selected_course:
        query = query.filter(Student.course_of_study == selected_course)
    if selected_year:
        query = query.filter(Student.year_of_graduation == selected_year)
    
    students = query.order_by(Student.id.desc()).all()
    
    unique_courses = db.session.query(Student.course_of_study).distinct().order_by(Student.course_of_study).all()
    unique_years = db.session.query(Student.year_of_graduation).distinct().order_by(Student.year_of_graduation.desc()).all()
    
    unique_courses = [c[0] for c in unique_courses]
    unique_years = [y[0] for y in unique_years]
    
    return render_template('view_certificates.html', 
                           students=students,
                           unique_courses=unique_courses,
                           unique_years=unique_years,
                           selected_course=selected_course,
                           selected_year=selected_year)


# --- Run the application ---
if __name__ == '__main__':
    with app.app_context():
        # Create all tables
        db.create_all() 
        create_default_admin()
        
        # Show blockchain status
        if blockchain:
            print(f"\n🔗 BLOCKCHAIN ENABLED")
            print(f"   Account: {blockchain.account_address}")
            print(f"   Contract: {blockchain.contract_address}")
            
            # Try to get balance (may fail if offline)
            try:
                balance = blockchain.get_balance()
                total = blockchain.get_total_certificates()
                print(f"   Balance: {balance} ETH")
                print(f"   Total Certificates on Chain: {total}")
            except Exception as e:
                print(f"   ⚠️  Warning: Cannot connect to blockchain network")
                print(f"   Reason: {str(e)[:80]}...")
                print(f"   App will run but blockchain features will be unavailable")
            print()
        else:
            print("\n⚠️  BLOCKCHAIN NOT CONFIGURED")
            print("   Set environment variables: INFURA_URL, CONTRACT_ADDRESS, PRIVATE_KEY\n")
        
    app.run(debug=True)