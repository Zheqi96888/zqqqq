from flask import Flask, request, jsonify, send_file, render_template_string
import yt_dlp
import os
import uuid

app = Flask(__name__)
DOWNLOAD_FOLDER = "/tmp/downloads"
COOKIE_FILE = "/opt/render/project/src/cookies.txt"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube to MP3 转换器</title>
    <style>
        body {
            background: #121212;
            color: #fff;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 550px;
            margin: 50px auto;
            padding: 20px;
        }
        h1 {
            text-align: center;
            color: #ff0000;
            margin-bottom: 30px;
        }
        input {
            width: 100%;
            padding: 14px;
            margin: 10px 0;
            background: #1e1e1e;
            border: 1px solid #333;
            border-radius: 8px;
            color: #fff;
            font-size: 16px;
            box-sizing: border-box;
        }
        button {
            width: 100%;
            padding: 14px;
            background: #ff0000;
            border: none;
            border-radius: 8px;
            color: #fff;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }
        button:hover {
            background: #cc0000;
        }
        #status {
            margin-top: 25px;
            padding: 15px;
            border-radius: 8px;
            font-size: 16px;
            text-align: center;
            display: none;
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
        .loading {
            background: #1a1a3a;
            border: 1px solid #3333ff;
            color: #3333ff;
        }
    </style>
</head>
<body>
    <h1>YouTube 🡢 MP3 转换器</h1>
    <input type="text" id="urlInput" placeholder="粘贴 YouTube 链接...">
    <button id="convertBtn">转换为 MP3</button>
    <div id="status"></div>

    <script>
        const urlInput = document.getElementById('urlInput');
        const convertBtn = document.getElementById('convertBtn');
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
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url })
                });

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
    data = request.json
    url = data.get("url")
    
    if not url:
        return jsonify({"error": "请输入 YouTube 链接"}), 400

    if not os.path.exists(COOKIE_FILE):
        return jsonify({"error": f"❌ 未找到 Cookie 文件！路径：{COOKIE_FILE}"}), 500

    try:
        file_id = str(uuid.uuid4())
        outtmpl = f"{DOWNLOAD_FOLDER}/{file_id}.%(ext)s"

        # ✅ 修复后的核心配置
        ydl_opts = {
            "format": "bestaudio/best",
            "extractaudio": True,
            "audioformat": "mp3",
            "audioquality": "320",
            "outtmpl": outtmpl,
            "quiet": True,
            "noplaylist": True,
            "cookiefile": COOKIE_FILE,
            "no_warnings": True,
            "postprocessor_args": ["-acodec", "libmp3lame"],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            original_filename = ydl.prepare_filename(info)
            mp3_filename = original_filename.rsplit('.', 1)[0] + '.mp3'

        return jsonify({
            "title": info.get("title", "YouTube Audio"),
            "file_id": file_id,
            "filename": f"{info.get('title', 'audio')}.mp3"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download/<file_id>")
def download(file_id):
    for file in os.listdir(DOWNLOAD_FOLDER):
        if file.startswith(file_id) and file.endswith(".mp3"):
            file_path = os.path.join(DOWNLOAD_FOLDER, file)
            return send_file(file_path, as_attachment=True)
    return jsonify({"error": "文件未找到"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 9000)), debug=False)
