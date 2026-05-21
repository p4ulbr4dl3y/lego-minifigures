import sys
import os
import shutil
import json
from collections import deque
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QGraphicsView, QGraphicsScene, 
                             QGraphicsPixmapItem, QGraphicsRectItem, QFrame, QProgressBar)
from PySide6.QtGui import QPixmap, QImage, QKeyEvent, QColor, QPen
from PySide6.QtCore import Qt, QSize, QThread, Signal, Slot
from PIL import Image, ImageOps

from sam_inference import Sam3Inference

# --- Персистентность ---
DB_PATH = "labeler_app/processed.json"

def load_processed():
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, "r") as f:
                content = f.read().strip()
                if not content:
                    return set()
                return set(json.loads(content))
        except (json.JSONDecodeError, ValueError):
            return set()
    return set()

def save_processed(processed_set):
    with open(DB_PATH, "w") as f:
        json.dump(list(processed_set), f)

# --- Фоновый обработчик ---
class SamWorker(QThread):
    result_ready = Signal(dict)  # Содержит {path, objects, w, h}
    progress = Signal(str)

    def __init__(self, image_paths, queue_ref):
        super().__init__()
        self.image_paths = image_paths
        self.queue_ref = queue_ref
        self.sam = None
        self._is_running = True

    def run(self):
        self.sam = Sam3Inference()
        for path in self.image_paths:
            if not self._is_running:
                break
            # Пауза, если очередь заполнена (backpressure)
            while len(self.queue_ref) >= self.queue_ref.maxlen and self._is_running:
                self.msleep(100)
            if not self._is_running:
                break
            self.progress.emit(f"Обработка {os.path.basename(path)}...")
            try:
                objects, w, h = self.sam.predict(path)
                if not self._is_running:
                    break
                self.result_ready.emit({
                    "path": path,
                    "objects": objects,
                    "w": w,
                    "h": h
                })
            except Exception as e:
                print(f"Ошибка обработки {path}: {e}")

    def stop(self):
        self._is_running = False

