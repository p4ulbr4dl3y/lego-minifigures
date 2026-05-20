import torch
import torch.nn as nn
from torchvision import datasets, transforms, models
from torch.utils.data import DataLoader
import os

def evaluate_model(data_dir, weights_path='best_model.pth', batch_size=32):
    # Настройка устройства
    device = torch.device("cuda:0" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu"))
    print(f"Используемое устройство: {device}")

    # Стандартные преобразования для валидации и тестирования
    test_transform = transforms.Compose([
        transforms.Resize((128, 128)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    test_dir = os.path.join(data_dir, 'test')
    if not os.path.exists(test_dir):
        print(f"Тестовая директория не найдена по пути: {test_dir}")
        return

    test_dataset = datasets.ImageFolder(test_dir, test_transform)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=2)
    
    print(f"Загружен тестовый набор данных: {len(test_dataset)} изображений по классам: {test_dataset.classes}")

    # Воссоздание структуры модели
    model = models.efficientnet_b0()
    num_ftrs = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.4, inplace=True),
        nn.Linear(num_ftrs, 2)
    )
    
    # Загрузка весов
    if not os.path.exists(weights_path):
        print(f"Файл весов не найден по пути: {weights_path}")
        return
        
    model.load_state_dict(torch.load(weights_path, map_location=device))
    model = model.to(device)
    model.eval()

    correct = 0
    total = 0
    
    # Отслеживание метрик по классам
    # Класс 0 - минифигурки, класс 1 - другие объекты (по алфавитному порядку)
    tp, fp, fn, tn = 0, 0, 0, 0

    with torch.no_grad():
        for inputs, labels in test_loader:
            inputs = inputs.to(device)
            labels = labels.to(device)
            
            outputs = model(inputs)
            _, preds = torch.max(outputs, 1)
            
            total += labels.size(0)
            correct += (preds == labels).sum().item()
            
            # Расчет метрик при условии, что класс 0 является положительным классом минифигурок
            for p, l in zip(preds, labels):
                p, l = p.item(), l.item()
                if l == 0:  # Реальный положительный класс
                    if p == 0:
                        tp += 1
                    else:
                        fn += 1
                else:  # Реальный отрицательный класс
                    if p == 1:
                        tn += 1
                    else:
                        fp += 1

    accuracy = correct / total
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    print("\n--- Метрики на тестовом наборе ---")
    print(f"Общая точность: {accuracy:.4f} ({correct}/{total})")
    print(f"Точность предсказания: {precision:.4f}")
    print(f"Полнота: {recall:.4f}")
    print(f"Мера F1: {f1:.4f}")
    print("\nМатрица ошибок:")
    print(f"                   Предсказано: минифигурка  Предсказано: другой объект")
    print(f"Минифигурка        {tp:<24}  {fn:<20}")
    print(f"Другой объект      {fp:<24}  {tn:<20}")

if __name__ == "__main__":
    data_dir = "/Users/yegor/lego-dataset/prepared_dataset"
    evaluate_model(data_dir)
