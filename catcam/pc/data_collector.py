"""
Сбор данных для обучения: запись видео с камеры в файлы
"""

import cv2
import yaml
import os
from datetime import datetime
from pathlib import Path
import time


class DataCollector:
    def __init__(self, config_path: str = "config.yaml", output_dir: str = "../data/raw_videos"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.cap = None
        self.writer = None
        self.recording = False
        
    def start_recording(self, duration_seconds: int = 300, segment_duration: int = 60):
        """Запись видео сегментами"""
        srt_url = self.config['srt']['url']
        full_url = srt_url
        
        print(f"Подключение к потоку: {srt_url}")
        print(f"Проверьте что Raspberry Pi запущен и стрим активен!")
        
        self.cap = cv2.VideoCapture(full_url, cv2.CAP_FFMPEG)
        
        # Даем время на подключение
        import time
        time.sleep(2)
        
        if not self.cap.isOpened():
            print(f"\nОШИБКА: Не удалось подключиться к {srt_url}")
            print("\nПроверьте:")
            print("  1. Raspberry Pi запущен и стрим активен?")
            print("  2. Правильный IP адрес в config.yaml?")
            print("  3. Порт 9000 открыт?")
            print("  4. Можете ли подключиться: ping <PI_IP>")
            print(f"\nПопробуйте запустить на Pi: ./stream_cam.sh")
            return False
        
        # Проверяем что кадры действительно приходят
        ret, test_frame = self.cap.read()
        if not ret:
            print("\nОШИБКА: Подключение установлено, но кадры не приходят")
            print("Проверьте что камера работает на Raspberry Pi")
            self.cap.release()
            return False
        
        print("✓ Подключение успешно! Кадры приходят.")
        
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(self.cap.get(cv2.CAP_PROP_FPS)) or 30
        
        print(f"Параметры: {width}x{height} @ {fps} fps")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        segment_num = 0
        start_time = time.time()
        segment_start = start_time
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        
        print(f"Запись начата: {duration_seconds}с, сегменты по {segment_duration}с")
        
        while time.time() - start_time < duration_seconds:
            ret, frame = self.cap.read()
            if not ret:
                break
            
            if self.writer is None or time.time() - segment_start >= segment_duration:
                if self.writer:
                    self.writer.release()
                
                segment_num += 1
                filename = f"{timestamp}_segment_{segment_num:03d}.mp4"
                filepath = self.output_dir / filename
                self.writer = cv2.VideoWriter(str(filepath), fourcc, fps, (width, height))
                segment_start = time.time()
                print(f"Сегмент {segment_num}: {filename}")
            
            self.writer.write(frame)
        
        if self.writer:
            self.writer.release()
        self.cap.release()
        print("Запись завершена")
        return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=300, help="Длительность записи (сек)")
    parser.add_argument("--segment", type=int, default=60, help="Длина сегмента (сек)")
    parser.add_argument("--output", type=str, default="../data/raw_videos")
    args = parser.parse_args()
    
    collector = DataCollector(output_dir=args.output)
    collector.start_recording(args.duration, args.segment)