class LegoLabeler(QMainWindow):
    def __init__(self, all_images):
        super().__init__()
        self.setWindowTitle("Lego Labeler - Multi-Image Mode")
        self.resize(1400, 950)

        self.processed = load_processed()
        self.pending_images = [p for p in all_images if p not in self.processed]
        self.total_images = len(all_images)
        
        # Состояние текущего изображения
        self.current_data = None  # {path, objects, w, h}
        self.current_idx = 0     # индекс объекта внутри изображения
        self.labels = {}         # idx -> метка
        self.queue = deque(maxlen=5)  # очередь обработанных данных из фонового потока

        self.setup_ui()
        
        # Запуск фонового обработчика
        self.worker = SamWorker(self.pending_images, self.queue)
        self.worker.result_ready.connect(self.on_data_ready)
        self.worker.progress.connect(lambda msg: self.info_label.setText(f"Worker: {msg}"))
        self.worker.start()

        self.setFocusPolicy(Qt.StrongFocus)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Левая панель
        left_layout = QVBoxLayout()
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setMinimumWidth(800)
        self.view.setFocusPolicy(Qt.NoFocus)
        left_layout.addWidget(QLabel("Контекст изображения"))
        left_layout.addWidget(self.view)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(self.total_images)
        self.progress_bar.setValue(len(self.processed))
        left_layout.addWidget(self.progress_bar)
        main_layout.addLayout(left_layout, 2)

        # Правая панель
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Текущий кандидат:"))
        self.crop_label = QLabel()
        self.crop_label.setFixedSize(400, 400)
        self.crop_label.setFrameShape(QFrame.StyledPanel)
        self.crop_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.crop_label)

        info_frame = QFrame()
        info_frame.setFrameShape(QFrame.StyledPanel)
        info_layout = QVBoxLayout(info_frame)
        self.info_label = QLabel("Ожидание SAM3...")
        self.img_info_label = QLabel("")
        self.stats_label = QLabel("")
        info_layout.addWidget(self.info_label)
        info_layout.addWidget(self.img_info_label)
        info_layout.addWidget(self.stats_label)
        info_layout.addWidget(QLabel("\n[J] Минифигурка\n[K] Не минифигурка\n[<- / ->] Навигация"))
        
        right_layout.addWidget(info_frame)
        right_layout.addStretch()
        main_layout.addLayout(right_layout, 1)

        self.highlight_rect = None
        self.main_pixmap_item = None

    @Slot(dict)
    def on_data_ready(self, data):
        self.queue.append(data)
        if self.current_data is None:
            self.load_next_image_from_queue()

    def load_next_image_from_queue(self):
        if not self.queue:
            self.current_data = None
            self.info_label.setText("Очередь пуста. Обработка...")
            return

        self.current_data = self.queue.popleft()
        
        # Автоматический пропуск изображений без объектов
        if not self.current_data["objects"]:
            print(f"Объекты не найдены в {self.current_data['path']}. Пропуск.")
            with open("labeler_app/problematic_images.txt", "a") as f:
                f.write(self.current_data["path"] + "\n")
            self.processed.add(self.current_data["path"])
            save_processed(self.processed)
            self.load_next_image_from_queue()
            return

        self.current_idx = 0
        self.labels = {}
        
        # Загрузка основного изображения
        image_pil = Image.open(self.current_data["path"]).convert("RGB")
        image_pil = ImageOps.exif_transpose(image_pil)
        qimg = self.pil_to_qimage(image_pil)
        
        self.scene.clear()
        self.main_pixmap_item = QGraphicsPixmapItem(QPixmap.fromImage(qimg))
        self.scene.addItem(self.main_pixmap_item)
        
        self.highlight_rect = QGraphicsRectItem()
        self.highlight_rect.setPen(QPen(QColor(255, 0, 0), 4))
        self.scene.addItem(self.highlight_rect)
        
        self.update_display()
        self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    def update_display(self):
        if not self.current_data or not self.current_data["objects"]:
            self.img_info_label.setText("Объекты на изображении не найдены.")
            return

        obj = self.current_data["objects"][self.current_idx]
        box = obj["box"]
        self.highlight_rect.setRect(box[0], box[1], box[2]-box[0], box[3]-box[1])

        crop_pil = obj["white_bg_crop"]
        qimg = self.pil_to_qimage(crop_pil)
        self.crop_label.setPixmap(QPixmap.fromImage(qimg).scaled(400, 400, Qt.KeepAspectRatio))

        status = self.labels.get(self.current_idx, "Не размечено")
        self.img_info_label.setText(f"Изображение: {os.path.basename(self.current_data['path'])}\n"
                                   f"Объект: {self.current_idx + 1} / {len(self.current_data['objects'])}\n"
                                   f"Статус: {status}")
        
        self.stats_label.setText(f"Обработано: {len(self.processed)} / {self.total_images}")
        self.progress_bar.setValue(len(self.processed))

    def pil_to_qimage(self, pil_img):
        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")
        data = pil_img.tobytes("raw", "RGB")
        return QImage(data, pil_img.size[0], pil_img.size[1], 3 * pil_img.size[0], QImage.Format_RGB888).copy()

    def keyPressEvent(self, event: QKeyEvent):
        if not self.current_data: return
        
        key = event.key()
        if key == Qt.Key_J:
            self.labels[self.current_idx] = "minifigure"
            self.next_object()
        elif key == Qt.Key_K:
            self.labels[self.current_idx] = "not_minifigure"
            self.next_object()
        elif key == Qt.Key_Right:
            self.next_object(auto_next_img=False)
        elif key == Qt.Key_Left:
            if self.current_idx > 0:
                self.current_idx -= 1
                self.update_display()

    def next_object(self, auto_next_img=True):
        if self.current_idx < len(self.current_data["objects"]) - 1:
            self.current_idx += 1
            self.update_display()
        elif auto_next_img:
            self.finalize_current_image()

    def finalize_current_image(self):
        self.save_current_results()
        self.processed.add(self.current_data["path"])
        save_processed(self.processed)
        self.load_next_image_from_queue()

    def save_current_results(self):
        if not self.current_data:
            return

        path = self.current_data["path"]
        name = os.path.splitext(os.path.basename(path))[0]
        num_objs = len(self.current_data["objects"])

        # Классификация
        for idx, label in self.labels.items():
            if idx >= num_objs: continue
            obj = self.current_data["objects"][idx]
            folder = "minifigures" if label == "minifigure" else "not_minifigures"
            save_dir = f"labeler_app/datasets/classification/{folder}"
            os.makedirs(save_dir, exist_ok=True)
            obj["white_bg_crop"].save(f"{save_dir}/{name}_obj{idx}.jpg")

        # Формат YOLO
        yolo_lines = []
        for idx, label in self.labels.items():
            if idx < num_objs and label == "minifigure":
                b = self.current_data["objects"][idx]["normalized_box"]
                yolo_lines.append(f"0 {b[0]} {b[1]} {b[2]} {b[3]}")

        if yolo_lines:
            img_save_dir = "labeler_app/datasets/yolo/images"
            lbl_save_dir = "labeler_app/datasets/yolo/labels"
            os.makedirs(img_save_dir, exist_ok=True)
            os.makedirs(lbl_save_dir, exist_ok=True)

            shutil.copy(path, f"{img_save_dir}/{os.path.basename(path)}")
            with open(f"{lbl_save_dir}/{name}.txt", "w") as f:
                f.write("\n".join(yolo_lines))

    def closeEvent(self, event):
        print("Завершение работы приложения...")
        if self.worker.isRunning():
            self.worker.result_ready.disconnect()
            self.worker.progress.disconnect()
            self.worker.stop()
            self.worker.quit()
            if not self.worker.wait(10000):
                print("Воркер не завершился за 10 секунд, принудительное завершение")
                self.worker.terminate()
                self.worker.wait()
        event.accept()
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    root_dir = "/Users/yegor/lego-dataset/avito_parser/lego_full_images"
    all_imgs = []
    for root, _, files in os.walk(root_dir):
        for f in files:
            if f.lower().endswith((".jpg", ".jpeg", ".png")):
                all_imgs.append(os.path.join(root, f))
    
    all_imgs.sort()
    window = LegoLabeler(all_imgs)
    window.show()
    sys.exit(app.exec())
