#!/usr/bin/env python3
"""
Local File Share Server
- Discoverable on local network via mDNS/Bonjour
- Web interface with drag-and-drop file upload
"""

import os
import socket
from flask import Flask, request, render_template_string, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from zeroconf import ServiceInfo, Zeroconf

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
SHARES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'shares')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SHARES_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SHARES_FOLDER'] = SHARES_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>File Share</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 40px 20px;
            color: #fff;
        }
        h1 {
            margin-bottom: 10px;
            font-size: 2.5rem;
        }
        .subtitle {
            color: #8892b0;
            margin-bottom: 40px;
        }
        .drop-zone {
            width: 100%;
            max-width: 600px;
            min-height: 300px;
            border: 3px dashed #4a5568;
            border-radius: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 40px;
            transition: all 0.3s ease;
            background: rgba(255,255,255,0.02);
            cursor: pointer;
        }
        .drop-zone:hover, .drop-zone.dragover {
            border-color: #667eea;
            background: rgba(102,126,234,0.1);
            transform: scale(1.02);
        }
        .drop-zone-icon {
            font-size: 4rem;
            margin-bottom: 20px;
        }
        .drop-zone-text {
            font-size: 1.2rem;
            color: #a0aec0;
            text-align: center;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 40px;
            font-size: 1.1rem;
            border-radius: 30px;
            cursor: pointer;
            margin-top: 20px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(102,126,234,0.4);
        }
        #fileInput { display: none; }
        .file-list {
            width: 100%;
            max-width: 600px;
            margin-top: 30px;
        }
        .file-item {
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            padding: 15px 20px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .file-name {
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .file-status {
            margin-left: 15px;
            font-size: 0.9rem;
        }
        .status-pending { color: #f6ad55; }
        .status-uploading { color: #63b3ed; }
        .status-done { color: #68d391; }
        .status-error { color: #fc8181; }
        .section-title {
            width: 100%;
            max-width: 600px;
            margin-top: 50px;
            margin-bottom: 20px;
            font-size: 1.5rem;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .downloads-list {
            width: 100%;
            max-width: 600px;
        }
        .download-item {
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            padding: 15px 20px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: background 0.2s;
        }
        .download-item:hover {
            background: rgba(255,255,255,0.1);
        }
        .download-info {
            flex: 1;
            overflow: hidden;
        }
        .download-name {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .download-size {
            color: #8892b0;
            font-size: 0.85rem;
            margin-top: 4px;
        }
        .download-btn {
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
            color: white;
            border: none;
            padding: 10px 20px;
            font-size: 0.9rem;
            border-radius: 20px;
            cursor: pointer;
            text-decoration: none;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .download-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(72,187,120,0.4);
        }
        .empty-msg {
            color: #8892b0;
            text-align: center;
            padding: 30px;
        }
        .refresh-btn {
            background: transparent;
            border: 2px solid #4a5568;
            color: #a0aec0;
            padding: 8px 16px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 0.9rem;
            transition: all 0.2s;
        }
        .refresh-btn:hover {
            border-color: #667eea;
            color: #667eea;
        }
        .progress-bar {
            width: 100%;
            height: 4px;
            background: rgba(255,255,255,0.1);
            border-radius: 2px;
            margin-top: 8px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            width: 0%;
            transition: width 0.3s;
        }
    </style>
</head>
<body>
    <h1>📁 File Share</h1>
    <p class="subtitle">Drop files here to upload</p>
    
    <div class="drop-zone" id="dropZone">
        <div class="drop-zone-icon">📤</div>
        <p class="drop-zone-text">Drag & drop files here<br>or click to select</p>
        <button class="btn" onclick="document.getElementById('fileInput').click()">Choose Files</button>
    </div>
    
    <input type="file" id="fileInput" multiple>
    
    <div class="file-list" id="fileList"></div>

    <div class="section-title">
        <span>📥 Available Downloads</span>
        <button class="refresh-btn" onclick="loadSharedFiles()">Refresh</button>
    </div>
    <div class="downloads-list" id="downloadsList">
        <p class="empty-msg">Loading...</p>
    </div>

    <script>
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        const fileList = document.getElementById('fileList');

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(event => {
            dropZone.addEventListener(event, e => {
                e.preventDefault();
                e.stopPropagation();
            });
        });

        ['dragenter', 'dragover'].forEach(event => {
            dropZone.addEventListener(event, () => dropZone.classList.add('dragover'));
        });

        ['dragleave', 'drop'].forEach(event => {
            dropZone.addEventListener(event, () => dropZone.classList.remove('dragover'));
        });

        dropZone.addEventListener('drop', e => handleFiles(e.dataTransfer.files));
        fileInput.addEventListener('change', e => handleFiles(e.target.files));
        dropZone.addEventListener('click', e => {
            if (e.target.tagName !== 'BUTTON') fileInput.click();
        });

        function handleFiles(files) {
            [...files].forEach(uploadFile);
        }

        function uploadFile(file) {
            const item = document.createElement('div');
            item.className = 'file-item';
            item.innerHTML = `
                <span class="file-name">${file.name}</span>
                <span class="file-status status-uploading">Uploading...</span>
                <div class="progress-bar"><div class="progress-fill"></div></div>
            `;
            fileList.appendChild(item);

            const progressFill = item.querySelector('.progress-fill');
            const status = item.querySelector('.file-status');

            const formData = new FormData();
            formData.append('file', file);

            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/upload', true);

            xhr.upload.onprogress = e => {
                if (e.lengthComputable) {
                    const pct = (e.loaded / e.total) * 100;
                    progressFill.style.width = pct + '%';
                }
            };

            xhr.onload = () => {
                if (xhr.status === 200) {
                    status.textContent = '✓ Done';
                    status.className = 'file-status status-done';
                } else {
                    status.textContent = '✗ Error';
                    status.className = 'file-status status-error';
                }
            };

            xhr.onerror = () => {
                status.textContent = '✗ Error';
                status.className = 'file-status status-error';
            };

            xhr.send(formData);
        }

        function formatSize(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
        }

        function loadSharedFiles() {
            fetch('/shares')
                .then(r => r.json())
                .then(files => {
                    const list = document.getElementById('downloadsList');
                    if (files.length === 0) {
                        list.innerHTML = '<p class="empty-msg">No files available for download</p>';
                        return;
                    }
                    list.innerHTML = files.map(f => `
                        <div class="download-item">
                            <div class="download-info">
                                <div class="download-name">${f.name}</div>
                                <div class="download-size">${formatSize(f.size)}</div>
                            </div>
                            <a href="/shares/${encodeURIComponent(f.name)}" class="download-btn" download>Download</a>
                        </div>
                    `).join('');
                })
                .catch(() => {
                    document.getElementById('downloadsList').innerHTML = '<p class="empty-msg">Error loading files</p>';
                });
        }

        loadSharedFiles();
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    filename = secure_filename(file.filename)
    # Handle duplicate filenames
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    base, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(filepath):
        filename = f"{base}_{counter}{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        counter += 1
    
    file.save(filepath)
    print(f"📥 Received: {filename}")
    return jsonify({'success': True, 'filename': filename})

@app.route('/shares')
def list_shares():
    """List all files in the shares folder"""
    files = []
    shares_path = app.config['SHARES_FOLDER']
    for filename in os.listdir(shares_path):
        filepath = os.path.join(shares_path, filename)
        if os.path.isfile(filepath):
            files.append({
                'name': filename,
                'size': os.path.getsize(filepath)
            })
    files.sort(key=lambda x: x['name'].lower())
    return jsonify(files)

@app.route('/shares/<path:filename>')
def download_file(filename):
    """Download a file from shares folder"""
    return send_from_directory(
        app.config['SHARES_FOLDER'],
        filename,
        as_attachment=True
    )

def get_local_ip():
    """Get the local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def register_mdns(port):
    """Register service for network discovery"""
    local_ip = get_local_ip()
    hostname = socket.gethostname()
    
    service_info = ServiceInfo(
        "_http._tcp.local.",
        f"FileShare ({hostname})._http._tcp.local.",
        addresses=[socket.inet_aton(local_ip)],
        port=port,
        properties={'path': '/'},
    )
    
    zeroconf = Zeroconf()
    zeroconf.register_service(service_info)
    print(f"📡 Service registered as 'FileShare ({hostname})' on local network")
    return zeroconf, service_info

if __name__ == '__main__':
    PORT = 8080
    local_ip = get_local_ip()
    
    print("\n" + "="*50)
    print("  📁 FILE SHARE SERVER")
    print("="*50)
    print(f"\n  Local URL:   http://localhost:{PORT}")
    print(f"  Network URL: http://{local_ip}:{PORT}")
    print(f"\n  Uploads saved to: {UPLOAD_FOLDER}")
    print(f"  Shared files from: {SHARES_FOLDER}")
    print("\n  Open the URL above on any device in your network")
    print("="*50 + "\n")
    
    # Register mDNS service for discovery
    zeroconf, service_info = register_mdns(PORT)
    
    try:
        app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)
    finally:
        zeroconf.unregister_service(service_info)
        zeroconf.close()
