# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, send_file, render_template_string
import yt_dlp
import os
import uuid
import traceback
import subprocess

app = Flask(__name__)

# 自动适配路径
if os.path.exists("/opt/render/project/src/"):
    COOKIE_FILE = "/opt/render/project/src/cookies.txt"
    # Render 环境：ffmpeg 放在项目根目录的 bin 文件夹
    FFMPEG_PATH = "/opt/render/project/src/bin/ffmpeg"
else:
    COOKIE_FILE = "cookies.txt"
    # 本地环境：直接用系统 ffmpeg
    FFMPEG_PATH = "ffmpeg"

DOWNLOAD_FOLDER = "/tmp/downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# 前端页面（不变）
INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube → MP3 转换器</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        body {
            background: #121212;
            color: #fff;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            width: 100%;
            max-width: 600px;
        }
        h1 {
            text-align: center;
            color: #ff0000;
            margin-bottom: 30px;
            font-size: 2.5rem;
        }
        #url-input {
            width: 100%;
            padding: 16px;
            margin-bottom: 16px;
            border-radius: 12px;
            border: 2px solid #333;
            background: #1e1e1e;
            color: #fff;
            font-size: 1.2rem;
            outline: none;
            transition: border 0.2s;
        }
        #url-input:focus {
            border-color: #ff0000;
        }
        #convert-btn {
            width: 100%;
            padding: 16px;
            background: #ff0000;
            color: #fff;
            border: none;
            border-radius: 12px;
            font-size: 1.5rem;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
            margin-bottom: 24px;
        }
        #convert-btn:hover {
            background: #cc0000;
        }
        #status {
            width: 100%;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            font-size: 1.2rem;
            display: none;
        }
        .loading {
            background: #1a1a3a;
            border: 1px solid #3333ff;
            color: #3333ff;
        }
        .success {
            background: #1a3a1a;
            border: 1px solid #33ff33;
            color: #33ff33;
        }
        .error {
            background: #3a1a1a;
            border: 1px solid #ff3333;
            color: #ff3333;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>YouTube → MP3 转换器</h1>
        <input type="text" id="url-input" placeholder="粘贴 YouTube 链接...">
        <button id="convert-btn">转换为 MP3</button>
        <div id="status"></div>
    </div>

    <script>
        const urlInput = document.getElementById('url-input');
        const convertBtn = document.getElementById('convert-btn');
        const status = document.getElementById('status');

        convertBtn.addEventListener('click', async () => {
            const url = urlInput.value.trim();
            if (!url) {
                status.textContent = "❌ 请输入有效的 YouTube 链接";
                status.className = "error";
                status.style.display = "block";
                return;
            }

            status.textContent = "🔄 转换中，请稍候...";
            status.className = "loading";
            status.style.display = "block";

            try {
                const res = await fetch('/convert', {
                    method: "POST",
                    headers: { 
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({ url })
                });

                const contentType = res.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {
                    const errorText = await res.text();
                    throw new Error(`后端返回非JSON：${errorText.substring(0, 100)}`);
                }

                const data = await res.json();
                if (!res.ok) throw new Error(data.error || "转换失败");

                status.textContent = `✅ 成功！正在下载：${data.title}`;
                status.className = "success";
                const a = document.createElement('a');
                a.href = `/download/${data.file_id}`;
                a.download = data.filename;
                a.click();
            } catch (err) {
                status.textContent = `❌ 错误：${err.message}`;
                status.className = "error";
                console.error("详细错误：", err);
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

@app.route("/convert", methods=["POST"])
def convert():
    try:
        data = request.json
        if not data or not data.get("url"):
            return jsonify({"error": "请输入有效的YouTube链接"}), 400

        # 检查Cookie文件
        if not os.path.exists(COOKIE_FILE):
            return jsonify({"error": f"❌ 未找到Cookie文件！路径：{COOKIE_FILE}"}), 500
        if os.path.getsize(COOKIE_FILE) < 100:
            return jsonify({"error": "❌ Cookie文件为空，请重新导出有效的Cookie"}), 500

        # 检查ffmpeg是否存在
        if not os.path.exists(FFMPEG_PATH) and FFMPEG_PATH != "ffmpeg":
            return jsonify({"error": f"❌ 未找到ffmpeg！路径：{FFMPEG_PATH}"}), 500

        file_id = str(uuid.uuid4())
        outtmpl = f"{DOWNLOAD_FOLDER}/{file_id}.%(ext)s"

        # 核心配置：指定ffmpeg路径，兼容所有格式
        ydl_opts = {
            "format": "bestaudio/best",
            "ffmpeg_location": FFMPEG_PATH,
            "postprocessors": [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "cookiefile": COOKIE_FILE,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "mweb", "ios"],
                }
            },
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(data["url"], download=True)
            mp3_path = f"{DOWNLOAD_FOLDER}/{file_id}.mp3"

        return jsonify({
            "title": info.get("title", "YouTube音频"),
            "file_id": file_id,
            "filename": f"{info.get('title', '音频')}.mp3"
        })
    except Exception as e:
        error_msg = str(e)
        app.logger.error(f"转换失败：{error_msg}")
        traceback.print_exc()
        if len(error_msg) > 500:
            error_msg = error_msg[:500] + "..."
        return jsonify({"error": error_msg}), 500

@app.route("/download/<file_id>")
def download(file_id):
    try:
        mp3_path = f"{DOWNLOAD_FOLDER}/{file_id}.mp3"
        if os.path.exists(mp3_path):
            return send_file(mp3_path, as_attachment=True)
        for file in os.listdir(DOWNLOAD_FOLDER):
            if file.startswith(file_id) and file.endswith(".mp3"):
                return send_file(os.path.join(DOWNLOAD_FOLDER, file), as_attachment=True)
        return jsonify({"error": "MP3文件未找到"}), 404
    except Exception as e:
        return jsonify({"error": f"下载失败：{str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 9000)), debug=False)
