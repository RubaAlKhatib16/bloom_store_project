#import openai
from flask_cors import CORS

#openai.api_key = "YOUR_API_KEY"

from flask import Flask, jsonify, request, render_template
from db import get_db_connection
from apscheduler.schedulers.background import BackgroundScheduler
from scheduler_jobs import check_reminders_and_notify_job
from routes.auth_routes import auth_bp
from routes.flower_routes import flower_bp



from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)

from functools import wraps
import db

app = Flask(__name__)
CORS(app)

app.config["JWT_SECRET_KEY"] = "super-secret-key-change-this"

jwt = JWTManager(app)

blocklist = set()

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    return jwt_payload["jti"] in blocklist

print(db.__file__)

# استيراد Blueprints
from routes.auth_routes import auth_bp
from routes.user_routes import user_bp
from routes.flower_routes import flower_bp
from routes.cart_routes import cart_bp
from routes.order_routes import order_bp
from routes.admin_routes import admin_bp
from routes.reminders import reminders_bp
from routes.img import img_bp
from routes.occasion_routes import occasion_bp
from routes.consultation_routes import consultation_bp
from routes.contact_routes import contact_bp


# تسجيل Blueprints مع prefix للـ API
app.register_blueprint(auth_bp, url_prefix='/api/auth')  
app.register_blueprint(user_bp, url_prefix='/api/user')
app.register_blueprint(flower_bp, url_prefix='/api/flowers')
app.register_blueprint(order_bp, url_prefix='/api/orders')
app.register_blueprint(admin_bp, url_prefix='/api/admin')
app.register_blueprint(reminders_bp, url_prefix='/api/reminders')
app.register_blueprint(img_bp, url_prefix='/api/img')
app.register_blueprint(occasion_bp)
app.register_blueprint(consultation_bp)
app.register_blueprint(cart_bp, url_prefix='/api/cart')
app.register_blueprint(contact_bp)
# Scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_reminders_and_notify_job, trigger="cron", hour=9, minute=0)
scheduler.start()

# ---------------------------
#  صفحات الواجهة (Frontend)
# ---------------------------
@app.route('/')
def home_page():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/signup')
def signup_page():
    return render_template('signup.html')

@app.route('/profile')
def profile_page():
    return render_template('profile.html')

@app.route('/shop')
def shop_page():
    return render_template('shop.html')

@app.route('/categories')
def categories_page():
    return render_template('categories.html')
@app.route('/occasions')
def occasions_page():
    return render_template('occasions.html')
@app.route('/category/<category>')
def category_detail_page(category):
    return render_template('category.html', category=category)

@app.route('/cart')
def cart_page():
    return render_template('cart.html')

@app.route('/product/<int:flower_id>')
def product_page(flower_id):
    return render_template('product.html')

@app.route('/consultation')
def consultation_page():
    return render_template('consultation.html')


@app.route('/order-confirmation/<int:order_id>')
def order_confirmation(order_id):
    return render_template('order-confirmation.html', order_id=order_id)

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/status')
def status():
    return "Smart Bloom Store Backend is running"

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)