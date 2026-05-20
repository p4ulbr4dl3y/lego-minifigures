import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms, models
from torch.utils.data import DataLoader
import os
import copy
from tqdm import tqdm

def train_model(data_dir, model_name='efficientnet_b0', num_epochs=50, batch_size=32, learning_rate=1e-4, patience=10):
    # Настройка устройства
    if torch.cuda.is_available():
        device = torch.device("cuda:0")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    print(f"Используемое устройство: {device}")

    # Аугментация и нормализация данных
    data_transforms = {
        'train': transforms.Compose([
            transforms.Resize((128, 128)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(20),
            transforms.ColorJitter(brightness=0.2, contrast=0.2), # Без изменения цветового тона по требованию заказчика
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
        'val': transforms.Compose([
            transforms.Resize((128, 128)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
    }

    # Загрузка наборов данных
    image_datasets = {x: datasets.ImageFolder(os.path.join(data_dir, x), data_transforms[x])
                      for x in ['train', 'val']}
    dataloaders = {x: DataLoader(image_datasets[x], batch_size=batch_size, shuffle=True, num_workers=2)
                   for x in ['train', 'val']}
    dataset_sizes = {x: len(image_datasets[x]) for x in ['train', 'val']}
    class_names = image_datasets['train'].classes

    # Загрузка предобученной модели EfficientNet-B0
    model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
    
    # Изменение классификатора для бинарной классификации
    num_ftrs = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.4, inplace=True),
        nn.Linear(num_ftrs, 2)
    )
    
    # Загрузка лучших весов для возобновления обучения, если они существуют
    weights_path = 'best_model.pth'
    if os.path.exists(weights_path):
        print(f"Загрузка весов из {weights_path} для возобновления обучения.")
        try:
            model.load_state_dict(torch.load(weights_path, map_location=device))
        except Exception as e:
            print(f"Не удалось загрузить веса из {weights_path}: {e}. Начало обучения с нуля.")
    
    model = model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-2)

    best_model_wts = copy.deepcopy(model.state_dict())
    best_acc = 0.0
    best_loss = float('inf')
    counter = 0

    for epoch in range(num_epochs):
        print(f'Эпоха {epoch}/{num_epochs - 1}')
        print('-' * 10)

        for phase in ['train', 'val']:
            if phase == 'train':
                model.train()
            else:
                model.eval()

            running_loss = 0.0
            running_corrects = 0

            for inputs, labels in tqdm(dataloaders[phase], desc='Обучение' if phase == 'train' else 'Валидация'):
                inputs = inputs.to(device)
                labels = labels.to(device)

                optimizer.zero_grad()

                with torch.set_grad_enabled(phase == 'train'):
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    loss = criterion(outputs, labels)

                    if phase == 'train':
                        loss.backward()
                        optimizer.step()

                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)

            epoch_loss = running_loss / dataset_sizes[phase]
            epoch_acc = running_corrects.float() / dataset_sizes[phase]

            phase_name = 'Обучение' if phase == 'train' else 'Валидация'
            print(f'{phase_name} - потери: {epoch_loss:.4f}, точность: {epoch_acc:.4f}')

            # Ранняя остановка и сохранение контрольной точки модели
            if phase == 'val':
                if epoch_loss < best_loss:
                    best_loss = epoch_loss
                    best_acc = epoch_acc
                    best_model_wts = copy.deepcopy(model.state_dict())
                    counter = 0
                    torch.save(best_model_wts, 'best_model.pth')
                    print("Потери на валидации снизились. Сохранение модели.")
                else:
                    counter += 1
                    print(f"Потери на валидации не снизились. Счетчик: {counter}/{patience}")

        if counter >= patience:
            print(f"Сработала ранняя остановка на эпохе {epoch}")
            break

    print(f'Лучшая точность на валидации: {best_acc:.4f}')
    model.load_state_dict(best_model_wts)
    return model

if __name__ == "__main__":
    data_dir = "/Users/yegor/lego-dataset/prepared_dataset"
    train_model(data_dir)
