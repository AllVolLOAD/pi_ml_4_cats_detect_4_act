"""
Receiver: Прием SRT потока от Raspberry Pi
Читает поток через FFmpeg (pipe), декодирует в raw BGR и кладет кадры в очередь
"""

import subprocess
import queue
import threading
import time
import sys
import yaml
import numpy as np
from typing import Optional, Tuple


class SRTReceiver:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.srt_url = self.config['srt']['url']
        self.width = self.config['stream']['width']
        self.height = self.config['stream']['height']

        self.frame_size = self.width * self.height * 3
        self.frame_queue = queue.Queue(maxsize=60)

        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.ffmpeg: Optional[subprocess.Popen] = None
        self.reconnect_interval = 5.0  # секунды между попытками переподключения
        self.last_reconnect_attempt = 0.0

    def _create_ffmpeg_process(self) -> bool:
        """Создание FFmpeg процесса для подключения к SRT потоку"""
        ffmpeg_cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",
            "-fflags", "nobuffer",
            "-flags", "low_delay",
            "-probesize", "32",
            "-analyzeduration", "0",
            "-i", self.srt_url,
            "-an",
            "-sn",
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
            "-s", f"{self.width}x{self.height}",
            "pipe:1"
        ]

        try:
            self.ffmpeg = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=self.frame_size * 4
            )

            time.sleep(2.0)

            if self.ffmpeg.poll() is not None:
                err = self.ffmpeg.stderr.read().decode("utf-8", errors="ignore")
                print("[Receiver] FFmpeg не смог подключиться")
                if err:
                    err_lines = err.split('\n')
                    # Показываем последние 3 строки ошибки (обычно там самое важное)
                    for line in err_lines[-3:]:
                        if line.strip():
                            print(f"[Receiver] {line.strip()}")
                self.ffmpeg = None
                return False

            return True
        except Exception as e:
            print(f"[Receiver] Ошибка создания FFmpeg процесса: {e}")
            self.ffmpeg = None
            return False

    def start(self) -> bool:
        """Запуск receiver (первая попытка подключения)"""
        print(f"[Receiver] Подключение к {self.srt_url}")
        
        if not self._create_ffmpeg_process():
            print("[Receiver] Первая попытка подключения неудачна, будут повторные попытки...")
            # Не возвращаем False, продолжаем работу - retry будет в _loop

        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        
        if self.ffmpeg:
            print("[Receiver] Прием потока запущен")
        else:
            print("[Receiver] Ожидание подключения...")
        
        return True

    def _reconnect(self) -> bool:
        """Попытка переподключения к SRT потоку"""
        current_time = time.time()
        
        # Проверяем, прошло ли достаточно времени с последней попытки
        if current_time - self.last_reconnect_attempt < self.reconnect_interval:
            return False
        
        self.last_reconnect_attempt = current_time
        
        # Закрываем старый процесс если есть
        if self.ffmpeg:
            try:
                self.ffmpeg.terminate()
                self.ffmpeg.wait(timeout=1.0)
            except:
                pass
            self.ffmpeg = None
        
        print(f"[Receiver] Попытка переподключения к {self.srt_url}...")
        return self._create_ffmpeg_process()

    def _loop(self):
        frame_count = 0
        last_time = time.time()
        last_fps_print = time.time()

        while self.running:
            # Проверяем подключение
            if not self.ffmpeg or self.ffmpeg.poll() is not None:
                # Процесс завершился, пытаемся переподключиться
                if self.ffmpeg:
                    # Читаем ошибку только один раз
                    try:
                        err = self.ffmpeg.stderr.read().decode("utf-8", errors="ignore")
                        if err:
                            err_lines = err.split('\n')
                            for line in err_lines[-2:]:
                                if line.strip() and 'error' in line.lower():
                                    print(f"[Receiver] {line.strip()}")
                    except:
                        pass
                    self.ffmpeg = None
                
                # Пытаемся переподключиться
                if not self._reconnect():
                    # Ждем перед следующей попыткой
                    time.sleep(0.5)
                    continue
                else:
                    print("[Receiver] Подключение восстановлено!")
                    frame_count = 0
                    last_time = time.time()
                    last_fps_print = time.time()
            
            # Читаем кадр
            try:
                raw = self.ffmpeg.stdout.read(self.frame_size)
            except Exception as e:
                print(f"[Receiver] Ошибка чтения: {e}")
                self.ffmpeg = None
                continue
            
            if len(raw) != self.frame_size:
                # Неполный кадр - возможно поток прервался
                if self.ffmpeg.poll() is not None:
                    self.ffmpeg = None
                    continue
                continue

            # Декодируем кадр
            try:
                frame = np.frombuffer(raw, dtype=np.uint8).reshape(
                    (self.height, self.width, 3)
                )
            except Exception as e:
                print(f"[Receiver] Ошибка декодирования кадра: {e}")
                continue

            # Кладем в очередь
            try:
                self.frame_queue.put_nowait(frame)
            except queue.Full:
                self.frame_queue.get_nowait()
                self.frame_queue.put_nowait(frame)

            # Логирование FPS
            frame_count += 1
            now = time.time()
            if now - last_fps_print >= 5:
                fps = frame_count / (now - last_time)
                print(f"[Receiver] FPS: {fps:.1f}")
                frame_count = 0
                last_time = now
                last_fps_print = now

    def get_frame(self, timeout=0.1) -> Optional[Tuple[float, np.ndarray]]:
        try:
            frame = self.frame_queue.get(timeout=timeout)
            return time.time(), frame
        except queue.Empty:
            return None

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        if self.ffmpeg:
            try:
                self.ffmpeg.terminate()
                self.ffmpeg.wait(timeout=1.0)
            except:
                try:
                    self.ffmpeg.kill()
                except:
                    pass
        print("[Receiver] Остановлен")


def main():
    receiver = SRTReceiver()

    if not receiver.start():
        sys.exit(1)

    print("Прием кадров... Ctrl+C для выхода")
    count = 0
    start = time.time()

    try:
        while True:
            item = receiver.get_frame(timeout=1)
            if item:
                _, frame = item
                count += 1
                if count % 30 == 0:
                    fps = count / (time.time() - start)
                    print(f"[Main] Кадров: {count}, FPS: {fps:.1f}, shape={frame.shape}")
            else:
                print("[Main] Кадр не получен")
    except KeyboardInterrupt:
        pass
    finally:
        receiver.stop()


if __name__ == "__main__":
    main()
