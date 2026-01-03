"""
Проверка подключения к SRT потоку
"""

import cv2
import yaml
import sys
import time

def check_srt_connection(config_path: str = "config.yaml"):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    srt_url = config['srt']['url']
    srt_params = f"?mode=caller&latency={config['srt']['latency']}"
    full_url = srt_url + srt_params
    
    print(f"Проверка подключения к: {srt_url}")
    print("Ожидание...")
    
    cap = cv2.VideoCapture(full_url, cv2.CAP_FFMPEG)
    time.sleep(3)  # Даем время на подключение
    
    if not cap.isOpened():
        print("❌ Не удалось открыть поток")
        print("\nПроверьте:")
        print(f"  1. IP адрес правильный? (текущий: {srt_url})")
        print("  2. Raspberry Pi запущен?")
        print("  3. Стрим активен? (запустите: ./stream_cam.sh на Pi)")
        print("  4. Сеть доступна? (ping <PI_IP>)")
        return False
    
    print("✓ Подключение установлено")
    
    # Пытаемся прочитать кадр
    ret, frame = cap.read()
    if not ret:
        print("❌ Кадры не приходят")
        cap.release()
        return False
    
    print(f"✓ Кадры приходят! Разрешение: {frame.shape[1]}x{frame.shape[0]}")
    
    # Показываем несколько кадров
    print("\nПоказываю первые 5 кадров (окно закроется автоматически)...")
    for i in range(5):
        ret, frame = cap.read()
        if ret:
            cv2.imshow("Test", frame)
            cv2.waitKey(1000)
        time.sleep(0.5)
    
    cv2.destroyAllWindows()
    cap.release()
    
    print("\n✓ Подключение работает нормально!")
    return True

if __name__ == "__main__":
    if not check_srt_connection():
        sys.exit(1)

