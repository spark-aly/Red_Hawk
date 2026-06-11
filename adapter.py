"""
adapter.py — a bridge so Red Hawk can red-team ANY real chatbot.

Red Hawk's fire_at_target sends:   POST {"message": "<attack prompt>"}
                       and reads:   the "response" field of the JSON reply.

Most real chatbots use a different JSON shape. This service speaks Red Hawk's
contract on /attack and forwards each message to a real upstream chatbot
(UPSTREAM_URL), translating the format both ways.

TO TARGET YOUR OWN BOT: edit ONLY the two "# adjust shape" lines below.

Run:
    pip install flask requests
    UPSTREAM_URL=https://your-bot.example.com/chat python adapter.py
    # then put this adapter's public URL (…/attack) into Red Hawk's
    # "Target chatbot URL" box.
"""

import os
import requests
from flask import Flask, request, jsonify


def _clean_env(name: str, default: str = "") -> str:
    """Read an env var with ALL whitespace/newlines collapsed.

    A wrapped copy-paste once put a stray '\\n' inside a URL and broke every
    request, so we defensively strip it here. URLs never contain whitespace.
    """
    return "".join(os.environ.get(name, default).split())


UPSTREAM_URL = _clean_env("UPSTREAM_URL")
PORT = int(_clean_env("PORT", "5002"))

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "upstream": UPSTREAM_URL or "(UPSTREAM_URL not set)"})


@app.route("/attack", methods=["POST"])
def attack():
    # Red Hawk always sends {"message": "<text>"}.
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    if not message:
        return jsonify({"response": "Adapter error: empty 'message' from Red Hawk."}), 400
    if not UPSTREAM_URL:
        return jsonify({"response": "Adapter error: UPSTREAM_URL is not set."}), 500

    try:
        # === adjust shape (1/2): how the UPSTREAM expects the prompt ===========
        # Change this JSON to match your target bot's request body.
        upstream_payload = {"message": message}
        # =======================================================================

        resp = requests.post(
            UPSTREAM_URL,
            json=upstream_payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()

        # === adjust shape (2/2): where the UPSTREAM's reply text lives =========
        # Change this to pull the text out of your target bot's response JSON.
        reply_text = body.get("response", str(body))
        # =======================================================================

        return jsonify({"response": str(reply_text)})

    except Exception as exc:
        # Never crash: hand Red Hawk a clear error in the field it reads, so the
        # failure shows up as an attack result instead of a 500 with no body.
        return jsonify({"response": f"Adapter upstream error: {exc}"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
