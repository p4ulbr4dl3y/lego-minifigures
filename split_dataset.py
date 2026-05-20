import os
import shutil
import random

def split_dataset(src_dir, dest_dir, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15):
    classes = ['minifigures', 'not_minifigures']
    
    for cls in classes:
        # Создание директорий
        for split in ['train', 'val', 'test']:
            os.makedirs(os.path.join(dest_dir, split, cls), exist_ok=True)
        
        # Получение списка файлов
        cls_dir = os.path.join(src_dir, cls)
        files = [f for f in os.listdir(cls_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        random.shuffle(files)
        
        # Разделение выборки
        n = len(files)
        train_end = int(n * train_ratio)
        val_end = train_end + int(n * val_ratio)
        
        train_files = files[:train_end]
        val_files = files[train_end:val_end]
        test_files = files[val_end:]
        
        # Копирование файлов
        for f in train_files:
            shutil.copy(os.path.join(cls_dir, f), os.path.join(dest_dir, 'train', cls, f))
        for f in val_files:
            shutil.copy(os.path.join(cls_dir, f), os.path.join(dest_dir, 'val', cls, f))
        for f in test_files:
            shutil.copy(os.path.join(cls_dir, f), os.path.join(dest_dir, 'test', cls, f))
            
        print(f"Класс {cls}: {len(train_files)} для обучения, {len(val_files)} для валидации, {len(test_files)} для теста")

if __name__ == "__main__":
    src = "/Users/yegor/lego-dataset/labeler_app/datasets/classification"
    dest = "/Users/yegor/lego-dataset/prepared_dataset"
    split_dataset(src, dest)
