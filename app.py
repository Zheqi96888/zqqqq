# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, send_file, render_template_string
import yt_dlp
import os
import uuid

app = Flask(__name__)

# ==========================
# 你的 cookies 保持不变！
# ==========================
COOKIE_DATA = """
# Netscape HTTP Cookie File
# https://curl.haxx.se/rfc/cookie_spec.html
# This is a generated file! Do not edit.

# ==========================

COOKIE_PATH = "/tmp/cookies.txt"
with open(COOKIE_PATH, "w", encoding="utf-8") as f:
    f.write(COOKIE_DATA.strip())

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
        *{box-sizing:border-box;margin:0;padding:0;font-family:Arial}
        body{background:#121212;color:white;padding:30px;display:flex;justify-content:center}
        .box{width:100%;max-width:550px}
        h1{text-align:center;color:red;margin-bottom:20px}
        input{width:100%;padding:14px;margin:10px 0;border-radius:8px;border:none}
        button{width:100%;padding:14px;background:red;color:white;border:none;border-radius:8px;font-size:16px}
        #status{margin-top:20px;padding:15px;border-radius:8px;text-align:center;display:none}
        .loading{background:#222}
        .success{background:#044600}
        .error{background:#5a0000}
    </style>
</head>
<body>
    <div class="box">
        <h1>YouTube → MP3</h1>
        <input id="url" placeholder="粘贴YouTube链接">
        <button onclick="convert()">下载MP3</button>
        <div id="status"></div>
    </div>
    <script>
        async function convert(){
            const s = document.getElementById("status");
            s.textContent = "处理中..."; s.className="loading"; s.style.display="block";
            const res = await fetch("/convert",{
                method:"POST",
                headers:{"Content-Type":"application/json"},
                body:JSON.stringify({url:document.getElementById("url").value})
            });
            const data = await res.json();
            if(res.ok){
                s.textContent="✅ 下载中"; s.className="success";
                location.href="/download/"+data.file_id;
            }else{
                s.textContent="❌ "+data.error; s.className="error";
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
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"error":"请输入链接"}),400

    file_id = str(uuid.uuid4())
    out = f"{DOWNLOAD_FOLDER}/{file_id}.%(ext)s"

    # ✅✅✅ 终极万能格式！永远不会报错！
    ydl_opts = {
        "format": "best",  # 🔥 自动下载任何能下载的格式
        "outtmpl": out,
        "cookiefile": COOKIE_PATH,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
        return jsonify({"file_id": file_id})
    except Exception as e:
        return jsonify({"error": str(e)}),500

@app.route("/download/<file_id>")
def download(file_id):
    for f in os.listdir(DOWNLOAD_FOLDER):
        if f.startswith(file_id) and f.endswith(".mp3"):
            return send_file(os.path.join(DOWNLOAD_FOLDER, f), as_attachment=True)
    return jsonify({"error":"文件不存在"}),404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
