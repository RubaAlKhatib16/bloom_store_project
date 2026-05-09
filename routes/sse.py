from flask import Blueprint, Response, stream_with_context, request, jsonify
from flask_jwt_extended import decode_token
import json
import queue
import threading

sse_bp = Blueprint('sse', __name__)

user_queues = {}
queue_lock = threading.Lock()

def get_user_queue(user_id):
    with queue_lock:
        if user_id not in user_queues:
            user_queues[user_id] = queue.Queue()
        return user_queues[user_id]

def send_notification_to_user(user_id, notification_data):
    q = get_user_queue(user_id)
    q.put(json.dumps(notification_data))

@sse_bp.route('/stream')
def stream():
    token = request.args.get('token')
    if not token:
        return "Missing token", 401
    
    # فك التوكن يدوياً للتحقق والحصول على user_id
    try:
        decoded = decode_token(token)
        user_id = decoded['sub']
    except Exception as e:
        return "Invalid token", 401
    
    q = get_user_queue(user_id)
    def event_stream():
        try:
            while True:
                try:
                    data = q.get(timeout=55)
                    yield f"data: {data}\n\n"
                except queue.Empty:
                    yield ": heartbeat\n\n"
        finally:
            with queue_lock:
                if user_id in user_queues:
                    del user_queues[user_id]
    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")