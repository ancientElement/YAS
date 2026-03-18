#!/usr/bin/env python3
"""
iPhone 压缩工具 - FFmpeg 服务器端压缩方案
作用：提供静态文件服务 + 视频压缩 API
优点：支持音频、压缩质量高、速度快（相对前端）
缺点：需要上传/下载文件
"""

import http.server
import socketserver
import os
import socket
import json
import subprocess
import tempfile
import shutil
from urllib.parse import parse_qs, urlparse

# 配置
PORT = 3000
ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(ROOT, 'temp')
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB 限制

# 确保临时目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)

# MIME 类型映射
MIME_TYPES = {
    '.html': 'text/html',
    '.css': 'text/css',
    '.js': 'application/javascript',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.ico': 'image/x-icon',
    '.svg': 'image/svg+xml',
    '.json': 'application/json',
    '.mp4': 'video/mp4',
    '.webm': 'video/webm',
    '.mov': 'video/quicktime'
}


def get_local_ips():
    """获取本机所有 IP 地址"""
    try:
        ips = []
        hostname = socket.gethostname()
        try:
            addr = socket.gethostbyname(hostname)
            if addr and addr != '127.0.0.1':
                ips.append(addr)
        except:
            pass
        
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0)
            try:
                s.connect(('8.8.8.8', 80))
                ip = s.getsockname()[0]
                if ip != '127.0.0.1' and ip not in ips:
                    ips.append(ip)
            except:
                pass
            finally:
                s.close()
        except:
            pass
        
        return ips if ips else ['localhost']
    except Exception:
        return ['localhost']


def compress_video(input_path, output_path, quality='medium'):
    """
    使用 FFmpeg 压缩视频
    quality: low(0.5), medium(0.7), high(0.9) 对应尺寸比例
    """
    # 质量参数映射
    scale_map = {
        'low': 'iw*0.5:ih*0.5',
        'medium': 'iw*0.7:ih*0.7',
        'high': 'iw*0.9:ih*0.9'
    }
    scale = scale_map.get(quality, 'iw*0.7:ih*0.7')
    
    # FFmpeg 命令
    cmd = [
        'ffmpeg',
        '-i', input_path,
        '-vf', f'scale={scale}',
        '-c:v', 'libx264',
        '-preset', 'fast',  # 压缩速度预设
        '-crf', '23',       # 质量 (0-51, 越小越好)
        '-c:a', 'aac',
        '-b:a', '128k',
        '-movflags', '+faststart',  # 优化网络播放
        '-y',               # 覆盖输出文件
        output_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(f"FFmpeg error: {result.stderr}")
            return False, result.stderr
        return True, None
    except subprocess.TimeoutExpired:
        return False, "压缩超时"
    except Exception as e:
        return False, str(e)


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
            # 获取 Content-Length
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > MAX_FILE_SIZE:
                self.send_json_response(413, {'error': '文件过大，最大支持 500MB'})
                return
            
            # 读取 multipart 数据
            content_type = self.headers.get('Content-Type', '')
            if 'multipart/form-data' not in content_type:
                self.send_json_response(400, {'error': '需要 multipart/form-data'})
                return
            
            # 解析 boundary
            boundary = content_type.split('boundary=')[1].split(';')[0].strip()
            
            # 读取请求体
            body = self.rfile.read(content_length)
            
            # 解析表单数据
            parts = body.split(b'--' + boundary.encode())
            
            file_data = None
            filename = 'input.mp4'
            quality = 'medium'
            
            for part in parts:
                if b'Content-Disposition' not in part:
                    continue
                
                # 分离头部和数据
                headers_end = part.find(b'\r\n\r\n')
                if headers_end == -1:
                    continue
                
                headers = part[:headers_end].decode('utf-8', errors='ignore')
                data = part[headers_end + 4:]
                
                # 去除末尾的 \r\n
                if data.endswith(b'\r\n'):
                    data = data[:-2]
                
                if 'name="file"' in headers:
                    file_data = data
                    # 提取文件名
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
            
            # 保存上传的文件
            with open(input_path, 'wb') as f:
                f.write(file_data)
            
            # 压缩视频
            success, error = compress_video(input_path, output_path, quality)
            
            if not success:
                # 清理临时文件
                for p in [input_path, output_path]:
                    if os.path.exists(p):
                        os.remove(p)
                self.send_json_response(500, {'error': f'压缩失败: {error}'})
                return
            
            # 读取压缩后的文件
            with open(output_path, 'rb') as f:
                compressed_data = f.read()
            
            # 获取文件大小
            original_size = os.path.getsize(input_path)
            compressed_size = len(compressed_data)
            
            # 清理临时文件
            for p in [input_path, output_path]:
                if os.path.exists(p):
                    os.remove(p)
            
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
            print(f"压缩错误: {e}")
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


def main():
    """启动服务器"""
    local_ips = get_local_ips()
    
    SilentTCPServer.allow_reuse_address = True
    
    with SilentTCPServer(("0.0.0.0", PORT), CompressHandler) as httpd:
        print('=' * 50)
        print('  iPhone 压缩工具 (FFmpeg 版) 已启动！')
        print('=' * 50)
        print()
        print('请用浏览器访问以下地址之一：')
        for ip in local_ips:
            print(f'  • http://{ip}:{PORT}')
        print(f'  • http://localhost:{PORT}')
        print()
        print('注意：需要在 iSH 中安装 FFmpeg')
        print('  apk add ffmpeg')
        print('=' * 50)
        print('  按 Ctrl+C 停止服务器')
        print('=' * 50)
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print()
            print('服务器已停止')
            # 清理临时文件
            if os.path.exists(UPLOAD_DIR):
                shutil.rmtree(UPLOAD_DIR)


if __name__ == '__main__':
    main()
