"""
Главный скрипт для запуска всех компонентов CatCam системы
Интегрирует receiver, ai_detector и streamer в единый процесс
"""

import threading
import time
import signal
import sys
import yaml
from typing import Optional
from receiver import SRTReceiver
from ai_detector import AIDetector
from streamer import Streamer
from roi import ROIEngine, ROIConfig, ZoneConfig, BBox, ROIResult
from telemetry import TelemetryLogger, FPSMetrics
import subprocess


def load_roi_config(path: str = "config.yaml") -> ROIConfig:
    """Загрузка ROI конфигурации из YAML"""
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    
    roi = cfg["roi"]
    zones = {}
    
    for name, z in roi["zones"].items():
        zones[name] = ZoneConfig(
            name=name,
            rect=tuple(z["rect"]),
            min_time_sec=float(z["min_time_sec"]),
            max_movement_px=float(z["max_movement_px"]) if "max_movement_px" in z else None,
        )
    
    priority = roi.get("priority", ["eating", "drinking", "sleeping", "playing"])
    hysteresis_ticks = roi.get("hysteresis_ticks", 3)
    
    return ROIConfig(
        frame_size=tuple(roi["frame_size"]),
        intersection_threshold=float(roi.get("intersection_threshold", 0.3)),
        zones=zones,
        priority=priority,
        hysteresis_ticks=int(hysteresis_ticks),
    )


class Watchdog:
    """Watchdog для мониторинга health компонентов и авто-рестарта"""
    
    def __init__(self, system, receiver_timeout_sec: float = 5.0, check_interval_sec: float = 2.0, auto_restart: bool = True):
        self.system = system
        self.receiver_timeout_sec = receiver_timeout_sec
        self.check_interval_sec = check_interval_sec
        self.auto_restart = auto_restart
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.last_frame_time: float = 0.0
    
    def update_frame_time(self):
        """Вызывать при получении каждого кадра"""
        self.last_frame_time = time.time()
    
    def check_receiver_health(self) -> bool:
        """Проверка health receiver: если нет кадров > timeout, возвращает False"""
        if self.system.receiver is None:
            return True  # Receiver не инициализирован - не проверяем
        
        current_time = time.time()
        time_since_last_frame = current_time - self.last_frame_time
        
        if time_since_last_frame > self.receiver_timeout_sec:
            print(f"[Watchdog] Receiver не получает кадры {time_since_last_frame:.1f} сек (timeout: {self.receiver_timeout_sec} сек)")
            return False
        return True
    
    def check_streamer_health(self) -> bool:
        """Проверка health streamer: если FFmpeg процесс умер, возвращает False"""
        if self.system.streamer is None:
            return True  # Streamer не инициализирован - не проверяем
        
        # Проверяем только в режиме twitch (не preview)
        if self.system.streamer.mode != "twitch":
            return True  # В preview режиме нет FFmpeg процесса
        
        if self.system.streamer.ffmpeg_process is None:
            return True  # FFmpeg процесс еще не создан
        
        # Проверяем, жив ли процесс
        if self.system.streamer.ffmpeg_process.poll() is not None:
            print(f"[Watchdog] FFmpeg процесс умер (exit code: {self.system.streamer.ffmpeg_process.poll()})")
            return False
        
        return True
    
    def _watchdog_loop(self):
        """Основной цикл watchdog"""
        while self.running:
            try:
                # Проверка receiver
                if not self.check_receiver_health():
                    if self.auto_restart:
                        print("[Watchdog] Перезапуск receiver...")
                        try:
                            if self.system.receiver:
                                self.system.receiver.stop()
                            self.system.receiver = SRTReceiver(self.system.config_path)
                            if not self.system.receiver.start():
                                print("[Watchdog] Ошибка перезапуска receiver")
                        except Exception as e:
                            print(f"[Watchdog] Исключение при перезапуске receiver: {e}")
                        self.last_frame_time = time.time()  # Сброс таймера
                
                # Проверка streamer
                if not self.check_streamer_health():
                    if self.auto_restart:
                        print("[Watchdog] Перезапуск streamer...")
                        try:
                            if self.system.streamer:
                                self.system.streamer.stop()
                            # Streamer перезапускается через start()
                            if self.system.streamer:
                                self.system.streamer.start()
                        except Exception as e:
                            print(f"[Watchdog] Исключение при перезапуске streamer: {e}")
                
            except Exception as e:
                print(f"[Watchdog] Ошибка в watchdog loop: {e}")
            
            time.sleep(self.check_interval_sec)
    
    def start(self):
        """Запуск watchdog в отдельном потоке"""
        if self.running:
            return
        
        self.running = True
        self.last_frame_time = time.time()
        self.thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self.thread.start()
        print("[Watchdog] Запущен")
    
    def stop(self):
        """Остановка watchdog"""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        print("[Watchdog] Остановлен")


