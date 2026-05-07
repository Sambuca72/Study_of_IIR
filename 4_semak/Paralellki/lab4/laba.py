import threading
import argparse
import logging
from queue import Queue, Empty
import time
import os
import sys
import cv2
import numpy as np

os.environ['OPENCV_LOG_LEVEL'] = 'OFF'
os.environ['OPENCV_VIDEOIO_PRIORITY_MSMF'] = '0'

os.makedirs("lab4/log", exist_ok=True)

logging.basicConfig(filename='lab4/log/app.log', filemode="w", format="[%(relativeCreated)d ms] [%(levelname)s] %(message)s", level=logging.INFO, encoding='utf-8')
parser = argparse.ArgumentParser(prog='task.py', description='Чтение данных с камеры', epilog='python lab4/task.py --camera 0 --size 1440x960 --fps 30')
parser.add_argument('--camera', type=str, default='0')
parser.add_argument('--size', type=str, default='1440x960')
parser.add_argument('--fps', type=int, default=30)
args = parser.parse_args()

# Любой метод класса Sensor должен быть наследником и иметь метод get(), чтобы возвращать данные сенсора
class Sensor:
    def get(self):
        raise NotImplementedError("Subclasses must implement method get()")
    

class SensorX(Sensor):
    def __init__(self, delay: float):
        self._delay = delay
        self._data = 0
    
    def get(self) -> int:
        time.sleep(self._delay)
        self._data += 1
        return self._data


class SensorCam(Sensor):
    def __init__(self, camera, resolution):
        camera = int(camera) if camera.isdigit() else camera
        self.camera = cv2.VideoCapture(camera, cv2.CAP_DSHOW)
        self._reconnect_start_time = None

        if not self.camera.isOpened():
            logging.error(f"Камера {camera} не открылась")
            raise RuntimeError(f"Камера {camera} не открылась")
        
        logging.info(f"Камера {camera} установлена")
        
        size = resolution.lower().split('x')
        if len(size) == 2:
            width, height = size
        else:
            logging.error(f"Некорректное разрешение. Пример: 1280x720")
            raise ValueError("Некорректное разрешение")

        if not width.isdigit() or not height.isdigit():
            logging.error(f"Ширина и высота - целые числа")
            raise ValueError("Ширина и высота - целые числа")
        
        width, height = int(width), int(height)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        real_width = self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)
        real_height = self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)

        if int(real_width) != width or int(real_height) != height:
            logging.warning(f"Камера не поддерживает разрешение: {width}x{height}")
        self.real_width = real_width
        self.real_height = real_height
        logging.info(f"Установлено разрешение: {real_width}x{real_height}")

    def get(self):
        ret, frame = self.camera.read()

        if not ret:
            if self._start_time is None:
                self._start_time = time.time()
                logging.warning("Нет соединения с камерой. Начало попыток переподключения..")
            
            elapsed = time.time() - self._start_time
            if elapsed > 5:
                logging.error(f"Не удалось восстановить соединение с камерой после {elapsed:.1f} секунд")
                stop_event.set()
                return None

            self.camera.release()
            
            camera_id = int(args.camera) if args.camera.isdigit() else args.camera
            self.camera = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
            
            if self.camera.isOpened():
                size = args.size.lower().split('x')
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, int(size[0]))
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, int(size[1]))
                
                ret, frame = self.camera.read()
                if ret:
                    logging.info("Камера успешно восстановлена")
                    self._start_time = None
                    return frame
            
            return None
        
        self._start_time = None
        return frame
            
    def stop(self):
        self.camera.release()
        logging.info("Камера освобождена")


class WindowImage():
    def __init__(self, fps):
        if fps <= 0:
            logging.error("fps должно быть больше 0")
            raise ValueError("fps должно быть больше 0")
        self.fps = fps
        logging.info("Окно создано")

    def show(self, img):
        try:
            cv2.imshow('Window', img)
            return cv2.waitKey(int(1000 / self.fps)) & 0xFF
        except Exception as e:
            logging.error(f"Не удалось отобразить изображение: {e}")
            raise RuntimeError(f"Не удалось отобразить изображение: {e}")

    def stop(self):
        cv2.destroyAllWindows()
        logging.info("Окно закрыто")


def worker(sensor, q, stop_event):
    while not stop_event.is_set():
        try:
            data = sensor.get()
        except Exception as e:
            print(e)
            stop_event.set()
            break

        if data is not None:
            try:
                q.get_nowait() # удаление старых данных
            except Empty:
                pass
            q.put(data)
        else:
            try:
                q.get_nowait()
            except Empty:
                pass
            q.put(None)

# если камера не открылась, то пока-пока
try:
    camera_sensor = SensorCam(args.camera, args.size)
except Exception as e:
    logging.error(f"Не удалось создать камеру: {e}")
    print(e)
    sys.exit(1)

sensor_100 = SensorX(1 / 100)
sensor_10 = SensorX(1 / 10)
sensor_1 = SensorX(1 / 1)

try:
    window = WindowImage(args.fps)
except Exception as e:
    logging.error(f"Не удалось создать окно: {e}")
    print(e)
    sys.exit(1)

# При получении данных сенсор пытается положить их в очередь, но
# если цикл не успел обработать старый данные, то он удаляет их и кладет новые данные, что позволяет видеть только актуал данные
cam_queue = Queue(maxsize=1)
q100 = Queue(maxsize=1)
q10 = Queue(maxsize=1)
q1 = Queue(maxsize=1)

stop_event = threading.Event()

# Запуск 4х паралельных потоков
threads = [
    threading.Thread(target=worker, args=(camera_sensor, cam_queue, stop_event), name='camera_sensor'),
    threading.Thread(target=worker, args=(sensor_100, q100, stop_event), name='sensor_100'),
    threading.Thread(target=worker, args=(sensor_10, q10, stop_event), name='sensor_10'),
    threading.Thread(target=worker, args=(sensor_1, q1, stop_event), name='sensor_1')]
cam_frame, frame_100, frame_10, frame_1 = None, 0, 0, 0

for thread in threads:
    thread.start()
    logging.info(f"Поток {thread.name} запущен")

try:
    while True:
        if stop_event.is_set():
            break
        # Забираем самый свежий кадр из очереди камеры
        try:
            new_frame = cam_queue.get_nowait()
            cam_frame = new_frame
        except Empty:
            pass

        try:
            while True:
                frame_100 = q100.get_nowait()
        except Empty:
            pass

        try:
            while True:
                frame_10 = q10.get_nowait()
        except Empty:
            pass

        try:
            while True:
                frame_1 = q1.get_nowait()
        except Empty:
            pass

        # Вывод в окне при отключении камеры с выводом дальнейшей надписи переподключения
        if cam_frame is not None:
            img = cam_frame.copy()
        else:
            h, w = int(camera_sensor.real_height), int(camera_sensor.real_width)
            img = np.zeros((h, w, 3), dtype=np.uint8)
            cv2.putText(img, "RECONNECTING...", (w//2-150, h//2), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        cv2.putText(img, f"Sensor100: {frame_100}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(img, f"Sensor10: {frame_10}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(img, f"Sensor1: {frame_1}", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        try:
            key = window.show(img)
        except Exception:
            break

        if key == ord('q'):
            logging.info("Нажата клавиша q")
            break
finally:
    stop_event.set()

    for thread in threads:
        thread.join()
        logging.info(f"Поток {thread.name} остановился")

    camera_sensor.stop()
    window.stop()