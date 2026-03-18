"""FFmpeg 视频压缩工具"""
import os
import subprocess


# 全局进度存储
compress_progress = {}


def get_video_duration(input_path):
    """获取视频时长（秒）"""
    try:
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
               '-of', 'default=noprint_wrappers=1:nokey=1', input_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return float(result.stdout.strip())
    except:
        return 0


def has_audio_stream(input_path):
    """检测视频是否有音频流"""
    try:
        cmd = ['ffprobe', '-v', 'error', '-select_streams', 'a',
               '-show_entries', 'stream=codec_type', '-of',
               'default=noprint_wrappers=1:nokey=1', input_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return 'audio' in result.stdout.lower()
    except:
        return False


def compress_video(input_path, output_path, quality='medium', client_id=None):
    """
    使用 FFmpeg 压缩视频
    quality: low(0.5), medium(0.7), high(0.9)
    """
    scale_map = {'low': 'iw*0.5:ih*0.5', 'medium': 'iw*0.7:ih*0.7', 'high': 'iw*0.9:ih*0.9'}
    scale = scale_map.get(quality, 'iw*0.7:ih*0.7')

    duration = get_video_duration(input_path)
    has_audio = has_audio_stream(input_path)

    cmd = [
        'ffmpeg', '-hide_banner', '-loglevel', 'warning',
        '-i', input_path, '-vf', f'scale={scale}',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
        '-progress', 'pipe:1', '-y'
    ]

    if has_audio:
        cmd.extend(['-c:a', 'aac', '-b:a', '128k', '-ar', '44100'])
    else:
        cmd.append('-an')

    cmd.append(output_path)

    try:
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   bufsize=1, universal_newlines=True, creationflags=creationflags)

        last_percent = 0
        error_output = []

        while True:
            line = process.stdout.readline()
            if not line:
                if process.poll() is not None:
                    break
                continue

            line = line.strip()
            if not line:
                continue

            error_output.append(line)
            if len(error_output) > 20:
                error_output.pop(0)

            # 解析进度
            if 'out_time_ms=' in line and 'N/A' not in line:
                try:
                    time_str = line.split('=')[1].strip()
                    if time_str and time_str != 'N/A':
                        time_ms = int(time_str)
                        if duration > 0:
                            percent = min(int((time_ms / 1000000) / duration * 100), 99)
                            if percent != last_percent:
                                last_percent = percent
                                if client_id:
                                    compress_progress[client_id] = {'percent': percent, 'status': 'compressing'}
                                bar = '█' * (percent // 5) + '░' * (20 - percent // 5)
                                print(f"\r  压缩进度: [{bar}] {percent}%", end='', flush=True)
                except:
                    pass

        print()
        process.wait()

        if process.returncode != 0:
            error_msg = '\n'.join(error_output[-5:])
            print(f"  FFmpeg error: {error_msg[:300]}")
            return False, error_msg

        if client_id:
            compress_progress[client_id] = {'percent': 100, 'status': 'done'}
        return True, None

    except subprocess.TimeoutExpired:
        return False, "压缩超时"
    except Exception as e:
        return False, str(e)
