"""
Streamer: Наложение оверлея и стрим в Twitch через FFmpeg
Этап 1: Фиксированная рамка
Этап 3: Динамическая рамка от AI детектора через UDP
"""

import cv2
import yaml
import subprocess
import numpy as np
import time
import socket
import json
import threading
from typing import Optional, Tuple, List
import sys
import time
from roi import ROIResult, ROIConfig


class BBoxReceiver:
    """UDP клиент для получения bbox от AI детектора"""
    def __init__(self, host: str = "127.0.0.1", port: int = 5555):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.1)
        self.sock.bind((host, port))
        self.current_bbox: Optional[Tuple[List[int], float]] = None  # ([x1,y1,x2,y2], conf)
        self.running = False
        self.thread: Optional[threading.Thread] = None
    
    def start(self):
        """Запуск приема bbox"""
        self.running = True
        self.thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.thread.start()
        print(f"[Streamer] UDP приемник bbox запущен на {self.host}:{self.port}")
    
    def _receive_loop(self):
        """Цикл приема bbox через UDP"""
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                msg = json.loads(data.decode('utf-8'))
                
                if msg.get('bbox') is not None:
                    bbox = msg['bbox']
                    conf = msg.get('conf', 0.0)
                    self.current_bbox = (bbox, conf)
                else:
                    self.current_bbox = None
                    
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[Streamer] Ошибка приема bbox: {e}")
    
    def get_bbox(self) -> Optional[Tuple[List[int], float]]:
        """Получить текущий bbox"""
        return self.current_bbox
    
    def stop(self):
        """Остановка приема"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        self.sock.close()


class Streamer:
    def __init__(self, config_path: str = "config.yaml", use_ai: bool = False):
        """Инициализация стримера"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.stream_config = self.config['stream']
        self.twitch_config = self.config.get('twitch', {})
        self.overlay_config = self.config['overlay']
        
        self.mode = self.stream_config.get('mode', 'preview')  # preview | twitch
        self.width = self.stream_config['width']
        self.height = self.stream_config['height']
        self.fps = self.stream_config['fps']
        
        self.use_ai = use_ai
        self.bbox_receiver: Optional[BBoxReceiver] = None
        self.current_roi_result: Optional[ROIResult] = None
        self.current_activity_start_time: Optional[float] = None  # для таймера активности
        self.roi_config: Optional[ROIConfig] = None  # для рисования зон
        self.current_all_bboxes: list = []  # Все найденные bbox для отрисовки
        
        if use_ai:
            udp_config = self.config['udp']
            self.bbox_receiver = BBoxReceiver(
                host=udp_config['host'],
                port=udp_config['port']
            )
        
        self.ffmpeg_process: Optional[subprocess.Popen] = None
        self.running = False
        
    def _create_ffmpeg_process(self):
        """Создание FFmpeg процесса для кодирования и стриминга"""
        rtmp_url = self.twitch_config['rtmp_url'] + self.twitch_config['stream_key']
        
        # FFmpeg команда для приема raw video через stdin и отправки в RTMP
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-s', f"{self.width}x{self.height}",
            '-r', str(self.fps),
            '-i', '-',  # stdin
            '-c:v', 'libx264',
            '-preset', self.stream_config['preset'],
            '-b:v', self.stream_config['bitrate'],
            '-maxrate', self.stream_config['bitrate'],
            '-bufsize', str(int(self.stream_config['bitrate'].replace('k', '')) * 2) + 'k',
            '-g', str(self.fps * 2),  # GOP size
            '-pix_fmt', 'yuv420p',
            '-f', 'flv',
            rtmp_url
        ]
        
        print(f"[Streamer] Запуск FFmpeg: {' '.join(ffmpeg_cmd[:10])}...")
        self.ffmpeg_process = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("[Streamer] FFmpeg процесс запущен")
    
    def _draw_overlay(self, frame: np.ndarray) -> np.ndarray:
        """Рисование оверлея на кадре"""
        overlay_frame = frame.copy()
        
        # Рисуем ROI зоны (тонкие прямоугольники)
        if self.roi_config:
            for zone_name, zone_config in self.roi_config.zones.items():
                x1, y1, x2, y2 = zone_config.rect
                # Тонкие линии для зон
                cv2.rectangle(overlay_frame, (x1, y1), (x2, y2), (128, 128, 128), 1)
                # Название зоны в углу
                cv2.putText(
                    overlay_frame,
                    zone_name,
                    (x1 + 5, y1 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (128, 128, 128),
                    1
                )
        
        # Рисуем все найденные bbox котов (новый способ - через current_all_bboxes)
        if self.current_all_bboxes:
            # Определяем какой bbox используется для ROI (самый крупный)
            roi_bbox = None
            if len(self.current_all_bboxes) > 1:
                # Берем самого крупного для ROI
                candidates = [(bbox, conf, (bbox[2]-bbox[0])*(bbox[3]-bbox[1])) 
                             for bbox, conf in self.current_all_bboxes]
                roi_bbox_tuple = max(candidates, key=lambda x: x[2])
                roi_bbox = roi_bbox_tuple[0]
            else:
                roi_bbox = self.current_all_bboxes[0][0]
            
            # Рисуем все bbox
            for bbox, conf in self.current_all_bboxes:
                x1, y1, x2, y2 = bbox
                is_roi_bbox = (bbox == roi_bbox)
                
                # Цвет: зеленый для ROI bbox, желтый для остальных
                if is_roi_bbox:
                    color = tuple(self.overlay_config['box_color'])  # Зеленый
                    thickness = self.overlay_config['box_thickness']
                else:
                    color = (0, 255, 255)  # Желтый для остальных котов
                    thickness = 1  # Тонкая рамка
                
                cv2.rectangle(overlay_frame, (x1, y1), (x2, y2), color, thickness)
                
                # Формируем текст
                text_parts = [f"CAT {conf:.2f}"]
                
                # Добавляем активность от ROI только для ROI bbox
                if is_roi_bbox and self.current_roi_result and self.current_roi_result.active_zone:
                    active_zone = self.current_roi_result.active_zone.upper()
                    if self.current_activity_start_time is not None:
                        duration = time.time() - self.current_activity_start_time
                        text_parts.append(f"{active_zone} ({duration:.1f}s)")
                    else:
                        text_parts.append(active_zone)
                
                text = " | ".join(text_parts)
                text_color = tuple(self.overlay_config['text_color'])
                text_scale = self.overlay_config['text_scale']
                text_thickness = self.overlay_config['text_thickness']
                
                (text_width, text_height), baseline = cv2.getTextSize(
                    text, cv2.FONT_HERSHEY_SIMPLEX, text_scale, text_thickness
                )
                
                # Фон для текста
                cv2.rectangle(
                    overlay_frame,
                    (x1, y1 - text_height - baseline - 5),
                    (x1 + text_width, y1),
                    color,
                    -1
                )
                
                cv2.putText(
                    overlay_frame,
                    text,
                    (x1, y1 - baseline - 2),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    text_scale,
                    text_color,
                    text_thickness
                )
        
        # Обратная совместимость: если есть bbox_receiver (старый способ через UDP)
        elif self.use_ai and self.bbox_receiver:
            bbox_data = self.bbox_receiver.get_bbox()
            if bbox_data:
                bbox, conf = bbox_data
                x1, y1, x2, y2 = bbox
                
                # Рисуем прямоугольник
                color = tuple(self.overlay_config['box_color'])
                thickness = self.overlay_config['box_thickness']
                cv2.rectangle(overlay_frame, (x1, y1), (x2, y2), color, thickness)
                
                # Формируем текст с активностью и таймером
                text_parts = [f"CAT {conf:.2f}"]
                
                # Добавляем активность от ROI
                if self.current_roi_result and self.current_roi_result.active_zone:
                    activity = self.current_roi_result.active_zone.upper()
                    # Таймер активности
                    if self.current_activity_start_time is not None:
                        elapsed = time.time() - self.current_activity_start_time
                        text_parts.append(f"{activity} ({elapsed:.1f}s)")
                    else:
                        text_parts.append(activity)
                
                text = " | ".join(text_parts)
                text_color = tuple(self.overlay_config['text_color'])
                text_scale = self.overlay_config['text_scale']
                text_thickness = self.overlay_config['text_thickness']
                
                (text_width, text_height), baseline = cv2.getTextSize(
                    text, cv2.FONT_HERSHEY_SIMPLEX, text_scale, text_thickness
                )
                
                # Фон для текста
                cv2.rectangle(
                    overlay_frame,
                    (x1, y1 - text_height - baseline - 5),
                    (x1 + text_width, y1),
                    color,
                    -1
                )
                
                cv2.putText(
                    overlay_frame,
                    text,
                    (x1, y1 - baseline - 2),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    text_scale,
                    text_color,
                    text_thickness
                )
        elif self.current_roi_result and self.current_roi_result.active_zone:
            # Если нет bbox, но есть активность - показываем только активность
            activity = self.current_roi_result.active_zone.upper()
            if self.current_activity_start_time is not None:
                elapsed = time.time() - self.current_activity_start_time
                text = f"ACTIVITY: {activity} ({elapsed:.1f}s)"
            else:
                text = f"ACTIVITY: {activity}"
            text_color = tuple(self.overlay_config['text_color'])
            text_scale = self.overlay_config['text_scale']
            text_thickness = self.overlay_config['text_thickness']
            cv2.putText(
                overlay_frame,
                text,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                text_scale,
                text_color,
                text_thickness
            )
        elif not self.use_ai:
            # Этап 1: Фиксированная рамка для тестирования
            center_x = self.width // 2
            center_y = self.height // 2
            box_size = 200
            
            x1 = center_x - box_size // 2
            y1 = center_y - box_size // 2
            x2 = center_x + box_size // 2
            y2 = center_y + box_size // 2
            
            color = tuple(self.overlay_config['box_color'])
            thickness = self.overlay_config['box_thickness']
            cv2.rectangle(overlay_frame, (x1, y1), (x2, y2), color, thickness)
            
            text = "TEST FRAME"
            text_color = tuple(self.overlay_config['text_color'])
            text_scale = self.overlay_config['text_scale']
            text_thickness = self.overlay_config['text_thickness']
            
            cv2.putText(
                overlay_frame,
                text,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                text_scale,
                text_color,
                text_thickness
            )
        
        return overlay_frame
    
    def start(self):
        """Запуск стримера"""
        if self.use_ai and self.bbox_receiver:
            self.bbox_receiver.start()
        
        if self.mode == "preview":
            self.running = True
            print("[Streamer] Preview режим запущен (OpenCV окно, без FFmpeg/Twitch)")
            print("[Streamer] Нажмите 'q' в окне для выхода")
        else:
            self._create_ffmpeg_process()
            self.running = True
            print("[Streamer] Стример запущен (Twitch режим)")
    
    def stream_frame(self, frame: np.ndarray, all_bboxes: Optional[list] = None, roi_result: Optional[ROIResult] = None):
        """
        Отправить кадр в стрим или показать в preview
        
        Args:
            frame: Кадр для отрисовки
            all_bboxes: Список всех найденных котов [(bbox, conf), ...], где bbox = [x1,y1,x2,y2]
            roi_result: Результат ROI Engine для отрисовки активности
        """
        # Сохраняем все bbox для отрисовки
        self.current_all_bboxes = all_bboxes if all_bboxes else []
        
        # Сохраняем ROI результат для отрисовки
        if roi_result is not None:
            self.current_roi_result = roi_result
            # Обновляем таймер активности
            if roi_result.active_zone:
                if self.current_activity_start_time is None:
                    self.current_activity_start_time = time.time()
            else:
                self.current_activity_start_time = None
        
        # Изменяем размер если нужно
        if frame.shape[1] != self.width or frame.shape[0] != self.height:
            frame = cv2.resize(frame, (self.width, self.height))
        
        # Рисуем оверлей
        frame_with_overlay = self._draw_overlay(frame)
        
        if self.mode == "preview":
            # Preview режим - показываем в OpenCV окне
            cv2.imshow("CatCam ROI Preview", frame_with_overlay)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                # Закрытие по 'q'
                self.running = False
            return True
        else:
            # Twitch режим - отправляем в FFmpeg
            if not self.running or not self.ffmpeg_process:
                return False
            
            try:
                # Отправляем в FFmpeg через stdin
                self.ffmpeg_process.stdin.write(frame_with_overlay.tobytes())
                self.ffmpeg_process.stdin.flush()
                return True
            except Exception as e:
                print(f"[Streamer] Ошибка отправки кадра: {e}")
                return False
    
    def stop(self):
        """Остановка стримера"""
        self.running = False
        
        if self.mode == "preview":
            cv2.destroyAllWindows()
            print("[Streamer] Preview окно закрыто")
        else:
            if self.ffmpeg_process:
                try:
                    self.ffmpeg_process.stdin.close()
                    self.ffmpeg_process.wait(timeout=5)
                except:
                    self.ffmpeg_process.kill()
                print("[Streamer] FFmpeg процесс остановлен")
        
        if self.bbox_receiver:
            self.bbox_receiver.stop()
        
        print("[Streamer] Стример остановлен")


def main():
    """Тестовая функция для проверки стримера с тестовым кадром"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CatCam Streamer')
    parser.add_argument('--use-ai', action='store_true', help='Использовать AI bbox через UDP')
    args = parser.parse_args()
    
    streamer = Streamer(use_ai=args.use_ai)
    streamer.start()
    
    try:
        print("Генерация тестовых кадров... Нажмите Ctrl+C для остановки")
        frame_count = 0
        start_time = time.time()
        
        while True:
            # Создаем тестовый кадр
            frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
            
            streamer.stream_frame(frame)
            frame_count += 1
            
            if frame_count % 25 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed
                print(f"Отправлено кадров: {frame_count}, FPS: {fps:.1f}")
            
            time.sleep(1.0 / streamer.fps)
            
    except KeyboardInterrupt:
        print("\nОстановка...")
    finally:
        streamer.stop()


if __name__ == "__main__":
    main()

