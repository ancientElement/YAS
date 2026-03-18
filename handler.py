"""HTTP 请求处理器"""
import http.server
import socketserver
import json
import os
from urllib.parse import urlparse

from config import ROOT, UPLOAD_DIR, MAX_FILE_SIZE, MIME_TYPES
from ffmpeg_utils import compress_video, compress_progress


class CompressHandler(http.server.SimpleHTTPRequestHandler):
    """自定义请求处理器"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def guess_type(self, path):
        ext = os.path.splitext(path)[1].lower()
        return MIME_TYPES.get(ext, 'application/octet-stream')

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        """处理 CORS 预检请求"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        """处理文件上传和压缩请求"""
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/api/compress':
            self.handle_compress()
        else:
            self.send_error(404)

    def handle_compress(self):
        """处理视频压缩请求"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > MAX_FILE_SIZE:
                self.send_json_response(413, {'error': '文件过大，最大支持 500MB'})
                return

            content_type = self.headers.get('Content-Type', '')
            if 'multipart/form-data' not in content_type:
                self.send_json_response(400, {'error': '需要 multipart/form-data'})
                return

            boundary = content_type.split('boundary=')[1].split(';')[0].strip()
            body = self.rfile.read(content_length)
            parts = body.split(b'--' + boundary.encode())

            file_data = None
            filename = 'input.mp4'
            quality = 'medium'

            for part in parts:
                if b'Content-Disposition' not in part:
                    continue

                headers_end = part.find(b'\r\n\r\n')
                if headers_end == -1:
                    continue

                headers = part[:headers_end].decode('utf-8', errors='ignore')
                data = part[headers_end + 4:]
                if data.endswith(b'\r\n'):
                    data = data[:-2]

                if 'name="file"' in headers:
                    file_data = data
                    if 'filename="' in headers:
                        fn = headers.split('filename="')[1].split('"')[0]
                        if fn:
                            filename = fn
                elif 'name="quality"' in headers:
                    quality = data.decode('utf-8').strip()

            if not file_data:
                self.send_json_response(400, {'error': '未找到文件'})
                return

            # 创建临时文件
            temp_id = str(os.urandom(8).hex())
            input_path = os.path.join(UPLOAD_DIR, f'{temp_id}_input.mp4')
            output_path = os.path.join(UPLOAD_DIR, f'{temp_id}_output.mp4')

            with open(input_path, 'wb') as f:
                f.write(file_data)

            print(f"\n[新任务] 开始压缩: {filename} ({len(file_data)/1024/1024:.1f}MB)")

            success, error = compress_video(input_path, output_path, quality, temp_id)

            if not success:
                for p in [input_path, output_path]:
                    if os.path.exists(p):
                        os.remove(p)
                self.send_json_response(500, {'error': f'压缩失败: {error}'})
                return

            with open(output_path, 'rb') as f:
                compressed_data = f.read()

            original_size = os.path.getsize(input_path)
            compressed_size = len(compressed_data)

            # 清理
            for p in [input_path, output_path]:
                if os.path.exists(p):
                    os.remove(p)
            if temp_id in compress_progress:
                del compress_progress[temp_id]

            print(f"[完成] 压缩完成: {filename} -> {compressed_size/1024/1024:.1f}MB\n")

            # 发送响应
            self.send_response(200)
            self.send_header('Content-Type', 'video/mp4')
            self.send_header('Content-Length', str(compressed_size))
            self.send_header('X-Original-Size', str(original_size))
            self.send_header('X-Compressed-Size', str(compressed_size))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(compressed_data)

        except Exception as e:
            import traceback
            print(f"压缩错误: {e}")
            traceback.print_exc()
            self.send_json_response(500, {'error': str(e)})

    def send_json_response(self, code, data):
        """发送 JSON 响应"""
        response = json.dumps(data).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response)

    def handle(self):
        """重写 handle 方法，捕获连接错误"""
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception:
            pass


class SilentTCPServer(socketserver.TCPServer):
    """静默 TCP 服务器"""
    def handle_error(self, request, client_address):
        pass
