import json
import os
import threading
import time
from typing import Dict, Optional, Set

from flask import Flask, abort, redirect, render_template_string, request, send_from_directory, url_for
from werkzeug.serving import make_server


CAT_MAP = {
    "1": "cat_1",
    "2": "cat_2",
    "3": "cat_3",
    "4": "cat_4",
}

ACTIVITY_MAP = {
    "1": "eating",
    "2": "drinking",
    "3": "playing",
    "4": "grooming",
    "5": "sleeping",
}


def _load_queue_meta(queue_path: str) -> Dict[str, dict]:
    if not os.path.exists(queue_path):
        return {}
    meta = {}
    with open(queue_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            clip_id = entry.get("clip_id")
            if clip_id:
                meta[clip_id] = entry
    return meta


def _load_labeled_ids(labels_path: str) -> Set[str]:
    if not os.path.exists(labels_path):
        return set()
    ids = set()
    with open(labels_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            clip_id = entry.get("clip_id")
            if clip_id:
                ids.add(clip_id)
    return ids


class WebReviewServer:
    def __init__(self, queue_dir: str, host: str, port: int):
        self.queue_dir = queue_dir
        self.host = host
        self.port = port
        self.queue_path = os.path.join(queue_dir, "queue.jsonl")
        self.labels_path = os.path.join(queue_dir, "labels.jsonl")
        os.makedirs(queue_dir, exist_ok=True)

        self.app = Flask(__name__)
        self._server = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        self._register_routes()

    def _register_routes(self):
        app = self.app

        @app.route("/")
        def index():
            clip_id, clip_path, entry = self._next_clip()
            if not clip_id:
                return "No clips in queue", 200
            pred_activity = entry.get("pred_activity", "")
            pred_conf = float(entry.get("pred_conf", 0.0))
            return render_template_string(
                _HTML_TEMPLATE,
                clip_id=clip_id,
                video_url=url_for("clip_file", filename=f"{clip_id}.mp4"),
                pred_activity=pred_activity,
                pred_conf=f"{pred_conf:.2f}",
            )

        @app.route("/clip/<path:filename>")
        def clip_file(filename):
            return send_from_directory(self.queue_dir, filename, as_attachment=False)

        @app.post("/label")
        def label():
            clip_id = request.form.get("clip_id", "")
            cat_key = request.form.get("cat_id", "")
            act_key = request.form.get("activity", "")
            if not clip_id or cat_key not in CAT_MAP or act_key not in ACTIVITY_MAP:
                abort(400)

            label = {
                "clip_id": clip_id,
                "clip_path": os.path.join(self.queue_dir, f"{clip_id}.mp4"),
                "cat_id": CAT_MAP[cat_key],
                "activity": ACTIVITY_MAP[act_key],
                "ts": time.time(),
            }
            self._append_label(label)
            return redirect(url_for("index"))

        @app.post("/skip")
        def skip():
            clip_id = request.form.get("clip_id", "")
            if not clip_id:
                abort(400)
            label = {
                "clip_id": clip_id,
                "skip": True,
                "ts": time.time(),
            }
            self._append_label(label)
            return redirect(url_for("index"))

    def _append_label(self, label: dict):
        with self._lock:
            with open(self.labels_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(label, ensure_ascii=False) + "\n")

    def _next_clip(self):
        meta = _load_queue_meta(self.queue_path)
        labeled = _load_labeled_ids(self.labels_path)
        clips = sorted(f for f in os.listdir(self.queue_dir) if f.endswith(".mp4"))
        for name in clips:
            clip_id = os.path.splitext(name)[0]
            if clip_id in labeled:
                continue
            entry = meta.get(clip_id, {})
            return clip_id, os.path.join(self.queue_dir, name), entry
        return None, None, {}

    def start(self):
        if self._thread:
            return
        self._server = make_server(self.host, self.port, self.app)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        print(f"[WebReview] http://{self.host}:{self.port}")

    def stop(self):
        if self._server:
            self._server.shutdown()
        if self._thread:
            self._thread.join(timeout=2.0)
        self._server = None
        self._thread = None


def start_web_review_server(config: dict, base_dir: str) -> Optional[WebReviewServer]:
    cfg = config.get("review_web", {})
    if not cfg.get("enabled", False):
        return None

    queue_dir = cfg.get("queue_dir") or config.get("review", {}).get("queue_dir", "../data/review_queue")
    if not os.path.isabs(queue_dir):
        queue_dir = os.path.abspath(os.path.join(base_dir, queue_dir))

    host = cfg.get("host", "0.0.0.0")
    port = int(cfg.get("port", 10025))

    server = WebReviewServer(queue_dir=queue_dir, host=host, port=port)
    server.start()
    return server


_HTML_TEMPLATE = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>CatCam Review</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 12px; }
      video { width: 100%; max-width: 720px; background: #000; }
      .row { margin: 8px 0; }
      button { padding: 10px 14px; margin: 4px; }
      .hint { color: #555; font-size: 14px; }
    </style>
  </head>
  <body>
    <h3>CatCam Review</h3>
    <div class="row">Clip: {{ clip_id }}</div>
    <div class="row hint">Pred: {{ pred_activity }} ({{ pred_conf }})</div>
    <video controls autoplay muted playsinline>
      <source src="{{ video_url }}" type="video/mp4">
    </video>
    <form method="post" action="/label">
      <input type="hidden" name="clip_id" value="{{ clip_id }}">
      <div class="row">
        <div>Cat:</div>
        <label><input type="radio" name="cat_id" value="1" required> 1 - Kaktus</label>
        <label><input type="radio" name="cat_id" value="2"> 2 - Plut</label>
        <label><input type="radio" name="cat_id" value="3"> 3 - Whisky</label>
        <label><input type="radio" name="cat_id" value="4"> 4 - Soda</label>
      </div>
      <div class="row">
        <div>Activity:</div>
        <label><input type="radio" name="activity" value="1" required> eating</label>
        <label><input type="radio" name="activity" value="2"> drinking</label>
        <label><input type="radio" name="activity" value="3"> playing</label>
        <label><input type="radio" name="activity" value="4"> grooming</label>
        <label><input type="radio" name="activity" value="5"> sleeping</label>
      </div>
      <button type="submit">Save</button>
    </form>
    <form method="post" action="/skip">
      <input type="hidden" name="clip_id" value="{{ clip_id }}">
      <button type="submit">Skip</button>
    </form>
  </body>
</html>
"""