class CatCamSystem:
    def __init__(self, config_path: str = "config.yaml"):
        """Инициализация полной системы"""
        self.config_path = config_path
        
        # Загружаем конфиг для телеметрии и streamer FPS
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        telemetry_config = config.get('telemetry', {})
        telemetry_enabled = telemetry_config.get('enabled', True)
        log_dir = telemetry_config.get('log_dir', 'logs')
        flush_interval = telemetry_config.get('flush_interval', 5.0)
        
        self.telemetry = TelemetryLogger(
            log_dir=log_dir,
            enabled=telemetry_enabled,
            flush_interval=flush_interval
        )
        self.fps_metrics = FPSMetrics()
        
        # Target FPS для streamer (из config)
        stream_config = config.get('stream', {})
        self.target_stream_fps = stream_config.get('fps', 25)
        self.last_stream_frame_time = 0.0
        
        # Watchdog конфигурация
        watchdog_config = config.get('watchdog', {})
        watchdog_enabled = watchdog_config.get('enabled', True)
        receiver_timeout_sec = watchdog_config.get('receiver_timeout_sec', 5.0)
        check_interval_sec = watchdog_config.get('streamer_check_interval_sec', 2.0)
        auto_restart = watchdog_config.get('auto_restart', True)
        
        self.watchdog: Optional[Watchdog] = None
        if watchdog_enabled:
            self.watchdog = Watchdog(
                self,
                receiver_timeout_sec=receiver_timeout_sec,
                check_interval_sec=check_interval_sec,
                auto_restart=auto_restart
            )
        
        self.receiver: Optional[SRTReceiver] = None
        self.ai_detector: Optional[AIDetector] = None
        self.streamer: Optional[Streamer] = None
        self.roi_engine: Optional[ROIEngine] = None
        self.running = False
    
    def start(self, use_ai: bool = True):
        """Запуск всех компонентов"""
        print("=" * 50)
        print("CatCam System - Запуск")
        print("=" * 50)
        
        # Инициализация компонентов
        self.receiver = SRTReceiver(self.config_path)
        self.streamer = Streamer(self.config_path, use_ai=use_ai)
        
        if use_ai:
            self.ai_detector = AIDetector(self.config_path, use_udp=True)
            
            # Загружаем ROI config один раз для ROI Engine и Streamer
            print("[2/4] Инициализация AI Detector...")
            # AI detector не требует явного start(), он работает в process_frame
            
            print("[3/4] Инициализация ROI Engine...")
            try:
                roi_config = load_roi_config(self.config_path)
                self.roi_engine = ROIEngine(roi_config)
                # Передаём ROI config в streamer для рисования зон
                self.streamer.roi_config = roi_config
                print("[ROI] ROI Engine инициализирован")
            except Exception as e:
                print(f"[ROI] Ошибка инициализации ROI Engine: {e}")
                print("[ROI] Продолжаем без ROI")
                self.roi_engine = None
        
        # Запуск компонентов
        print("\n[1/4] Запуск Receiver...")
        if not self.receiver.start():
            print("Ошибка: не удалось запустить Receiver")
            return False
        
        print("[4/4] Запуск Streamer...")
        self.streamer.start()
        
        # Запуск watchdog
        if self.watchdog:
            self.watchdog.start()
        
        self.running = True
        print("\nСистема запущена!")
        return True
    
    def run(self):
        """Основной цикл обработки"""
        if not self.running:
            return
        
        frame_count = 0
        last_fps_time = time.time()
        last_ai_time = time.time()
        ai_interval = 1.0 / 8.0  # AI обработка ~8 fps
        
        try:
            while self.running:
                # Получаем кадр от receiver
                result = self.receiver.get_frame(timeout=0.1)
                
                if result:
                    timestamp, frame = result
                    
                    # Обновляем watchdog (получен кадр)
                    if self.watchdog:
                        self.watchdog.update_frame_time()
                    
                    # Обновляем FPS метрики для receiver
                    self.fps_metrics.update_receiver()
                    
                    # Обработка через AI detector (если включен, ограничиваем частоту)
                    all_bboxes: list = []  # Все найденные коты для отрисовки
                    current_bbox: Optional[BBox] = None  # Один bbox для ROI Engine
                    conf: Optional[float] = None
                    all_detections = []
                    roi_result: Optional[ROIResult] = None
                    
                    if self.ai_detector:
                        current_time = time.time()
                        if current_time - last_ai_time >= ai_interval:
                            # Получаем всех котов
                            all_detections = self.ai_detector.detect_all(frame)
                            self.fps_metrics.update_infer()
                            last_ai_time = current_time
                            
                            if all_detections:
                                all_bboxes = all_detections
                                
                                # Для ROI выбираем самого крупного (для обратной совместимости)
                                if len(all_detections) > 1:
                                    # Сортируем по площади и берем самого крупного
                                    candidates = []
                                    for bbox_list, conf_val in all_detections:
                                        area = (bbox_list[2] - bbox_list[0]) * (bbox_list[3] - bbox_list[1])
                                        candidates.append((bbox_list, conf_val, area))
                                    best = max(candidates, key=lambda x: x[2])
                                    bbox_list, conf = best[0], best[1]
                                else:
                                    bbox_list, conf = all_detections[0]
                                
                                current_bbox = BBox(x1=bbox_list[0], y1=bbox_list[1], x2=bbox_list[2], y2=bbox_list[3])
                            
                            # Обработка через ROI Engine (использует одного кота - самого крупного)
                            if self.roi_engine:
                                current_ts = time.time()
                                roi_result = self.roi_engine.update(current_bbox, current_ts)
                                
                                # Логирование событий ROI
                                for ev in roi_result.events:
                                    print(f"[EVENT] {ev.type} {ev.duration_sec:.1f}s")
                                    # Логируем событие в телеметрию
                                    self.telemetry.log_event(ev, avg_conf=conf)
                            
                            # Логирование телеметрии (на каждом AI inference тике)
                            current_ts = time.time()
                            self.telemetry.log_telemetry(
                                ts=current_ts,
                                bbox=current_bbox,
                                conf=conf,
                                roi_result=roi_result,
                                fps_metrics=self.fps_metrics
                            )
                    
                    # Ограничение FPS для streamer (timestamp-based throttling)
                    current_time_for_stream = time.time()
                    frame_interval = 1.0 / self.target_stream_fps
                    
                    if current_time_for_stream - self.last_stream_frame_time >= frame_interval:
                        # Обновляем FPS метрики для streamer
                        self.fps_metrics.update_stream()
                        
                        # Отправка кадра в стрим
                        self.streamer.stream_frame(frame, all_bboxes=all_bboxes, roi_result=roi_result)
                        
                        self.last_stream_frame_time = current_time_for_stream
                    else:
                        # Пропускаем кадр для соблюдения target FPS
                        pass
                    
                    frame_count += 1
                    
                    # Выводим FPS каждые 5 секунд
                    current_time = time.time()
                    if current_time - last_fps_time >= 5.0:
                        fps = frame_count / (current_time - last_fps_time)
                        print(f"[System] FPS стрима: {fps:.1f} | Receiver: {self.fps_metrics.receiver_fps:.1f} | Infer: {self.fps_metrics.infer_fps:.1f}")
                        frame_count = 0
                        last_fps_time = current_time
                else:
                    # Нет кадров, небольшая задержка
                    time.sleep(0.01)
        
        except KeyboardInterrupt:
            print("\nПолучен сигнал остановки...")
        finally:
            self.stop()
    
    def stop(self):
        """Остановка всех компонентов"""
        print("\nОстановка системы...")
        self.running = False
        
        if self.receiver:
            self.receiver.stop()
        
        if self.streamer:
            self.streamer.stop()
        
        if self.ai_detector:
            self.ai_detector.close()
        
        if self.telemetry:
            self.telemetry.close()
        
        if self.watchdog:
            self.watchdog.stop()
        
        print("Система остановлена.")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='CatCam System - Полная система')
    parser.add_argument('--no-ai', action='store_true', help='Запуск без AI (только фиксированная рамка)')
    parser.add_argument('--config', type=str, default='config.yaml', help='Путь к config.yaml')
    args = parser.parse_args()
    
    system = CatCamSystem(config_path=args.config)
    
    # Обработка сигналов для корректного завершения
    def signal_handler(sig, frame):
        system.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    use_ai = not args.no_ai
    
    if not system.start(use_ai=use_ai):
        sys.exit(1)
    
    system.run()


if __name__ == "__main__":
    main()

