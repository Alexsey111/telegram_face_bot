# Бот без базы данных
import os
import cv2
import asyncio
import traceback
from datetime import datetime
import pytz
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from deepface import DeepFace
import nest_asyncio

nest_asyncio.apply()

# Константы
TOKEN = "7634676284:AAF5Fbm5DN_Cx-2rj63MKWvUj80ZJnrmH_8"  
STUDENTS_DIR = "/content/dataset"  # Папка с фото студентов
ATTENDANCE_FILE = "attendance.txt"  # Файл для отчета

# Классификатор OpenCV для поиска лиц
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

# Словарь для хранения часовых поясов пользователей
user_timezones = {}

# Создаем клавиатуру
keyboard = [["/start", "/help"]]
reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_local_timestamp(timezone):
    """
    Возвращает временную метку в указанном часовом поясе.
    :param timezone: Объект часового пояса из pytz.
    :return: Отформатированная строка с временной меткой.
    """
    local_time = datetime.now(timezone)
    return local_time.strftime("%Y-%m-%d %H:%M:%S")

def get_expected_students(directory):
    """
    Генерирует список ожидаемых студентов на основе названий файлов в директории.
    Возвращает множество имен студентов без расширений.
    """
    expected_students = set()
    for filename in os.listdir(directory):
        if filename.lower().endswith((".png", ".jpg", ".jpeg")):
            name, _ = os.path.splitext(filename)
            expected_students.add(name)
    return expected_students

def format_student_list(students):
    """
    Форматирует список студентов:
    - Если имена содержат числовые префиксы, сортирует их по числам и убирает префиксы.
    - Если числовых префиксов нет, сортирует по алфавиту.
    Возвращает отформатированный список строк.
    """
    has_numbers = all(student.split("_")[0].isdigit() for student in students if "_" in student)

    if has_numbers:
        sorted_students = sorted(students, key=lambda x: int(x.split("_")[0]))
        formatted_students = [student.split("_", 1)[1] if "_" in student else student for student in sorted_students]
    else:
        formatted_students = sorted(students)

    return [f"{i + 1}. {name}" for i, name in enumerate(formatted_students)]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветственное сообщение"""
    await update.message.reply_text(
        "Привет! Отправь мне фото аудитории, и я отмечу присутствующих.\n"
        "Установи свой часовой пояс с помощью команды /set_timezone.\n"
        "Например: /set_timezone Europe/Moscow",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Справка по использованию бота"""
    help_text = (
        "Справка:\n"
        "/start - Начать работу с ботом.\n"
        "/help - Получить эту справку.\n"
        "/set_timezone <часовой_пояс> - Установить ваш часовой пояс (например, Europe/Moscow).\n"
        "Отправьте фото аудитории, чтобы отметить присутствующих студентов."
    )
    await update.message.reply_text(help_text, reply_markup=reply_markup)

