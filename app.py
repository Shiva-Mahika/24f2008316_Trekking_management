
from flask import Flask,render_template,request,redirect,session,url_for,send_from_directory,flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from datetime import datetime,timedelta
from werkzeug.security import check_password_hash,generate_password_hash
import os


app=Flask(__name__)
app.config['SECRET_KEY']="pass"
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///Trekking.db'
db=SQLAlchemy(app)

# models
class User(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(80),unique=True,nullable=False)
    email=db.Column(db.String(120),unique=True,nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role=db.Column(db.String(80),nullable=False,default='customer')
    ph_number=db.Column(db.String(15),unique=True)
    bookings=db.relationship('Booking',backref='user',lazy=True)
    is_blacklisted=db.Column(db.Boolean,default=False)
    def set_password(self,raw):
        self.password_hash=generate_password_hash(raw)
    def check_password(self,raw):
        return check_password_hash(self.password_hash, raw)
class Trek(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    trek_name=db.Column(db.String(100),unique=True,nullable=False)
    trek_location=db.Column(db.String(50),unique=True,nullable=False)
    difficulty=db.Column(db.String(10))
    duration=db.Column(db.Integer,nullable=False)
    number_slots=db.Column(db.Integer,nullable=False)
    open_trek=db.Column(db.Boolean,default=True)
    status=db.Column(db.String(10),default="Upcoming")
    staff_id = db.Column(db.Integer,db.ForeignKey('staff.id'),nullable=True)
    bookings = db.relationship('Booking', backref='trek', lazy=True,cascade="all,delete-orphan")
    start_date=db.Column(db.Date,nullable=False)
class Booking(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)
    trek_id=db.Column(db.Integer,db.ForeignKey('trek.id'),nullable=False)
    payment_status=db.Column(db.Boolean,nullable=False,default=False)
    booked_at=db.Column(db.DateTime,default=datetime.now)
    
    status = db.Column(db.String(20), default="Booked", nullable=False)
class Staff(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer,db.ForeignKey('user.id'),unique=True,nullable=False)

    approval = db.Column(db.String(10),nullable=False,default='pending')
    user = db.relationship("User", backref="staff_profile")
    treks = db.relationship('Trek',backref='staff',lazy=True)

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/login",methods=['GET','POST'])
def login():
    if request.method=="POST":
        email=request.form.get('email'," ").strip()
        password=request.form.get('password'," ")
        user=User.query.filter_by(email=email).first()
        if not email or not password:
            return render_template('login.html',error='Fill all fields')
        if not user or not user.check_password(password):
            return render_template('login.html',error='Your password is wrong')
        if user.role == 'staff':
            staff = Staff.query.filter_by(user_id=user.id).first()

            if not staff or staff.approval != 'approved':
                return render_template('login.html',error='Your account is pending approval')

            
        if user.is_blacklisted:
            return render_template('login.html',error='Your account is blacklisted')
        session['user_id']=user.id
        session['role']=user.role
        session['name']=user.name
    
        if user.role=='admin':
            return redirect(url_for('admin_dashboard'))
        elif user.role=='staff':
            return redirect(url_for('staff_dashboard'))
        else:
            return redirect(url_for('customer_dashboard'))
        
    return render_template("login.html")

def logged_in():
    if 'user_id' in session:
        return User.query.get(session["user_id"])
    return None

@app.route("/customer_dashboard")
def customer_dashboard():
    if session.get("role") != "customer":
        return redirect(url_for("index"))

    customer = logged_in()

    query = Trek.query.filter_by(open_trek=True)

    search = request.args.get("search", "").strip()

    if search:
        query = query.filter(
            db.or_(
                Trek.trek_name.ilike(f"%{search}%"),
                Trek.trek_location.ilike(f"%{search}%")
            )
        )

    open_trek = query.all()

    booking_history = Booking.query.filter_by(
        user_id=customer.id
    ).order_by(
        Booking.booked_at.desc()
    ).all()

    return render_template(
        "customer_dash.html",
        customer=customer,
        open_trek=open_trek,
        booking_history=booking_history,
        search=search
    )



@app.route("/book_trek/<int:trek_id>", methods=["POST"])
def book_trek(trek_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.get_or_404(session["user_id"])
    trek = Trek.query.get_or_404(trek_id)

    if not trek.open_trek:
        flash("This trek is no longer open for booking.", "danger")
        return redirect(url_for("customer_dashboard"))

    if trek.number_slots <= 0:
        trek.open_trek = False
        db.session.commit()
        flash("No slots available.", "danger")
        return redirect(url_for("customer_dashboard"))

    existing_booking = Booking.query.filter_by(
        user_id=user.id,
        trek_id=trek.id
    ).first()

    if existing_booking:
        flash("You have already booked this trek.", "warning")
        return redirect(url_for("customer_dashboard"))

    booking = Booking(
        user_id=user.id,
        trek_id=trek.id
    )

    db.session.add(booking)
    trek.number_slots -= 1
    if trek.number_slots == 0:
        trek.open_trek = False

    db.session.commit()

    return redirect(url_for("customer_dashboard"))




@app.route("/admin_dashboard",methods=['GET','POST'])
def admin_dashboard():
    if session.get('role')!="admin":
          return render_template('index.html')
    total_staff=User.query.filter_by(role="staff").count()
    total_customer=User.query.filter_by(role="customer").count()
    total_booking=Booking.query.count()
    total_trek=Trek.query.count()

    pending_req = Staff.query.filter_by(approval='pending').all()
    all_staff = Staff.query.all()
    all_customer=User.query.filter_by(role="customer").all()
    all_booking=Booking.query.all()
    all_trek=Trek.query.all()
    assigned_staff_ids = (
    db.session.query(Trek.staff_id).filter(Trek.staff_id != None).all())
    assigned_staff_ids = [x[0] for x in assigned_staff_ids]

    available_staff = Staff.query.filter(Staff.approval == "approved",~Staff.id.in_(assigned_staff_ids)).all()

    search_query=request.args.get('q','').strip()
    
    search_results_customer=[]
    search_results_staff=[]
    
    if search_query:
        like=f'%{search_query}%'
        search_results_customer=User.query.filter(
            User.role=='customer',
            or_(User.name.like(like), User.email.like(like))).all()
        search_results_staff=User.query.filter(
            User.role=='staff',
            or_(User.name.like(like), User.email.like(like))).all()
        

    return render_template('admin_dash.html'
                           ,total_staff=total_staff,
                           total_customer=total_customer,
                           total_trek=total_trek,
                           total_booking=total_booking,
                           pending_req=pending_req,
                           all_customer=all_customer,
                           all_staff=all_staff,
                           all_booking=all_booking,
                           all_trek=all_trek,
                           available_staff=available_staff,
                           search_query=search_query,
                           search_results_customer=search_results_customer,
                           search_results_staff=search_results_staff,
                           assigned_staff_ids=assigned_staff_ids
                           )



@app.route('/assign_staff/<int:trek_id>', methods=['POST'])
def assign_staff(trek_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))

    staff_id = request.form.get('staff_id')

    trek = Trek.query.get_or_404(trek_id)
    trek.staff_id = int(staff_id)

    db.session.commit()

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/approve_staff/<int:staff_id>',methods=['GET','POST']) 
def approve_staff(staff_id):
    if session.get('role')!='admin':
        return redirect(url_for('index'))
    staff = Staff.query.get_or_404(staff_id)
    staff.approval = 'approved'
    db.session.commit()

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reject_staff/<int:staff_id>',methods=['GET','POST']) 
def reject_staff(staff_id):
    if session.get('role')!='admin':
        return redirect(url_for('index'))
    staff=Staff.query.get_or_404(staff_id)
    staff.approval='rejected'
    staff.user.is_blacklisted=True
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/create_trek',methods=['GET','POST'])
def create_trek():
    if request.method=="POST":
        if session.get("role") != "admin":
            return redirect(url_for("index"))
        name=request.form.get('trek_name'," ").strip()
        location=request.form.get("trek_location").strip()
        difficulty=request.form.get("difficulty")
        duration=request.form.get("duration")
        number_slots=request.form.get("number_slots")


        start_date = datetime.strptime(request.form["start_date"],"%Y-%m-%d").date()
        trek = Trek(trek_name=name,trek_location=location,difficulty=difficulty,duration=int(duration),number_slots=int(number_slots),start_date=start_date)

        db.session.add(trek)
        db.session.commit()
        return redirect(url_for('admin_dashboard'))

    return render_template('create_trek.html')

@app.route('/delete_trek/<int:trek_id>',methods=['GET','POST'])
def delete_trek(trek_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))

    trek = Trek.query.get_or_404(trek_id)

    db.session.delete(trek)
    db.session.commit()

    return redirect(url_for('admin_dashboard'))



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route("/staff_dashboard", methods=["GET", "POST"])
def staff_dashboard():
    if session.get("role") != "staff":
        return render_template("index.html")

    user = logged_in()
    staff = Staff.query.filter_by(user_id=user.id).first()
    my_assigned_trek = Trek.query.filter_by(staff_id=staff.id).first()
    if my_assigned_trek is None:
        return "<h1>No trek assigned yet.<h1>"

    if my_assigned_trek:
        total_booking = Booking.query.filter_by(trek_id=my_assigned_trek.id).count()
    else:
        total_booking = 0
    return render_template(
        "staff_dash.html",
        staff=staff,
        my_assigned_trek=my_assigned_trek,
        total_booking=total_booking
    )
@app.route('/staff/open_closed/<int:trek_id>', methods=['POST'])
def open_or_closed(trek_id):
    if session.get('role') != 'staff':
        return redirect(url_for('index'))

    trek = Trek.query.get_or_404(trek_id)
    trek.open_trek= not trek.open_trek

    db.session.commit()

    return redirect(url_for('staff_dashboard'))

@app.route('/staff/checked_in/<int:booking_id>',methods=['POST'])
def check_in(booking_id):
    if session.get('role')!='staff':
        return redirect(url_for('index'))
    booking=Booking.query.get_or_404(booking_id)
    if booking.status=="Completed":
        flash("trek is alredy Completed", "warning")
        return redirect(url_for('staff_dashboard'))
    booking.status="Checked_in"
    db.session.commit()
    return redirect(url_for('staff_dashboard'))

@app.route("/staff/update_slots/<int:trek_id>", methods=["POST"])
def update_slots(trek_id):
    if session.get("role") != "staff":
        return redirect(url_for("index"))

    user = logged_in()
    staff = Staff.query.filter_by(user_id=user.id).first()

    trek = Trek.query.get_or_404(trek_id)
    slots = request.form.get("number_slots", type=int)
    trek.number_slots = slots
    trek.open_trek = slots > 0

    db.session.commit()

    flash("Slots updated successfully.", "success")
    return redirect(url_for("staff_dashboard"))


@app.route("/staff/update_status/<int:trek_id>", methods=["POST"])
def update_trek_status(trek_id):
    if session.get("role") != "staff":
        return redirect(url_for("index"))

    trek = Trek.query.get_or_404(trek_id)
    status = request.form.get("status")

    trek.status = status

    if status == "Completed":
        for booking in trek.bookings:
            booking.status = "Completed"

    db.session.commit()

    return redirect(url_for("staff_dashboard"))

@app.route("/staff/update_staff_profile",methods=["Get","POST"])
def update_staff_profile():
    user = User.query.get_or_404(session["user_id"])

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        ph_number = request.form.get("number", "").strip()
        password = request.form.get("password", "").strip()

        if name:
            user.name = name

        if email:
            exist = User.query.filter(
                User.email == email,
                User.id != user.id
            ).first()

            if exist:
                flash("Email already exists")
                return redirect(url_for("update_staff_profile"))
            user.email = email

        if ph_number:
            exist_1=User.query.filter(
                User.ph_number==ph_number,
                User.id != user.id).first()
            if exist_1:
                flash("Phone number alreday exists")
                return redirect(url_for("update_staff_profile"))

            user.ph_number = ph_number
        db.session.commit()

        return redirect(url_for("staff_dashboard"))

    return render_template("update_profile.html", user=user)




@app.route("/update_profile", methods=["GET", "POST"])
def update_profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.get_or_404(session["user_id"])

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        ph_number = request.form.get("number", "").strip()
        password = request.form.get("password", "").strip()

        if name:
            user.name = name

        if email:
            exist = User.query.filter(
                User.email == email,
                User.id != user.id
            ).first()

            if exist:
                flash("Email already exists")
                return redirect(url_for("update_profile"))
            user.email = email

        if ph_number:
            exist_1=User.query.filter(
                User.ph_number==ph_number,
                User.id != user.id).first()
            if exist_1:
                flash("Phone number alreday exists")
                return redirect(url_for("update_profile"))

            user.ph_number = ph_number


        if password:
            user.set_password(password)

        db.session.commit()

        return redirect(url_for("customer_dashboard"))

    return render_template("update_profile.html", user=user)


    

@app.route('/admin/update_trek/<int:trek_id>', methods=['GET', 'POST'])
def update_trek(trek_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))

    trek = Trek.query.get_or_404(trek_id)

    if request.method == 'POST':
        trek_name = request.form.get('trek_name', '').strip()
        trek_location = request.form.get('trek_location', '').strip()
        difficulty = request.form.get('difficulty')
        duration = request.form.get('duration', '').strip()
        number_slots = request.form.get('number_slots', '').strip()

        if trek_name:
            trek.trek_name = trek_name

        if trek_location:
            trek.trek_location = trek_location

        if difficulty and difficulty != "Trek Difficulty":
            trek.difficulty = difficulty

        if duration:
            trek.duration = int(duration)

        if number_slots:
            trek.number_slots = int(number_slots)

        db.session.commit()
        return redirect(url_for('admin_dashboard'))

    return render_template('update_trek.html', trek=trek)

    return render_template('update_trek.html', trek=trek)

