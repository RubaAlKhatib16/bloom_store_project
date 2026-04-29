# routes/img.py
from flask import Blueprint

img_bp = Blueprint('img', __name__)

@img_bp.route('/api/img/upload', methods=['POST'])
def upload_image():
    return {"message": "Image upload endpoint"}