async def list_timezones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет список всех доступных часовых поясов"""
    timezones = pytz.all_timezones
    message = "Список доступных часовых поясов:\n\n" + "\n".join(timezones)

    # Разбиваем сообщение на части, так как Telegram имеет ограничение на длину сообщений
    max_length = 4096
    for i in range(0, len(message), max_length):
        await update.message.reply_text(message[i:i + max_length], reply_markup=reply_markup)

async def set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установка часового пояса пользователя"""
    user_id = update.message.from_user.id
    user_input = update.message.text.split("/set_timezone ")[-1]  # Пример: /set_timezone Europe/Moscow

    try:
        # Проверяем, существует ли такой часовой пояс
        user_timezone = pytz.timezone(user_input)
        user_timezones[user_id] = user_timezone  # Сохраняем часовой пояс пользователя
        await update.message.reply_text(f"⏰ Часовой пояс установлен: {user_input}", reply_markup=reply_markup)
    except Exception as e:
        await update.message.reply_text(
            "Ошибка: неверный часовой пояс. Пожалуйста, используйте полное название часового пояса.\n"
            "Примеры:\n"
            "/set_timezone Europe/Moscow\n"
            "/set_timezone Asia/Almaty\n"
            "/set_timezone Asia/Krasnoyarsk\n"
            "Для просмотра всех доступных часовых поясов воспользуйтесь командой /list_timezones.",
            reply_markup=reply_markup
        )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка фото с аудиторией"""
    user_id = update.message.from_user.id

    # Получаем часовой пояс пользователя или используем UTC по умолчанию
    user_timezone = user_timezones.get(user_id, pytz.utc)

    # Получаем текущее время в часовом поясе пользователя
    timestamp = get_local_timestamp(user_timezone)

    # Скачиваем фото
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    file_path = "photo.jpg"
    await file.download_to_drive(file_path)

    img = cv2.imread(file_path)
    if img is None:
        await update.message.reply_text("Ошибка загрузки изображения.", reply_markup=reply_markup)
        return

    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(img_gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    if len(faces) == 0:
        await update.message.reply_text("Лица не найдены.", reply_markup=reply_markup)
        return
    else:
        await update.message.reply_text(f"Найдено лиц: {len(faces)}", reply_markup=reply_markup)

    found_students = set()
    threshold = 0.5  # Порог схожести лиц

    for i, (x, y, w, h) in enumerate(faces):
        face_crop = img[y:y + h, x:x + w]
        if face_crop.shape[0] == 0 or face_crop.shape[1] == 0:
            continue

        face_crop_path = f"face_{i}.png"
        cv2.imwrite(face_crop_path, face_crop)

        for student in os.listdir(STUDENTS_DIR):
            student_path = os.path.join(STUDENTS_DIR, student)

            if not student.lower().endswith((".png", ".jpg", ".jpeg")):
                continue

            test_img = cv2.imread(student_path)
            if test_img is None:
                print(f"⚠️ Ошибка: изображение {student_path} не может быть загружено!")
                continue

            try:
                result = DeepFace.verify(
                    img1_path=face_crop_path,
                    img2_path=student_path,
                    model_name='VGG-Face', # 'Facenet', 'ArcFace', 'OpenFace', 'VGG-Face'
                    enforce_detection=False
                )

                distance = result.get("distance", float('inf'))

                if result.get("verified", False) and distance < threshold:
                    found_students.add(os.path.splitext(student)[0])
                    break
            except Exception as e:
                print(f"Ошибка сравнения {face_crop_path} -> {student_path}: {e}")

        os.remove(face_crop_path)

    # Генерируем список ожидаемых студентов
    expected_students = get_expected_students(STUDENTS_DIR)

    if not expected_students:
        await update.message.reply_text("Ошибка: в папке со студентами нет подходящих изображений!", reply_markup=reply_markup)
        return

    # Определяем отсутствующих и лишних студентов
    found_students = set(found_students)
    missing_students = sorted(expected_students - found_students)
    extra_students = sorted(found_students - expected_students)

    # Записываем отчет с временной меткой
    with open(ATTENDANCE_FILE, "w", encoding="utf-8") as f:
        f.write(f"Время проверки: {timestamp}\n\n")
        f.write(f"Распознанные студенты ({len(found_students)} из {len(expected_students)}):\n")
        formatted_found = format_student_list(found_students)
        f.write("\n".join(formatted_found) + "\n\n")

        if missing_students:
            f.write(f"Не распознанные ({len(missing_students)}):\n")
            formatted_missing = format_student_list(missing_students)
            f.write("\n".join(formatted_missing) + "\n\n")
        else:
            f.write("Все студенты распознаны!\n\n")

        if extra_students:
            f.write(f"Лишние лица ({len(extra_students)}):\n")
            formatted_extra = format_student_list(extra_students)
            f.write("\n".join(formatted_extra) + "\n\n")

        total_faces = len(faces)
        if total_faces > len(expected_students):
            f.write(f"Обнаружено {total_faces} лиц, что превышает количество студентов ({len(expected_students)}).\n")

    # Отправляем отчет пользователю
    await update.message.reply_document(document=open(ATTENDANCE_FILE, "rb"), filename=ATTENDANCE_FILE)

async def main():
    """Запуск бота"""
    application = Application.builder().token(TOKEN).build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("set_timezone", set_timezone))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(CommandHandler("list_timezones", list_timezones))

    print("Бот запущен!")
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
