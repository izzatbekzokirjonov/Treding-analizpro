import os
import threading
from flask import Flask, send_from_directory

app = Flask(__name__)

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@app.route("/")
def home():
    return "Bot is alive!", 200


@app.route("/health")
def health():
    return {"status": "ok"}, 200


@app.route("/webapp")
def webapp():
    return send_from_directory(_BASE_DIR, "webapp.html")


def run_server():
    port = int(os.getenv("PORT", 3000))
    app.run(host="0.0.0.0", port=port)


def keep_alive():
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
