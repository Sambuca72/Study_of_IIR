import argparse
import os
import time
import threading
import subprocess
from queue import Queue

import cv2 
import torch
import imageio_ffmpeg 
from ultralytics import YOLO

def process_frame(model, frame, imgsz=640, conf=0.25):
    with torch.inference_mode():
        results = model.predict(frame, imgsz=imgsz, conf=conf, device="cpu", verbose=False)
    return results[0].plot()


class VideoReader:
    def __init__(self, video_path):
        self.is_camera = False
        self.video_path = video_path
        
        if str(video_path).isdigit():
            self.video_path = int(video_path)
            self.is_camera = True
            
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            raise RuntimeError(f"Can not open videoflow: {self.video_path}")
            
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0:
            self.fps = 25
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.idx = 0
        
        # Для камеры запускаем выделенный поток, который в фоне сдувает все кадры, сохраняя только один самый свежий
        # Это полностью убирает задержку
        if self.is_camera:
            self.latest_frame = None
            self.running = True
            self.cam_thread = threading.Thread(target=self._cam_read_loop)
            self.cam_thread.daemon = True
            self.cam_thread.start()

    def _cam_read_loop(self):
        while self.running and self.cap.isOpened():
            ok, frame = self.cap.read()
            if ok:
                self.latest_frame = frame
            else:
                break

    def read_frame(self):
        if self.is_camera:
            # Ждем пока появится первый кадр
            while self.latest_frame is None and self.running:
                time.sleep(0.01)
            
            if not self.running or self.latest_frame is None:
                return None, None
                
            idx = self.idx
            self.idx += 1
            return idx, self.latest_frame.copy()
        else:
            ok, frame = self.cap.read()
            if not ok:
                return None, None
            idx = self.idx
            self.idx += 1
            return idx, frame

    def __del__(self):
        self.running = False
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()


class VideoWriter:
    def __init__(self, output_path, fps, width, height):
        self.output_path = output_path
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        if not self.writer.isOpened():
            raise RuntimeError(f"Can not save video: {output_path}")

    def write_frame(self, frame, width, height):
        if frame.shape[1] != width or frame.shape[0] != height:
            frame = cv2.resize(frame, (width, height))
        self.writer.write(frame)

    def __del__(self):
        if hasattr(self, 'writer') and self.writer.isOpened():
            self.writer.release()
            print(f"Saved video without sound: {self.output_path}")


# функция, которая берёт обработанное видео без звука и добавляет в него звук из исходного видео
def add_audio(original_video, processed_video, output_video):
    temp_output = output_video + ".tmp.mp4" # временный файл

    os.replace(processed_video, temp_output) # обработанное видео переименовывается во временный файл

    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

    cmd = [ffmpeg_path, "-y", "-i", temp_output, "-i", original_video, "-map", "0:v:0",
           "-map", "1:a?", "-c:v", "copy", "-c:a", "aac", "-shortest", output_video]
    subprocess.run(cmd, check=True)

    if os.path.exists(temp_output):
        os.remove(temp_output)

    print(f"Saved video with sound: {output_video}")

# функция для режима сингл т.е обработка видео в одном потоке
def run_single(video_path, output_path, model_path):
    start = time.perf_counter() # запоминает время старта

    reader = VideoReader(video_path)
    writer = None
    model = YOLO(model_path)

    while True:
        idx, frame = reader.read_frame()
        if frame is None:
            break
            
        print(f"Single: frame {idx + 1}")
        annotated = process_frame(model, frame) # обработка кадра через модельку
        
        # только когда готов первый обработанный кадр, мы создаем файл
        if writer is None:
            writer = VideoWriter(output_path, reader.fps, reader.width, reader.height)
        writer.write_frame(annotated, reader.width, reader.height)
        
        if str(video_path).isdigit():
            cv2.imshow("Real-Time single", annotated)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    if str(video_path).isdigit():
        cv2.destroyAllWindows()
    del writer
    del reader

    if not str(video_path).isdigit():
        try:
            add_audio(video_path, output_path, output_path)
        except Exception as e:
            print(f"Skipping audio addition: {e}")

    elapsed = time.perf_counter() - start
    print(f"Single-thread time: {elapsed:.3f} sec")
    return elapsed

# функция одного рабочего потока
# input_buffer это очередь с кадрами, которые надо обработать
def worker(input_buffer, output_buffer, model_path, worker_id):
    try:
        model = YOLO(model_path)

        while True:
            item = input_buffer.get() # worker берёт один элемент из очереди input_buffer

            if item is None:
                break

            idx, frame = item
            annotated = process_frame(model, frame)

            output_buffer.put(("ok", idx, annotated))

    except Exception as e:
        output_buffer.put(("error", worker_id, str(e)))
    finally:
        output_buffer.put(("done", worker_id, None))


