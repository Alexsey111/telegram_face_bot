# Код загрузки части датасета и создания коллажа
import os
import random
import numpy as np
from sklearn.datasets import fetch_lfw_people
from PIL import Image, ImageDraw, ImageFont

# 1. Загружаем датасет LFW
lfw = fetch_lfw_people(color=True, resize=1.0, min_faces_per_person=5)
images, names = lfw.images, lfw.target_names

# Приводим изображения к uint8 (PIL не поддерживает float32)
images = (images * 255).astype(np.uint8)

# 2. Создаём папку для хранения изображений
dataset_path = "/content/dataset"
os.makedirs(dataset_path, exist_ok=True)

# 3. Выбираем 20 случайных студентов и сохраняем их изображения
num_students = 20
selected_indices = random.sample(range(len(images)), num_students)

students = []  # Список для хранения (имя, путь к файлу)

for i, idx in enumerate(selected_indices):
    name = names[lfw.target[idx]]
    img = images[idx]

    # Формируем путь к файлу
    filename = f"{i+1:02d}_{name.replace(' ', '_')}.jpg"
    file_path = os.path.join(dataset_path, filename)

    # Сохраняем изображение
    Image.fromarray(img).save(file_path)

    # Добавляем в список
    students.append((name, file_path))

print(f"✅ 20 изображений сохранены в {dataset_path}")

# 4. Создаём коллаж из сохранённых изображений
rows, cols = 4, 5
face_size = 125  # Размер лица в коллаже
collage_width = cols * face_size
collage_height = rows * face_size
collage = Image.new("RGB", (collage_width, collage_height), (255, 255, 255))
draw = ImageDraw.Draw(collage)
font = ImageFont.load_default()

for idx, (name, file_path) in enumerate(students):
    row, col = divmod(idx, cols)

    # Загружаем сохранённое изображение
    img_pil = Image.open(file_path)

    # Получаем текущие размеры изображения
    img_width, img_height = img_pil.size
    scale = face_size / max(img_width, img_height)  # Масштабирование по самой большой стороне
    new_width = int(img_width * scale)
    new_height = int(img_height * scale)

    # Масштабируем изображение
    img_resized = img_pil.resize((new_width, new_height), Image.LANCZOS)

    # Создаём квадратное изображение с отступами
    square_img = Image.new("RGB", (face_size, face_size), (255, 255, 255))
    x_offset = (face_size - new_width) // 2
    y_offset = (face_size - new_height) // 2
    square_img.paste(img_resized, (x_offset, y_offset))

    # Вставляем в коллаж
    collage.paste(square_img, (col * face_size, row * face_size))

    # Подписываем имя
    text_position = (col * face_size + 5, row * face_size + face_size - 15)
    draw.text(text_position, name, font=font, fill=(0, 0, 0))

# 5. Сохраняем коллаж
collage_path = os.path.join(dataset_path, "classroom_collage.jpg")
collage.save(collage_path)

print(f"✅ Коллаж сохранён: {collage_path}")
