
from flask import Flask, jsonify, request, send_from_directory, abort
from flask_cors import CORS
import os, requests, json, base64
from datetime import datetime, timedelta

app = Flask(__name__, static_folder="static")
CORS(app)

HF_API_KEY = os.environ.get("HF_API_KEY")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "WVVj3EZhk1QfAyrlXO0vEkzHNp3AtIQZ")
CACHE_TTL_HOURS = int(os.environ.get("CACHE_TTL_HOURS", "3"))
HF_IMAGE_MODEL = os.environ.get("HF_IMAGE_MODEL", "stabilityai/stable-diffusion-2-1")

_cache = {"time": None, "data": []}

def fetch_english_titles():
    return [
        "AI breakthrough in medical diagnosis",
        "New AI model creates realistic videos",
        "AI translates humor with cultural accuracy"
    ]

def generate_image_hf(prompt):
    if not HF_API_KEY:
        return None
    try:
        url = f"https://api-inference.huggingface.co/models/{HF_IMAGE_MODEL}"
        headers = {"Authorization": f"Bearer {HF_API_KEY}" }
        payload = {"inputs": prompt}
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        if "image" in r.headers.get("Content-Type", ""):
            b64 = base64.b64encode(r.content).decode("ascii")
            return f"data:image/png;base64,{b64}"
    except Exception as e:
        print("HF image error", e)
    return None

def build_news_item(title):
    img = generate_image_hf(title) or ""
    return {"title": title, "text": f"Описание: {title}", "image": img}

def refresh_cache():
    titles = fetch_english_titles()
    news = [build_news_item(t) for t in titles]
    _cache["time"] = datetime.utcnow()
    _cache["data"] = news
    return news

@app.route("/news")
def news():
    if not _cache["time"] or (datetime.utcnow() - _cache["time"]) > timedelta(hours=CACHE_TTL_HOURS):
        refresh_cache()
    return jsonify(_cache["data"])

def require_admin(req):
    token = req.args.get("token") or req.headers.get("X-Admin-Token")
    if token != ADMIN_TOKEN:
        abort(401)

@app.route("/admin/refresh", methods=["POST"])
def admin_refresh():
    require_admin(request)
    news = refresh_cache()
    return jsonify({"status":"ok","items":len(news)})

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/<path:path>")
def static_proxy(path):
    return send_from_directory("static", path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