def run_multi(video_path, output_path, model_path, workers_count):
    start = time.perf_counter()

    reader = VideoReader(video_path)

    # для камеры буфер минимальный
    # для видеофайла можно побольше
    buffer_scale = 1 if str(video_path).isdigit() else 100
    input_buffer = Queue(maxsize=buffer_scale)
    output_buffer = Queue() # очередь результатов: обработанные кадры или ошибки

    # собственно инициализация работников
    threads = []
    for worker_id in range(workers_count):
        t = threading.Thread(
            target=worker, # внутри потока надо запустить функцию worker
            args=(input_buffer, output_buffer, model_path, worker_id))
        t.daemon = True # смерть потоков вместе с программой
        t.start()
        threads.append(t)

    # запускаем поток для чтения кадров, который будет их ложить уже в инпут буфер
    def vreader(q_in, reader):
        total_p = 0
        while True:
            idx, frame = reader.read_frame()
            if frame is None:
                break
            q_in.put((idx, frame))
            total_p += 1
        
        for _ in range(workers_count):
            q_in.put(None)
        return total_p
        
    reader_thread = threading.Thread(target=vreader, args=(input_buffer, reader))
    reader_thread.daemon = True
    reader_thread.start()

    results = {}
    current_write_idx = 0
    writer = None
    frames_received = 0
    completed_workers = 0
    stop_requested = False


    while completed_workers < workers_count:
        status, a, b = output_buffer.get()

        if status == "error":
            raise RuntimeError(f"Worker {a} crashed: {b}")
        elif status == "done":
            completed_workers += 1
            continue

        # сортировка кадров по ходу дела некий словарь
        idx = a
        annotated = b
        results[idx] = annotated
        frames_received += 1
        
        if writer is None:
            writer = VideoWriter(output_path, reader.fps, reader.width, reader.height)

        # Пишем кадры в правильном порядке
        while current_write_idx in results:
            frame_to_write = results.pop(current_write_idx)
            writer.write_frame(frame_to_write, reader.width, reader.height)
            
            if str(video_path).isdigit():
                cv2.imshow("RealTime Multi", frame_to_write)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    stop_requested = True
                    break
            current_write_idx += 1

        if stop_requested:
            break

    if not stop_requested:
        for t in threads:
            t.join()
        reader_thread.join()

    if str(video_path).isdigit():
        cv2.destroyAllWindows()

    del writer
    del reader

    if not str(video_path).isdigit():
        try:
            add_audio(video_path, output_path, output_path)
        except Exception as e:
            print(f"Skipping audio addition: {e}")

    elapsed = time.perf_counter() - start
    print(f"Multi-thread time: {elapsed:.3f} sec")
    print(f"Workers: {workers_count}")
    return elapsed


def run_benchmark(video_path, output_path, model_path, max_workers):
    results = []

    # проверяем разное количество потоков
    for workers in range(1, max_workers + 1):
        out_name = output_path.replace(".mp4", f"_w{workers}.mp4")

        print(f"\nTesting workers = {workers}")

        # запускаем многопоточную обработку с текущим числом потоков
        elapsed = run_multi(video_path=video_path, output_path=out_name, model_path=model_path, workers_count=workers)
        results.append((workers, elapsed))

    print("\nBenchmark result:")
    print("workers | time | speedup")

    # время при 1 потоке берём как базовое
    # с ним будем сравнивать остальные запуски
    base_time = results[0][1]

    # переменные для поиска самого быстрого варианта
    best_workers = None
    best_time = 10**9

    for workers, elapsed in results:
        speedup = base_time / elapsed

        print(f"{workers:7d} | {elapsed:6.3f} | {speedup:6.3f}x")

        if elapsed < best_time:
            best_time = elapsed
            best_workers = workers
    print(f"\nBest workers count: {best_workers}")
    print(f"Best time: {best_time:.3f} sec")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--video", required=True, help="Путь к входному видео")
    parser.add_argument("--mode", required=True, choices=["single", "multi", "bench"])
    parser.add_argument("--output", required=True, help="Путь к выходному видео")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--max-workers", type=int, default=os.cpu_count())
    parser.add_argument("--model", default="yolov8s-pose.pt")

    args = parser.parse_args()
    torch.set_num_threads(1)

    if args.mode == "single":
        run_single(args.video, args.output, args.model)
    elif args.mode == "multi":
        run_multi(args.video, args.output, args.model, args.workers)
    elif args.mode == "bench":
        run_benchmark(args.video, args.output, args.model, args.max_workers)

if __name__ == "__main__":
    main()
