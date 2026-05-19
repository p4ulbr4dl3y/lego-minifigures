import sys
import os
import shutil
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QGraphicsView, QGraphicsScene, 
                             QGraphicsPixmapItem, QGraphicsRectItem, QFrame)
from PySide6.QtGui import QPixmap, QImage, QKeyEvent, QColor, QPen
from PySide6.QtCore import Qt, QSize
from PIL import Image, ImageOps

from sam_inference import Sam3Inference

class LegoLabeler(QMainWindow):
    def __init__(self, image_path):
        super().__init__()
        self.setWindowTitle(f"Lego Labeler - {os.path.basename(image_path)}")
        self.resize(1400, 900)

        self.image_path = image_path
        self.sam = Sam3Inference()
        
        # Data state
        self.objects, self.img_w, self.img_h = self.sam.predict(image_path)
        self.current_idx = 0
        self.labels = {} # idx -> "minifigure" or "not_minifigure"
        
        self.setup_ui()
        
        # Load main pixmap from oriented PIL image to match inference coordinates
        image_pil = Image.open(self.image_path).convert("RGB")
        image_pil = ImageOps.exif_transpose(image_pil)
        self.main_pixmap = QPixmap.fromImage(self.pil_to_qimage(image_pil))
        self.scene.addItem(QGraphicsPixmapItem(self.main_pixmap))
        
        # Highlight rectangle for current candidate
        self.highlight_rect = QGraphicsRectItem()
        self.highlight_rect.setPen(QPen(QColor(255, 0, 0), 4))
        self.scene.addItem(self.highlight_rect)
        
        self.setFocusPolicy(Qt.StrongFocus)
        self.update_display()
        self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left side: Full image context
        left_layout = QVBoxLayout()
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setMinimumWidth(800)
        self.view.setFocusPolicy(Qt.NoFocus) # Prevent view from stealing key events
        left_layout.addWidget(QLabel("Full Image Context (Box indicates current candidate)"))
        left_layout.addWidget(self.view)
        main_layout.addLayout(left_layout, 2)

        # Right side: Crop and Info
        right_layout = QVBoxLayout()
        
        # Crop View
        right_layout.addWidget(QLabel("Current Candidate (Crop):"))
        self.crop_label = QLabel()
        self.crop_label.setFixedSize(400, 400)
        self.crop_label.setFrameShape(QFrame.StyledPanel)
        self.crop_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.crop_label)

        # Info Panel
        info_frame = QFrame()
        info_frame.setFrameShape(QFrame.StyledPanel)
        info_layout = QVBoxLayout(info_frame)
        
        self.info_label = QLabel("Loading...")
        self.stats_label = QLabel("Stats: ...")
        self.controls_label = QLabel("Controls:\n[J] Minifigure\n[K] Not Minifigure\n[<- / ->] Navigate\n[Space] Save & Exit")
        
        info_layout.addWidget(self.info_label)
        info_layout.addWidget(self.stats_label)
        info_layout.addWidget(self.controls_label)
        
        right_layout.addWidget(info_frame)
        right_layout.addStretch()
        
        main_layout.addLayout(right_layout, 1)

    def update_display(self):
        if not self.objects:
            self.info_label.setText("No objects found!")
            return

        obj = self.objects[self.current_idx]
        
        # 1. Update Highlight Rect
        box = obj["box"]
        self.highlight_rect.setRect(box[0], box[1], box[2]-box[0], box[3]-box[1])

        # 2. Update Crop
        crop_pil = obj["white_bg_crop"]
        qimg = self.pil_to_qimage(crop_pil)
        crop_pixmap = QPixmap.fromImage(qimg).scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.crop_label.setPixmap(crop_pixmap)

        # 3. Update Info
        status = self.labels.get(self.current_idx, "Unlabeled")
        self.info_label.setText(f"Object {self.current_idx + 1} / {len(self.objects)}\nStatus: {status}")
        
        # Stats
        mini_count = list(self.labels.values()).count("minifigure")
        not_mini_count = list(self.labels.values()).count("not_minifigure")
        self.stats_label.setText(f"Session:\nMinifigures: {mini_count}\nNot Minifigures: {not_mini_count}")

    def pil_to_qimage(self, pil_img):
        # Convert to RGB if needed
        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")
        
        data = pil_img.tobytes("raw", "RGB")
        width, height = pil_img.size
        bytes_per_line = 3 * width
        # Use .copy() to ensure QImage owns the data and doesn't point to GC'd PIL buffer
        return QImage(data, width, height, bytes_per_line, QImage.Format_RGB888).copy()

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key == Qt.Key_J:
            self.labels[self.current_idx] = "minifigure"
            self.next_object()
        elif key == Qt.Key_K:
            self.labels[self.current_idx] = "not_minifigure"
            self.next_object()
        elif key == Qt.Key_Right:
            self.next_object()
        elif key == Qt.Key_Left:
            self.prev_object()
        elif key == Qt.Key_Space:
            self.save_dataset()
            self.close()

    def next_object(self):
        if self.current_idx < len(self.objects) - 1:
            self.current_idx += 1
            self.update_display()
        else:
            print("Reached last object. Press Space to save.")

    def prev_object(self):
        if self.current_idx > 0:
            self.current_idx -= 1
            self.update_display()

    def save_dataset(self):
        print("Saving results...")
        base_name = os.path.basename(self.image_path)
        name_no_ext = os.path.splitext(base_name)[0]
        
        # 1. Classification Crops
        for idx, label in self.labels.items():
            obj = self.objects[idx]
            folder = "minifigures" if label == "minifigure" else "not_minifigures"
            save_path = f"labeler_app/datasets/classification/{folder}/{name_no_ext}_obj{idx}.jpg"
            obj["white_bg_crop"].save(save_path)
            
        # 2. YOLO Dataset
        yolo_labels = []
        for idx, label in self.labels.items():
            if label == "minifigure":
                box = self.objects[idx]["normalized_box"]
                # YOLO format: class xc yc w h (class 0 for minifigure)
                yolo_labels.append(f"0 {box[0]} {box[1]} {box[2]} {box[3]}")
        
        if yolo_labels:
            # Copy image
            shutil.copy(self.image_path, f"labeler_app/datasets/yolo/images/{base_name}")
            # Save labels
            with open(f"labeler_app/datasets/yolo/labels/{name_no_ext}.txt", "w") as f:
                f.write("\n".join(yolo_labels))
                
        print("Done!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    test_img = "/Users/yegor/lego-dataset/avito_parser/lego_full_images/ad_99_Lego минифигурки Серийки/photo_2.jpg"
    if not os.path.exists(test_img):
        print(f"Error: Test image not found at {test_img}")
        sys.exit(1)
    window = LegoLabeler(test_img)
    window.show()
    sys.exit(app.exec())
