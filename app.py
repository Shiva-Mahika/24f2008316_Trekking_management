from flask import Flask,render_template,request,redirect,session,url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime,timedelta
from werkzeug.security import check_password_hash,generate_password_hash
import os


app=Flask(__name__)
app.config['SECRET_KEY']="pass"
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///placement.db'
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
    def set_password(self,raw):
        self.password_hash=generate_password_hash(raw)
    def check_password(self,raw):
        return check_password_hash(self.password_hash, raw)
class Trek(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    trek_name=db.Column(db.String(20),unique=True,nullable=False)
    trek_location=db.Column(db.String(50),unique=True,nullable=False)
    Difficulty=db.Column(db.String(10))
    duration=db.Column(db.Integer,nullable=False)
    number_slots=db.Column(db.Integer,nullable=False)
    staff_id = db.Column(
        db.Integer,
        db.ForeignKey('staff.id'),
        nullable=False
    )
    bookings = db.relationship('Booking', backref='trek', lazy=True)
class Booking(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)
    trek_id=db.Column(db.Integer,db.ForeignKey('trek.id'),nullable=False)
    status=db.Column(db.String(80),nullable=False,default='pending')
    payment_status=db.Column(db.String(80),nullable=False)
    booked_at=db.Column(db.DateTime,default=datetime.now)
class Staff(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(20),unique=True,nullable=False)
    ph_number=db.Column(db.String(20),unique=True)
    status=db.Column(db.String(10),nullable=False)
    treks = db.relationship('Trek', backref='staff', lazy=True)
    

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
        if user.role=='staff' and user.status!='approved':
            return render_template('login.html',error='Your account is pending approval')
        session['user_id']=user.id
        session['role']=user.role
        session['name']=user.name
        if user.role=='admin':
            return redirect(url_for('admin_dashboard'))
        elif user.role=='staff':
            return redirect(url_for('staff_dashboard'))
        else:
            return redirect(url_for('custamer_dashboard'))
        
    return render_template("login.html")
@app.route("/admin_dashboard")
def admin_dashboard():
    staff=User.query.filter_by(role="staff")
    customer=User.query.filter_by(role="customer")
    return render_template('admin_dash.html', staff_list=staff,Customer_list=customer)
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route("/staff_dashboard")
def company_dashboard():
    return render_template('company_dash.html')




@app.route("/customer_dashboard")
def student_dashboard():
    return render_template('student_dash.html')
 
@app.route("/update_profile",methods=['GET','POST'])
def update_profile():
    if request.method=='POST':
        name=request.form.get('name'," ").strip()
        email=request.form.get('email'," ").strip()
        password=request.form.get('password'," ")
        ph_number=request.form.get('ph_number')
        user=User(name=name, email=email,ph_number=ph_number)
        user.set_password(password)

        
        db.session.add(user)
        db.session.commit()
        return redirect("/")
    return render_template('update_profile.html')




@app.route("/register",methods=['GET','POST'])
def register():
    if request.method=='POST':
        role=request.form.get('role')
        name=request.form.get('name'," ").strip()
        email=request.form.get('email'," ").strip()
        password=request.form.get('password'," ")
        ph_number=request.form.get('ph_number')
        print(password)
        if not name or not email or not password or role not in ('staff','user'):
            return render_template('index.html')
        exist=User.query.filter_by(email=email).first()
        if exist:
            return render_template("register.html",error="Email already exists")
        user=User(name=name, email=email, role=role,ph_number=ph_number)
        user.set_password(password)

        
        db.session.add(user)
        db.session.commit()
        return redirect("/")
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