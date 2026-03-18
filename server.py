#!/usr/bin/env python3
"""
iPhone 压缩工具 - Python 服务器
作用：提供静态文件服务，部署 WebApp
适用于 iSH 等性能受限环境
"""

import http.server
import socketserver
import os
import socket

# 配置
PORT = 3000
ROOT = os.path.dirname(os.path.abspath(__file__))

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
    '.json': 'application/json'
}


class StaticHandler(http.server.SimpleHTTPRequestHandler):
    """自定义静态文件处理器"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)
    
    def guess_type(self, path):
        """根据扩展名返回 MIME 类型"""
        ext = os.path.splitext(path)[1].lower()
        return MIME_TYPES.get(ext, 'application/octet-stream')
    
    def end_headers(self):
        """添加禁用缓存头"""
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()
    
    def log_message(self, format, *args):
        """简化日志输出"""
        pass  # 静默模式，减少 iSH 终端输出开销


def get_local_ips():
    """获取本机所有 IP 地址"""
    try:
        ips = []
        # 获取所有网络接口
        hostname = socket.gethostname()
        # 尝试获取 IP 地址
        try:
            addr = socket.gethostbyname(hostname)
            if addr and addr != '127.0.0.1':
                ips.append(addr)
        except:
            pass
        
        # 通过连接外部地址获取本机 IP
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


def main():
    """启动服务器"""
    local_ips = get_local_ips()
    
    # 允许地址重用，避免端口占用问题
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("0.0.0.0", PORT), StaticHandler) as httpd:
        print('=' * 40)
        print('  iPhone 压缩工具已启动！')
        print('=' * 40)
        print()
        print('请用浏览器访问以下地址之一：')
        for ip in local_ips:
            print(f'  • http://{ip}:{PORT}')
        print(f'  • http://localhost:{PORT}')
        print()
        print('=' * 40)
        print('  按 Ctrl+C 停止服务器')
        print('=' * 40)
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print()
            print('服务器已停止')


if __name__ == '__main__':
    main()
