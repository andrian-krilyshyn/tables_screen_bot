import fitz  # PyMuPDF
import io
from googleapiclient.discovery import build
from google.oauth2 import service_account
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, ContextTypes, CallbackQueryHandler
from datetime import datetime
import sqlite3
from Chat import Chat
import os


ADMIN_CHAT_ID = -1002432818486
# Ваш токен бота та ID чату
TOKEN = '7437436266:AAGkrZ0Hjijun2loep5t22tf-5kdomLqdRE'
CHAT_OBJECTS = []
# Налаштування для Google Sheets
SERVICE_ACCOUNT_FILE = 's.json'
SCOPES = ['https://www.googleapis.com/auth/drive']

# Налаштування Google Drive API
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('drive', 'v3', credentials=credentials)


# Функція ініціалізації списку об'єктів chat з бази даних
def initialize_chats_from_db(db_name):
    # Підключення до бази даних
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Запит для отримання даних з таблиці properties
    select_query = "SELECT tableName, sheetId, chatId FROM properties"
    cursor.execute(select_query)

    # Ініціалізація списку об'єктів chat
    chat_list = []
    rows = cursor.fetchall()
    for row in rows:
        table_name, sheet_id, chat_id = row
        chat_obj = Chat(sheet_id, chat_id, table_name)
        chat_list.append(chat_obj)

    # Закриття з'єднання з базою даних
    conn.close()
    return chat_list


def setUpDatabase():
    global CHAT_OBJECTS
    # Виклик функції для створення об'єктів з бази даних
    database_name = 'properties.db'  # Замість цього використайте вашу назву бази
    CHAT_OBJECTS = initialize_chats_from_db(database_name)

    # Перевірка результату
    print(f"Ініціалізовано {len(CHAT_OBJECTS)} об'єктів.")


# Завантаження PDF з Google Sheets
def fetch_pdf(sheet_id, output_path):
    request = service.files().export_media(fileId=sheet_id, mimeType='application/pdf')
    fh = io.BytesIO(request.execute())
    with open(output_path, 'wb') as f:
        f.write(fh.getvalue())
    print(f"PDF завантажено: {output_path}")


# Збереження лише першої сторінки PDF
def save_first_page(input_pdf_path, output_pdf_path):
    doc = fitz.open(input_pdf_path)  # Відкриваємо PDF
    new_doc = fitz.open()  # Створюємо новий PDF документ
    new_doc.insert_pdf(doc, from_page=0, to_page=0)  # Копіюємо лише першу сторінку
    new_doc.save(output_pdf_path)  # Зберігаємо новий PDF з першою сторінкою
    new_doc.close()
    doc.close()
    print(f"Збережено першу сторінку: {output_pdf_path}")

def process_chats():
    # Створення папки для збереження PDF, якщо вона не існує
    os.makedirs('pdf', exist_ok=True)

    # Ітерація по кожному об'єкту в CHAT_OBJECTS
    for chat in CHAT_OBJECTS:
        pdf_name = f"{chat.tableName}.pdf"
        temp_pdf_path = f"temp/temp_{pdf_name}"  # Тимчасовий файл для повного PDF
        output_pdf_path = f"pdf/{pdf_name}"  # Остаточний файл з першою сторінкою

        try:
            # Завантаження PDF файлу з Google Sheets
            fetch_pdf(chat.sheetId, temp_pdf_path)

            # Збереження першої сторінки PDF у папку pdf
            save_first_page(temp_pdf_path, output_pdf_path)

            # Видалення тимчасового файлу
            os.remove(temp_pdf_path)
        except Exception as e:
            print(f"Помилка при обробці {chat.tableName}: {e}")

