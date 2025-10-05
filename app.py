# app.py
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import os
import datetime
from functools import wraps
# App config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "viclink.db")
app = Flask(__name__)
app.config["SECRET_KEY"] = "viclink_secret"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///viclink.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
# Models
class Plan(db.Model):

    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    max_receivers = db.Column(db.Integer, nullable=False)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
class Connection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(30), default="pending")
# Helpers
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
       token = request.headers.get("x-access-token")
       if not token:
         return jsonify({"error": "Token is missing!"}), 401
       try:
        data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        current_user = User.query.get(data["id"])
       except:
        return jsonify({"error": "Token is invalid or expired!"}), 401
       return f(current_user, *args, **kwargs)
    return decorated
# Auth Routes
@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    if not data or not data.get("username") or not data.get("password"):
       return jsonify({"error": "Username and password required"}), 400
    if User.query.filter_by(username=data["username"]).first():
       return jsonify({"error": "User already exists"}), 400
    hashed_pw = generate_password_hash(data["password"], method="sha256")
    new_user = User(username=data["username"], password=hashed_pw)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User created successfully !","plan": "personal"})
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    User = User.query.filter_by(username=data["username"]).first()
    if not user or not check_password_hash(user.password, data["password"]):
       return jsonify({"error": "Invalid credentials"}), 400
    token = jwt.encode({"id": user.id, "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)}, app.config["SECRET_KEY"], algorithm="HS256")
    return jsonify({"token": token})
# Connection Routes
@app.route("/connection/request/<int:user_id>", methods=["POST"])
@token_required
def send_request(current_user, user_id):
     if current_user.id == user_id:
         return jsonify({"error": "You cannot connect with yourself"}), 400
     existing = Connection.query.filter_by(sender_id=current_user.id,receiver_id=user_id).first()
     if existing:
        return jsonify({"error": "Request already send"}), 400
     request_conn = Connection(sender_id=current_user.id, receiver_id=user_id)
     db.session.add(request_conn)
     db.session.commit()
     return jsonify({"message": "Connection request sent!"})
@app.route("/connection/respond/<int:request_id>", methods=["POST"])
@token_required
def respond_request(current_user, request_id):
    data = request.json
    req = connection_query.get(request_id)
    if not req or req.receiver_id !=current_user.id:
        return jsonify({"error": "Request not found"}), 404
    if data.get("action") not in ["accept", "reject"]:
        return jsonify({"error": "Invalid action"}), 400
    req.status = "accepted" if data["action"] == "accept" else "rejected"
    db.session.commit()
    return jsonify({"message": f"Request {req.status}!"})
@app.route("/connection/incoming", methods=["GET"])
@token_required
def incoming_requests(current_user):
     req = Connection.query.filter_by(receiver_id=current_user.id,status="pending").all()
     return jsonify([{"id": r.id, "from": r.sender_id, "status": r.status} for r in reqs])
@app.route("/friends", methods=["GET"])
@token_required
def friends_list(current_user):
    connection = Connection.query.filter(((Connection.sender_id == current_user.id) | (Connection.receiver_id == current_user.id)) & (Connection.status == "accepted")).all()
    friends = []
    for c in connection:
     friend_id = c.receiver_id if c.sender_id == current_user.id else c.sender_id
     friend = User.query.get(friend_id)
     friends.append({"id": friend.id, "username": friend.username})
    return jsonify(friends)
@app.route("/plans",methods=["GET"])
def list_plans():
    plans = Plan.query.all()
    return jsonify([{"id": p.id, "name": p.name, "price": p.price, "max_receivers": p.max_receivers} for p in plans])
@app.route("/use-friend-internet/<int:friend_id>", methods=["POST"])
@token_required
def use_friend_internt(current_user, friend_id):
    friend = User.query.get(friend_id)
    if not friend:
      return jsonify({"error": "Friend not found"}), 404
    active_receivers = Connection.query.filter_by(sender_id=friend.id, status="accepted").count()
    if active_receivers >=friend.plan.max_receivers:
      return jsonify({"error": f"{friend.username}`s {friend.plan.name} plan limit reached"}),403
      return jsonify({"message": f"You are now connected to {friend_id}`s internet via viclink","plan": friend.plan.name,"max_receivers": friend.plan.max_receivers})
@app.route("/config", methods=["GET", "POST"])
@token_required
def config_settings(current_user):
    if request.method == "POST":
      data = request.json
      return jsonify({"message": "Settings saved", "data": data})
    return jsonify({"theme": "blue-white", "notifications": True})
@app.route('/')
def home():
    return jsonify({"message": "Flask is working"})
@app.route("/Viclink")
def Viclink():
   return jsonify({"message": "welcome to viclink"})
if __name__ == "__main__":
   with app.app_context():
     db.drop_all()
     db.create_all()
     if not Plan.query.first():
       personal = Plan(name="personal",price=400, max_receivers=1)
       friends = Plan(name="Friends", price=700, max_receivers=3)
       db.session.add_all([personal, friends])
       db.session.commit()
       print("plans added succefuly!")
   app.run(debug=True, host="0.0.0.0", port=5000)

