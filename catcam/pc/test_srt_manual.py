"""
Ручная проверка SRT подключения разными способами
"""

import subprocess
import sys
import yaml

def test_srt_ffmpeg_direct(config_path="config.yaml"):
    """Тест SRT через прямой вызов ffmpeg"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    srt_url = config['srt']['url']
    
    print(f"Тест 1: Прямой вызов ffmpeg для SRT потока")
    print(f"URL: {srt_url}")
    print()
    
    # Пробуем прочитать несколько секунд через ffmpeg
    cmd = [
        'ffmpeg',
        '-i', srt_url,
        '-t', '5',  # 5 секунд
        '-f', 'null',
        '-'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✓ FFmpeg может подключиться к SRT потоку!")
            return True
        else:
            print("❌ FFmpeg не может подключиться")
            print("stderr:", result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("❌ Таймаут - поток не отвечает")
        return False
    except FileNotFoundError:
        print("❌ FFmpeg не найден в PATH")
        return False

def test_srt_with_cv2(config_path="config.yaml"):
    """Тест через OpenCV"""
    try:
        import cv2
        import yaml
        import time
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        srt_url = config['srt']['url']
        srt_params = f"?mode=caller&latency=200"
        full_url = srt_url + srt_params
        
        print(f"\nТест 2: OpenCV подключение")
        print(f"URL: {full_url}")
        
        cap = cv2.VideoCapture(full_url, cv2.CAP_FFMPEG)
        time.sleep(3)
        
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print("✓ OpenCV может подключиться и читать кадры!")
                cap.release()
                return True
            else:
                print("❌ OpenCV подключился, но кадры не приходят")
                cap.release()
                return False
        else:
            print("❌ OpenCV не может открыть поток")
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Проверка SRT подключения")
    print("=" * 50)
    print()
    
    # Сначала проверяем через ffmpeg (более надежно)
    ffmpeg_ok = test_srt_ffmpeg_direct()
    
    if not ffmpeg_ok:
        print("\n" + "=" * 50)
        print("РЕШЕНИЕ:")
        print("=" * 50)
        print("SRT поток не доступен. Возможные причины:")
        print()
        print("1. Стрим не запущен на Raspberry Pi")
        print("   Подключитесь к Pi по SSH и запустите:")
        print("   cd catcam/pi")
        print("   chmod +x stream_cam.sh")
        print("   ./stream_cam.sh")
        print()
        print("2. Проверьте что стрим запущен на Pi:")
        print("   ps aux | grep ffmpeg")
        print("   netstat -tulpn | grep 9000")
        print()
        print("3. Если стрим не запускается на Pi - проверьте:")
        print("   - Камера подключена? lsusb")
        print("   - Камера видна? v4l2-ctl --list-devices")
        print("   - FFmpeg установлен? ffmpeg -version")
        sys.exit(1)
    
    # Если ffmpeg работает, проверяем cv2
    cv2_ok = test_srt_with_cv2()
    
    if ffmpeg_ok and not cv2_ok:
        print("\n⚠ FFmpeg работает, но OpenCV не может подключиться")
        print("Это известная проблема - OpenCV может не поддерживать SRT напрямую")
        print("Нужно будет использовать альтернативный метод")
    elif ffmpeg_ok and cv2_ok:
        print("\n✓ Все работает! Можно использовать data_collector.py")

