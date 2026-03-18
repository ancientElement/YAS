#!/usr/bin/env python3
"""
iPhone 压缩工具 - FFmpeg 服务器端压缩方案
"""

import socketserver
import shutil
import os

from config import PORT, UPLOAD_DIR
from utils import get_local_ips
from handler import CompressHandler, SilentTCPServer


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
        print('注意：需要在运行环境中安装 FFmpeg')
        print('  apk add ffmpeg')
        print('=' * 50)
        print('  按 Ctrl+C 停止服务器')
        print('=' * 50)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print()
            print('服务器已停止')
            if os.path.exists(UPLOAD_DIR):
                shutil.rmtree(UPLOAD_DIR)


if __name__ == '__main__':
    main()
