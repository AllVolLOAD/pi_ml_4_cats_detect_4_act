"""
AI Detector: Детекция кота через YOLOv8
Этап 2: Вывод bbox в консоль
Этап 3: Отправка bbox через UDP JSON
"""

import cv2
import yaml
import numpy as np
import time
import socket
import json
from typing import Optional, List, Tuple
from ultralytics import YOLO
import sys
from storage import StoragePaths


class AIDetector:
    def __init__(self, config_path: str = "config.yaml", use_udp: bool = False):
        """Инициализация AI детектора"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.ai_config = self.config['ai']
        self.udp_config = self.config.get('udp', {})
        
        # Инициализация storage paths
        self.storage = StoragePaths(self.config)
        
        # Загрузка модели YOLOv8
        model_path_config = self.ai_config['model_path']
        model_path = self.storage.get_model_path(model_path_config)
        
        print(f"[AI] Загрузка модели YOLOv8 из {model_path}...")
        
        try:
            self.model = YOLO(str(model_path))
            print(f"[AI] Модель загружена успешно: {model_path}")
        except Exception as e:
            print(f"[AI] Ошибка загрузки модели {model_path}: {e}")
            print("[AI] Попытка загрузки предобученной модели yolov8n.pt...")
            try:
                self.model = YOLO('yolov8n.pt')
                print("[AI] Предобученная модель загружена")
            except Exception as e2:
                print(f"[AI] Критическая ошибка: не удалось загрузить модель: {e2}")
                raise
        
        # Настройка устройства (GPU если доступен)
        self.device = 'cuda' if self.model.device.type == 'cuda' else 'cpu'
        print(f"[AI] Используется устройство: {self.device}")
        
        self.input_width = self.ai_config['input_width']
        self.input_height = self.ai_config['input_height']
        self.confidence_threshold = self.ai_config['confidence_threshold']
        self.class_filter = self.ai_config.get('class_filter', ['cat'])
        self.log_low_confidence = self.ai_config.get('log_low_confidence', False)
        
        # UDP для отправки bbox
        self.use_udp = use_udp
        self.udp_sock: Optional[socket.socket] = None
        
        if use_udp:
            self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_host = self.udp_config.get('host', '127.0.0.1')
            self.udp_port = self.udp_config.get('port', 5555)
            print(f"[AI] UDP отправка включена: {self.udp_host}:{self.udp_port}")
    
    def _get_class_id(self, class_name: str) -> Optional[int]:
        """Получить ID класса по имени"""
        class_names = self.model.names
        for idx, name in class_names.items():
            if name.lower() == class_name.lower():
                return idx
        return None
    
    def detect_all(self, frame: np.ndarray) -> List[Tuple[List[int], float]]:
        """
        Детекция всех котов на кадре
        
        Args:
            frame: Кадр в формате BGR (OpenCV)
        
        Returns:
            Список [(bbox, confidence), ...] всех найденных котов
            bbox: [x1, y1, x2, y2] в координатах исходного кадра
        """
        # Изменяем размер для детекции
        input_frame = cv2.resize(frame, (self.input_width, self.input_height))
        
        # YOLOv8 ожидает RGB формат
        input_frame_rgb = cv2.cvtColor(input_frame, cv2.COLOR_BGR2RGB)
        
        # Детекция
        results = self.model.predict(
            input_frame_rgb,
            conf=self.confidence_threshold,
            verbose=False,
            device=self.device
        )
        
        result = results[0]
        
        # Масштабирование координат обратно к исходному размеру кадра
        scale_x = frame.shape[1] / self.input_width
        scale_y = frame.shape[0] / self.input_height
        
        all_detections = []
        
        # Фильтрация по классу и сбор всех результатов
        for box in result.boxes:
            class_id = int(box.cls[0])
            class_name = self.model.names[class_id]
            
            if class_name.lower() in [c.lower() for c in self.class_filter]:
                conf = float(box.conf[0])
                
                # Координаты в формате xyxy (normalized)
                xyxy = box.xyxy[0].cpu().numpy()
                
                # Масштабируем к исходному размеру
                x1 = int(xyxy[0] * scale_x)
                y1 = int(xyxy[1] * scale_y)
                x2 = int(xyxy[2] * scale_x)
                y2 = int(xyxy[3] * scale_y)
                
                all_detections.append(([x1, y1, x2, y2], conf))
        
        return all_detections
    
    def detect(self, frame: np.ndarray) -> Optional[Tuple[List[int], float]]:
        """
        Детекция кота на кадре (возвращает самого крупного)
        
        Args:
            frame: Кадр в формате BGR (OpenCV)
        
        Returns:
            (bbox, confidence) или None если кот не обнаружен
            bbox: [x1, y1, x2, y2] в координатах исходного кадра
        """
        # Используем detect_all и выбираем самого крупного
        all_detections = self.detect_all(frame)
        
        if not all_detections:
            return None
        
        if len(all_detections) == 1:
            return all_detections[0]
        
        # Выбираем самого крупного кота (по площади)
        # Это работает лучше чем по confidence, потому что:
        # - Крупный кот = ближе к камере = важнее для детекции активности
        # - Дальний план имеет меньшую площадь и не перекрывает крупные bbox
        candidates = []
        for bbox, conf in all_detections:
            area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            candidates.append((bbox, conf, area))
        
        best = max(candidates, key=lambda x: x[2])  # x[2] = area
        
        # Логируем если нашли несколько котов
        if self.log_low_confidence:
            print(f"[AI] Найдено {len(all_detections)} котов, для ROI выбран самый крупный (area={best[2]}, conf={best[1]:.2f})")
        
        return (best[0], best[1])  # (bbox, conf)
    
    def _send_bbox_udp(self, bbox: Optional[Tuple[List[int], float]]):
        """Отправка bbox через UDP"""
        if not self.use_udp or not self.udp_sock:
            return
        
        timestamp = time.time()
        
        if bbox:
            bbox_coords, conf = bbox
            msg = {
                "t": timestamp,
                "bbox": bbox_coords,
                "conf": conf
            }
        else:
            msg = {
                "t": timestamp,
                "bbox": None
            }
        
        try:
            data = json.dumps(msg).encode('utf-8')
            self.udp_sock.sendto(data, (self.udp_host, self.udp_port))
        except Exception as e:
            print(f"[AI] Ошибка отправки UDP: {e}")
    
    def process_frame(self, frame: np.ndarray, print_result: bool = False) -> Optional[Tuple[List[int], float]]:
        """
        Обработка кадра: детекция и отправка результата
        
        Args:
            frame: Кадр в формате BGR
            print_result: Выводить результат в консоль
        
        Returns:
            (bbox, confidence) или None
        """
        start_time = time.time()
        result = self.detect(frame)
        inference_time = (time.time() - start_time) * 1000  # мс
        
        if result:
            bbox, conf = result
            # Логируем детекции с низким confidence (возможно кот на заднем плане)
            if self.log_low_confidence:
                if conf < 0.3:
                    area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                    print(f"[AI] Кот обнаружен (низкий conf/дальний план?): conf={conf:.3f}, area={area}, время={inference_time:.1f}мс")
                elif print_result:
                    print(f"[AI] Кот обнаружен: bbox={bbox}, conf={conf:.3f}, время={inference_time:.1f}мс")
            elif print_result:
                print(f"[AI] Кот обнаружен: bbox={bbox}, conf={conf:.3f}, время={inference_time:.1f}мс")
        else:
            if print_result:
                print(f"[AI] Кот не обнаружен, время={inference_time:.1f}мс")
        
        # Отправка через UDP если включено
        if self.use_udp:
            self._send_bbox_udp(result)
        
        return result
    
    def close(self):
        """Закрытие ресурсов"""
        if self.udp_sock:
            self.udp_sock.close()


def main():
    """Тестовая функция для проверки детектора"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CatCam AI Detector')
    parser.add_argument('--udp', action='store_true', help='Отправлять bbox через UDP')
    parser.add_argument('--image', type=str, help='Путь к тестовому изображению')
    parser.add_argument('--camera', type=int, default=-1, help='ID камеры для тестирования (-1 для файла)')
    args = parser.parse_args()
    
    detector = AIDetector(use_udp=args.udp)
    
    try:
        if args.image:
            # Тестирование на изображении
            print(f"[AI] Загрузка изображения: {args.image}")
            frame = cv2.imread(args.image)
            
            if frame is None:
                print(f"[AI] Ошибка: не удалось загрузить изображение {args.image}")
                sys.exit(1)
            
            result = detector.process_frame(frame, print_result=True)
            
            if result:
                bbox, conf = result
                x1, y1, x2, y2 = bbox
                
                # Рисуем bbox на изображении
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"CAT {conf:.2f}", (x1, y1-10),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                # Сохраняем результат
                output_path = "detection_result.jpg"
                cv2.imwrite(output_path, frame)
                print(f"[AI] Результат сохранен: {output_path}")
        
        elif args.camera >= 0:
            # Тестирование на камере
            print(f"[AI] Открытие камеры {args.camera}...")
            cap = cv2.VideoCapture(args.camera)
            
            if not cap.isOpened():
                print(f"[AI] Ошибка: не удалось открыть камеру {args.camera}")
                sys.exit(1)
            
            print("Детекция... Нажмите 'q' для выхода")
            frame_count = 0
            start_time = time.time()
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                detector.process_frame(frame, print_result=(frame_count % 30 == 0))
                
                # Выводим FPS
                if frame_count % 30 == 0:
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed
                    print(f"[AI] FPS обработки: {fps:.1f}")
                
                # Показываем кадр (опционально)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
            
            cap.release()
        
        else:
            print("[AI] Укажите --image <путь> или --camera <ID>")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\nОстановка...")
    finally:
        detector.close()


if __name__ == "__main__":
    main()

