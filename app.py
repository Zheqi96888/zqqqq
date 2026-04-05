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

.youtube.com	TRUE	/	TRUE	1809707600	LOGIN_INFO	AFmmF2swRQIhAKVix7XHrRGd15oprx_zsRcpPg3FYJlktzMpy5zRgYH8AiB4ON1VGla9DlrFcED1vTNWtpvKpIxraGgD4dmd3OwkVw:QUQ3MjNmeGFFYzNtNF96RXEydlBkRkNfUVZpS2RHd0JudlZxMk9lY1pBVThLYlVjWTVhQXZXMjdrV0xocTR4VU5SWkotVV94clVTWGlnSjNVby1xZlNLMVlhdTZKUjJwLURMdW1YVTAtdjFMaVBkX2hGei1TRDNnNXVueG1mUGp3eGJNcVZFb1Rhb24wLThNS254dVhSTVdJRGs2bVNRMF93
.youtube.com	TRUE	/	TRUE	1809957291	PREF	tz=Asia.Singapore&f4=4010000
.youtube.com	TRUE	/	FALSE	1809964179	SID	g.a0008gi0U-PIpPyv1nXu3r7nKgLlh9AeMMliZTm55Dcje6FDU9V7x4ELk2ACt1YzEHiBiHJJMwACgYKAb4SARESFQHGX2MiOzrzk7EjlYPXyq51-jrdjBoVAUF8yKqXFkRZbO--R3blijSYfDVK0076
.youtube.com	TRUE	/	TRUE	1809964179	__Secure-1PSID	g.a0008gi0U-PIpPyv1nXu3r7nKgLlh9AeMMliZTm55Dcje6FDU9V7Im0B7nwbGpJL31mly852HQACgYKAb8SARESFQHGX2MiPw8yIyHhWQD9wKI6m3O_ZRoVAUF8yKr35yuvRssABFqOB5DWjCQN0076
.youtube.com	TRUE	/	TRUE	1809964179	__Secure-3PSID	g.a0008gi0U-PIpPyv1nXu3r7nKgLlh9AeMMliZTm55Dcje6FDU9V7eSo46eakwXrLu1STMjAWswACgYKATgSARESFQHGX2MiPtYNpXWNtzMM-jh7DXllMxoVAUF8yKraldAoA8vQm9oQBrMgz2wz0076
.youtube.com	TRUE	/	FALSE	1809964179	HSID	A_LReFYNuPuhA3NKj
.youtube.com	TRUE	/	TRUE	1809964179	SSID	AzZven4j88HS3Rt2z
.youtube.com	TRUE	/	FALSE	1809964179	APISID	tpkBOHxGjZkAgZ9E/AkFDLrBCTB0dMl_IX
.youtube.com	TRUE	/	TRUE	1809964179	SAPISID	kLvSnagiidCIQ_AA/A-GePGDWOI6VgCzzj
.youtube.com	TRUE	/	TRUE	1809964179	__Secure-1PAPISID	kLvSnagiidCIQ_AA/A-GePGDWOI6VgCzzj
.youtube.com	TRUE	/	TRUE	1809964179	__Secure-3PAPISID	kLvSnagiidCIQ_AA/A-GePGDWOI6VgCzzj
.youtube.com	TRUE	/	TRUE	1806945331	__Secure-1PSIDTS	sidts-CjQBWhotCW4VqE1GWyApZBtVPkcBpFok5zq8p6PPlzoaFvchKLNhA2hhiHFCdMqWuwMNT6xgEAA
.youtube.com	TRUE	/	TRUE	1806945331	__Secure-3PSIDTS	sidts-CjQBWhotCW4VqE1GWyApZBtVPkcBpFok5zq8p6PPlzoaFvchKLNhA2hhiHFCdMqWuwMNT6xgEAA
.youtube.com	TRUE	/	FALSE	1806945331	SIDCC	AKEyXzUfw4-9wo5cSvb6E-U5y3lVuyEi3nSMlBpmE6R59AaLW-QhtvNOOqzIriO04v-yiLoERQ
.youtube.com	TRUE	/	TRUE	1806945331	__Secure-1PSIDCC	AKEyXzXNqiIRnx9YZ8ifDYn2_15VmB_CYiENpPRNdYv2-SgjZoKxhUQczMXChWsRRQIaiZ1qLA
.youtube.com	TRUE	/	TRUE	1806945331	__Secure-3PSIDCC	AKEyXzXN5qvCvL4aHIlwr8JJyaAscZ3PgprBNhdLnLimXzCD29YejWL6lLE87VemBTCfAU6TFw
.youtube.com	TRUE	/	TRUE	1790949286	VISITOR_INFO1_LIVE	J1U9emQQx_s
.youtube.com	TRUE	/	TRUE	1790949286	VISITOR_PRIVACY_METADATA	CgJTRxIEGgAgYg%3D%3D
.youtube.com	TRUE	/	TRUE	0	YSC	V4e1hT3Y8Hw
.youtube.com	TRUE	/	TRUE	1790873304	__Secure-ROLLOUT_TOKEN	CPXQv8HC9tXjEBD3upiQzM-TAxjrpbKd09STAw%3D%3D
"""
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

    # ✅ 自动下载 → 提取音频 → 转 MP3（高音质）
    ydl_opts = {
        "format": "worst",  # 最小视频（一定有声音）
        "outtmpl": out,
        "cookiefile": COOKIE_PATH,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",  # 🔥 直接转 MP3
            "preferredquality": "192", # 🔥 高音质
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
