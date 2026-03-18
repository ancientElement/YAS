"""工具函数"""
import socket


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