def process_single_chat(chat):
     # Створення папки для збереження PDF, якщо вона не існує
    os.makedirs('pdf', exist_ok=True)

    pdf_name = f"{chat.tableName}.pdf"
    temp_pdf_path = f"temp/temp_{pdf_name}"  # Тимчасовий файл для повного PDF
    output_pdf_path = f"pdf/{pdf_name}"  # Остаточний файл з першою сторінкою

    try:
            # Завантаження PDF файлу з Google Sheets
            fetch_pdf(chat.sheetId, temp_pdf_path)

            # Збереження першої сторінки PDF у папку pdf
            save_first_page(temp_pdf_path, output_pdf_path)

            # Видалення тимчасового файлу
            os.remove(temp_pdf_path)
    except Exception as e:
            print(f"Помилка при обробці {chat.tableName}: {e}")

# Надсилання PDF у чат
async def send_pdf(pdf_path, chatID, table_name):
    bot = Bot(token=TOKEN)
    with open(pdf_path, 'rb') as pdf_file:
        sent_message = await bot.send_document(chat_id=chatID, document=pdf_file)
    # Час надсилання
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Надсилаємо текстове повідомлення як відповідь на надісланий PDF
    if sent_message:
        await bot.send_message(chat_id=chatID, text=f"Документ '{table_name}' был послан в {current_time}.", reply_to_message_id=sent_message.message_id)
    else:
        await bot.send_message(chat_id=chatID, text=f"Документ '{table_name}' был послан в {current_time}.")


async def send_pdfs_to_all_chats():
    for chat in CHAT_OBJECTS:
        # Шлях до PDF-файлу для поточного чату
        pdf_path = f"pdf/{chat.tableName}.pdf" 
        
        # Спроба надіслати файл і обробити помилки
        try:
            await send_pdf(pdf_path, chat.chatId, chat.tableName)
            print(f"Файл {chat.tableName}.pdf надіслано в чат {chat.chatId}.")
        except Exception as e:
            print(f"Помилка при надсиланні {chat.tableName}.pdf у чат {chat.chatId}: {e}")

        try:
            await send_pdf(pdf_path, ADMIN_CHAT_ID, chat.tableName)
            print(f"Файл {chat.tableName}.pdf надіслано в чат ADMIN: {ADMIN_CHAT_ID}.")
        except Exception as e:
            print(f"Помилка при надсиланні {chat.tableName}.pdf у чат {ADMIN_CHAT_ID}: {e}")


async def send_pdfs_to_admin_chat():
    for chat in CHAT_OBJECTS:
        # Шлях до PDF-файлу для поточного чату
        pdf_path = f"pdf/{chat.tableName}.pdf" 
        
        # Спроба надіслати файл і обробити помилки
        try:
            await send_pdf(pdf_path, ADMIN_CHAT_ID, chat.tableName)
            print(f"Файл {chat.tableName}.pdf надіслано в чат {ADMIN_CHAT_ID}.")
        except Exception as e:
            print(f"Помилка при надсиланні {chat.tableName}.pdf у чат {ADMIN_CHAT_ID}: {e}")




# Основна робота: завантаження та надсилання PDF
async def job():
    setUpDatabase()
    process_chats()
    await  send_pdfs_to_all_chats()
    
async def button_job(chatId):
    found_chat = None
    for chat in CHAT_OBJECTS:
        if chat.chatId == str(chatId):
            found_chat = chat
            break

        
    if found_chat:
        process_single_chat(found_chat)
        pdf_path = f"pdf/{found_chat.tableName}.pdf"
        await send_pdf(pdf_path, found_chat.chatId, found_chat.tableName)

    if chatId == ADMIN_CHAT_ID:
        process_chats()
        await send_pdfs_to_admin_chat()

# Відповідь на команду /start
async def start(update: Update, context: CallbackContext):
    keyboard = [[InlineKeyboardButton("Выполнить действия", callback_data='run_job')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Нажмите кнопку для выполнения действий.', reply_markup=reply_markup)

# Обробка натискання кнопки
async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.message.chat.id
    await query.answer()
    if query.data == 'run_job':
        await button_job(chat_id)

# Основна функція для запуску бота
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    setUpDatabase()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button))

    # Запуск асинхронного циклу планувальника
    scheduler = AsyncIOScheduler()
    scheduler.add_job(job, 'interval', minutes=30)  # Запуск кожні 30 хвилин
    scheduler.start()

    app.run_polling()

if __name__ == '__main__':
    main()