@app.route('/admin/blacklisted/<int:staff_id>', methods=['POST'])
def blacklisted(staff_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))

    staff = Staff.query.get_or_404(staff_id)
    staff.user.is_blacklisted = not staff.user.is_blacklisted

    db.session.commit()

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/blacklist/<int:customer_id>', methods=['POST'])
def blacklist(customer_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))

    customer = User.query.get_or_404(customer_id)
    customer.is_blacklisted = not customer.is_blacklisted

    db.session.commit()

    return redirect(url_for('admin_dashboard'))


@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':

        role = request.form.get('role')
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        ph_number = request.form.get('ph_number')

        if not name or not email or not password or role not in ('staff', 'customer'):
            return render_template(
                'register.html',
                error='Fill all fields correctly'
            )

        exist = User.query.filter_by(email=email).first()

        if exist:
            return render_template("register.html",error="Email already exists")
        phone_exist = User.query.filter_by(ph_number=ph_number).first()

        if phone_exist:
            return render_template(
                "register.html",
                error="Phone number already exists"
            )

        if role == 'staff':

            user = User(name=name,email=email,role='staff',ph_number=ph_number)
            user.set_password(password)

            db.session.add(user)
            db.session.flush()

            staff = Staff(user_id=user.id,approval='pending')

            db.session.add(staff)

        else:

            user = User(name=name,email=email,role='customer',ph_number=ph_number)
            user.set_password(password)

            db.session.add(user)

        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        Admin=User.query.filter_by(role='admin').first()
        if Admin is None:
            Admin=User(name='admin',email='admin@gmail.com',role='admin')
            Admin.set_password('1234')
            db.session.add(Admin)
            db.session.commit()
    app.run(debug=True)