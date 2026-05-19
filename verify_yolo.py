import os
import cv2
import numpy as np

def verify_yolo(img_dir, label_dir, output_dir="verification"):
    os.makedirs(output_dir, exist_ok=True)
    
    image_files = [f for f in os.listdir(img_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    if not image_files:
        print("Изображения в директории YOLO не найдены.")
        return

    for img_name in image_files:
        img_path = os.path.join(img_dir, img_name)
        label_path = os.path.join(label_dir, os.path.splitext(img_name)[0] + ".txt")
        
        if not os.path.exists(label_path):
            print(f"Разметка для {img_name} не найдена")
            continue
            
        img = cv2.imread(img_path)
        h, w, _ = img.shape
        
        with open(label_path, "r") as f:
            lines = f.readlines()
            
        for line in lines:
            parts = line.strip().split()
            if len(parts) != 5:
                continue
                
            cls, xc, yc, bw, bh = map(float, parts)
            
            # Конвертация формата YOLO в пиксельные координаты
            x1 = int((xc - bw/2) * w)
            y1 = int((yc - bh/2) * h)
            x2 = int((xc + bw/2) * w)
            y2 = int((yc + bh/2) * h)
            
            # Отрисовка рамки
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 3)
            cv2.putText(img, f"Class {int(cls)}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        output_path = os.path.join(output_dir, f"verified_{img_name}")
        cv2.imwrite(output_path, img)
        print(f"Верификационное изображение сохранено в {output_path}")

if __name__ == "__main__":
    verify_yolo(
        "labeler_app/datasets/yolo/images",
        "labeler_app/datasets/yolo/labels"
    )
