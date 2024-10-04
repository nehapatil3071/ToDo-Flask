from flask import Flask, render_template,request, redirect, url_for,session,jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_dance.contrib.google import make_google_blueprint, google
import os
import paypalrestsdk
from dotenv import load_dotenv

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
load_dotenv()

app = Flask(__name__)

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersekrit")

client_id = os.getenv("GOOGLE_CLIENT_ID")
client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

google_bp = make_google_blueprint(client_id=os.getenv("GOOGLE_CLIENT_ID"),
                                  client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
                                  redirect_to="google_login")
app.register_blueprint(google_bp, url_prefix="/login")

paypalrestsdk.configure({
    "mode": "sandbox",
    "client_id": os.getenv("PAYPAL_CLIENT_ID"),
    "client_secret": os.getenv("PAYPAL_CLIENT_SECRET")
})

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db =SQLAlchemy(app)

class Todo(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    desc = db.Column(db.String(500), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"{self.sno} - {self.title}"

@app.route('/', methods=['GET','POST'])
def hello_world():
    user_name = session.get('user_name', None)
    user_photo = session.get('user_photo', None)
    if request.method == 'POST':
        title = request.form['title']
        desc = request.form['desc']
        todo = Todo(title=title ,desc=desc)
        db.session.add(todo)
        db.session.commit()
    allTodo = Todo.query.all()
    return render_template('index.html', allTodo = allTodo,user_name=user_name,user_photo=user_photo)

@app.route('/update/<int:sno>', methods=['GET', 'POST'])
def update(sno):
    if request.method=='POST':
        title = request.form['title']
        desc = request.form['desc']
        todo = Todo.query.filter_by(sno=sno).first()
        todo.title = title
        todo.desc = desc
        db.session.add(todo)
        db.session.commit()
        return redirect("/")
        
    todo = Todo.query.filter_by(sno=sno).first()
    return render_template('update.html', todo=todo)

@app.route('/delete/<int:sno>')
def delete(sno):
    todo = Todo.query.filter_by(sno=sno).first()
    db.session.delete(todo)
    db.session.commit()
    return redirect('/')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        email = request.form['email']
        name = request.form['name']
        address = request.form['address']
        city = request.form['city']
        state = request.form['state']
        zip_code = request.form['zip']

        return redirect('/')

    return render_template('contact.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/pro', methods=['GET', 'POST'])
def pro():
    return render_template('pro.html')


@app.route("/google")
def google_login():
    if not google.authorized:
        return redirect(url_for("google.login"))

    resp = google.get("https://people.googleapis.com/v1/people/me?personFields=names,emailAddresses,photos")

    if not resp.ok:
        app.logger.error(f"Google login failed: {resp.text}")
        return "Failed to retrieve user information", 500

    user_data = resp.json()
    user_name = user_data.get('names', [{}])[0].get('displayName', "Unknown User")
    user_photo = user_data.get('photos', [{}])[0].get('url', None)   
     
    session['user_name'] = user_name
    session['user_photo'] = user_photo
    
    return redirect(url_for("hello_world"))

@app.route('/logout')
def logout():
    session.pop('user_name', None)
    session.pop('user_photo', None)
    return redirect('/')

@app.route('/pay', methods=['POST'])
def pay():
    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal"
        },
        "redirect_urls": {
            "return_url": "http://localhost:5000/payment-success",
            "cancel_url": "http://localhost:5000/payment-cancel"
        },
        "transactions": [{
            "item_list": {
                "items": [{
                    "name": "Pro Subscription",
                    "sku": "pro_subscription",
                    "price": "100.00",
                    "currency": "USD",
                    "quantity": 1
                }]
            },
            "amount": {
                "currency": "USD",
                "total": "100.00"
            },
            "description": "Pro subscription to the app."
        }]
    })

    
    if payment.create():
        print("Payment created successfully")
        return redirect(payment.links[1].href) 
    else:
        print(payment.error)
        return "Error creating payment" + str(payment.error), 400
    
    
@app.route('/payment/execute', methods=['GET'])
def execute_payment():
    payment_id = request.args.get('paymentId')
    payer_id = request.args.get('PayerID')

    payment = paypalrestsdk.Payment.find(payment_id)

    if payment.execute({"payer_id": payer_id}):
        return "Payment executed successfully!"
    else:
        return jsonify({'error': payment.error})

@app.route('/payment/cancel', methods=['GET'])
def payment_cancel():
    return "Payment was cancelled by the user."


if  __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))