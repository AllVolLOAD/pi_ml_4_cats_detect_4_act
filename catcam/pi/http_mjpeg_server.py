#!/usr/bin/env python3
"""
Простой HTTP MJPEG сервер для стриминга с USB камеры
"""
import cv2
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
import sys

class MJPEGHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=--jpgboundary')
            self.end_headers()
            
            cap = cv2.VideoCapture(0)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            cap.set(cv2.CAP_PROP_FPS, 30)
            
            try:
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    # Кодируем кадр в JPEG
                    _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    
                    # Отправляем кадр (правильный формат multipart/x-mixed-replace)
                    self.wfile.write(b'--jpgboundary\r\n')
                    self.wfile.write(b'Content-Type: image/jpeg\r\n')
                    self.wfile.write(f'Content-Length: {len(jpeg)}\r\n'.encode())
                    self.wfile.write(b'\r\n')
                    self.wfile.write(jpeg.tobytes())
                    self.wfile.write(b'\r\n')
                    self.wfile.flush()
            finally:
                cap.release()
    
    def log_message(self, format, *args):
        pass  # Отключаем логирование

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
    server = HTTPServer(('0.0.0.0', port), MJPEGHandler)
    print(f"MJPEG сервер запущен на порту {port}")
    print(f"Подключение: http://<PI_IP>:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()

