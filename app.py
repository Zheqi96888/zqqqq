# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, send_file, render_template_string
import yt_dlp
import os
import uuid

app = Flask(__name__)

FFMPEG_PATH = "/opt/render/project/src/bin/ffmpeg"
DOWNLOAD_FOLDER = "/tmp/downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube → MP3</title>
    <style>
        * { box-sizing: border-box; margin:0; padding:0; font-family: Arial, sans-serif; }
        body { background:#121212; color:white; padding:30px; display:flex; justify-content:center; }
        .box { width:100%; max-width:550px; }
        h1 { text-align:center; color:red; margin-bottom:20px; }
        input { width:100%; padding:14px; margin:10px 0; border-radius:8px; border:none; font-size:16px; }
        button { width:100%; padding:14px; background:red; color:white; font-size:18px; border:none; border-radius:8px; cursor:pointer; }
        #status { margin-top:20px; padding:15px; border-radius:8px; text-align:center; display:none; }
        .loading { background:#222; color:#aaa; }
        .success { background:#044600; color:white; }
        .error { background:#5a0000; color:white; }
    </style>
</head>
<body>
    <div class="box">
        <h1>YouTube → MP3</h1>
        <input id="url" placeholder="粘贴YouTube链接">
        <button onclick="convert()">转换为MP3</button>
        <div id="status"></div>
    </div>
    <script>
        async function convert() {
            const url = document.getElementById("url").value.trim();
            const s = document.getElementById("status");
            s.textContent = "转换中...";
            s.className = "loading";
            s.style.display = "block";

            try {
                const res = await fetch("/convert", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ url })
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.error);

                s.textContent = "✅ 下载中...";
                s.className = "success";
                window.location.href = `/download/${data.file_id}`;
            } catch (e) {
                s.textContent = "❌ " + e.message;
                s.className = "error";
            }
        }
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

@app.route("/convert", methods=["POST"])
def convert():
    data = request.json
    url = data.get("url")
    if not url:
        return jsonify({"error":"请输入链接"}), 400

    file_id = str(uuid.uuid4())
    outtmpl = f"{DOWNLOAD_FOLDER}/{file_id}.%(ext)s"

    # ✅✅✅ 终极修复：下载“带声音的最差画质视频”，再转MP3
    ydl_opts = {
        "format": "worst[ext=mp4]/worst",  # 下载最小画质视频（一定有声音）
        "ffmpeg_location": FFMPEG_PATH,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320",
        }],
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "mweb"],
            }
        },
        "nocheckcertificate": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
        return jsonify({"file_id": file_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download/<file_id>")
def download(file_id):
    for f in os.listdir(DOWNLOAD_FOLDER):
        if f.startswith(file_id) and f.endswith(".mp3"):
            path = os.path.join(DOWNLOAD_FOLDER, f)
            return send_file(path, as_attachment=True)
    return jsonify({"error":"文件不存在"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
