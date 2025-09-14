import os
import json
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageReactionHandler, ContextTypes
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен бота из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')

def log_user_action(user_id: int, action: str, details: str = ""):
    """Логирует действия пользователя в файл"""
    try:
        # Создаем папку users если её нет
        users_dir = 'users'
        if not os.path.exists(users_dir):
            os.makedirs(users_dir)
        
        # Создаем папку для конкретного пользователя
        user_dir = os.path.join(users_dir, str(user_id))
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
        
        # Путь к файлу лога
        log_file = os.path.join(user_dir, 'actions.log')
        
        # Формируем запись лога
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {action}"
        if details:
            log_entry += f" - {details}"
        log_entry += "\n"
        
        # Записываем в файл
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
            
    except Exception as e:
        logger.error(f"Ошибка при логировании действия пользователя {user_id}: {e}")

async def handle_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает реакции пользователей на сообщения"""
    try:
        user = update.effective_user
        message_reaction = update.message_reaction
        
        if not user or not message_reaction:
            return
        
        # Получаем информацию о реакции
        reactions = message_reaction.new_reaction
        old_reactions = message_reaction.old_reaction
        
        # Логируем новые реакции
        if reactions:
            for reaction in reactions:
                emoji = reaction.emoji if hasattr(reaction, 'emoji') else str(reaction)
                log_user_action(
                    user.id, 
                    "Добавлена реакция", 
                    f"Эмодзи: {emoji}, Сообщение ID: {message_reaction.message_id}"
                )
        
        # Логируем удаленные реакции
        if old_reactions:
            for reaction in old_reactions:
                emoji = reaction.emoji if hasattr(reaction, 'emoji') else str(reaction)
                log_user_action(
                    user.id, 
                    "Удалена реакция", 
                    f"Эмодзи: {emoji}, Сообщение ID: {message_reaction.message_id}"
                )
                
    except Exception as e:
        logger.error(f"Ошибка при обработке реакции: {e}")

def get_locations_from_data():
    """Получает список локаций из папки data в алфавитном порядке"""
    try:
        data_path = 'data'
        if not os.path.exists(data_path):
            logger.error("Папка data не найдена!")
            return []
        
        # Получаем все папки в data и сортируем их
        locations = []
        for item in os.listdir(data_path):
            item_path = os.path.join(data_path, item)
            if os.path.isdir(item_path):
                locations.append(item)
        
        return sorted(locations)  # Сортируем в алфавитном порядке
    except Exception as e:
        logger.error(f"Ошибка при получении локаций из папки data: {e}")
        return []

def get_location_text(location_name):
    """Получает текст из первого .txt файла в папке локации"""
    try:
        location_path = os.path.join('data', location_name)
        if not os.path.exists(location_path):
            logger.error(f"Папка {location_path} не найдена!")
            return None
        
        # Ищем первый .txt файл в папке
        for file in os.listdir(location_path):
            if file.endswith('.txt'):
                file_path = os.path.join(location_path, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
        
        logger.error(f"Текстовый файл не найден в папке {location_path}")
        return None
    except Exception as e:
        logger.error(f"Ошибка при чтении файла локации: {e}")
        return None

def get_location_images(location_name):
    """Получает список всех изображений из папки локации"""
    try:
        location_path = os.path.join('data', location_name)
        if not os.path.exists(location_path):
            logger.error(f"Папка {location_path} не найдена!")
            return []
        
        # Поддерживаемые форматы изображений
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        images = []
        
        for file in os.listdir(location_path):
            file_lower = file.lower()
            if any(file_lower.endswith(ext) for ext in image_extensions):
                file_path = os.path.join(location_path, file)
                images.append(file_path)
        
        return sorted(images)  # Сортируем для предсказуемого порядка
    except Exception as e:
        logger.error(f"Ошибка при получении изображений локации: {e}")
        return []

def get_location_audio(location_name):
    """Получает первый найденный аудиофайл из папки локации"""
    try:
        location_path = os.path.join('data', location_name)
        if not os.path.exists(location_path):
            logger.error(f"Папка {location_path} не найдена!")
            return None
        
        # Поддерживаемые форматы аудио
        audio_extensions = ['.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac']
        
        for file in os.listdir(location_path):
            file_lower = file.lower()
            if any(file_lower.endswith(ext) for ext in audio_extensions):
                file_path = os.path.join(location_path, file)
                return file_path
        
        return None  # Аудиофайл не найден
    except Exception as e:
        logger.error(f"Ошибка при получении аудиофайла локации: {e}")
        return None



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение при команде /start"""
    user = update.effective_user
    
    # Логируем действие
    log_user_action(user.id, "Команда /start", f"Пользователь: {user.first_name} (@{user.username})")
    
    # Создаем кнопку
    keyboard = [[InlineKeyboardButton("Начнём! 🚀", callback_data='start_excursion')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_html(
        f"Привет, {user.mention_html()}! 👋\n\n"
        f"Добро пожаловать в наш туристический бот! 🗺️\n"
        f"Я готов помочь тебе с путешествиями и туризмом.\n\n"
        f"Нажми кнопку ниже, чтобы начать экскурсию!",
        reply_markup=reply_markup,
        disable_notification=True
    )

async def show_location(update: Update, context: ContextTypes.DEFAULT_TYPE, location_name: str) -> None:
    """Показывает информацию о локации с кнопками навигации"""
    # Получаем текст локации
    location_text = get_location_text(location_name)
    if not location_text:
        await update.callback_query.edit_message_text("❌ Ошибка при загрузке информации о локации!")
        return
    
    # Получаем список всех локаций
    all_locations = get_locations_from_data()
    if not all_locations:
        await update.callback_query.edit_message_text("❌ Локации не найдены!")
        return
    
    
    # Находим текущую позицию в списке локаций
    current_index = all_locations.index(location_name) if location_name in all_locations else -1
    
    # Создаем кнопки для навигации
    keyboard = []
    
    # Кнопка "Следующая локация" если есть следующая
    if current_index < len(all_locations) - 1:
        next_location = all_locations[current_index + 1]
        keyboard.append([InlineKeyboardButton(f"➡️ Следующая: {next_location}", callback_data=f'location_{next_location}')])
    
    # Добавляем кнопку "Начать заново" если это последняя локация
    if current_index == len(all_locations) - 1:
        keyboard.append([InlineKeyboardButton("🔄 Начать заново", callback_data='start_excursion')])
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    # Получаем изображения и аудио локации
    images = get_location_images(location_name)
    audio_file = get_location_audio(location_name)
    
    # Отправляем информацию о локации
    message = f"🎯 **{location_name}**\n\n{location_text}"
    
    try:
        # Отправляем изображения если есть
        if images:
            # Создаем медиа-группу из всех изображений
            media_group = []
            for image_path in images:
                with open(image_path, 'rb') as photo:
                    media_group.append(InputMediaPhoto(media=photo))
            
            # Отправляем все изображения группой
            await context.bot.send_media_group(
                chat_id=update.effective_chat.id,
                media=media_group,
                disable_notification=True
            )
        
        # Отправляем текстовое сообщение с кнопками
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            parse_mode='Markdown',
            reply_markup=reply_markup,
            disable_notification=True
        )
        
        # Отправляем аудиофайл если есть
        if audio_file:
            with open(audio_file, 'rb') as audio:
                await context.bot.send_audio(
                    chat_id=update.effective_chat.id,
                    audio=audio,
                    disable_notification=True
                )
                
    except Exception as e:
        logger.error(f"Ошибка при отправке медиа: {e}")
        # Если ошибка с медиа, отправляем только текст
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            parse_mode='Markdown',
            reply_markup=reply_markup,
            disable_notification=True
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатие кнопки"""
    query = update.callback_query
    user = update.effective_user
    await query.answer()
    
    # Логируем нажатие кнопки
    log_user_action(user.id, "Нажата кнопка", f"Кнопка: {query.data}")
    
    if query.data == 'start_excursion':
        # Получаем список всех локаций
        all_locations = get_locations_from_data()
        if not all_locations:
            await query.edit_message_text("❌ Локации не найдены!")
            return
        
        # Получаем первую локацию (стартовую)
        start_location = all_locations[0]
        
        # Показываем стартовую локацию (show_location сама удалит предыдущие сообщения)
        await show_location(update, context, start_location)
    
    elif query.data.startswith('location_'):
        # Извлекаем название локации из callback_data
        location_name = query.data.replace('location_', '')
        
        # Показываем новую локацию
        await show_location(update, context, location_name)
    

async def show_all_locations(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает все доступные локации с кнопками для быстрого перехода"""
    user = update.effective_user
    
    # Логируем действие
    log_user_action(user.id, "Команда /show_all_locations")
    
    # Получаем список всех локаций из папки data
    all_locations = get_locations_from_data()
    if not all_locations:
        await update.message.reply_text("❌ Локации не найдены!")
        return
    
    # Создаем кнопки для всех локаций
    keyboard = []
    for location in all_locations:
        keyboard.append([InlineKeyboardButton(f"📍 {location}", callback_data=f'location_{location}')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = "🗺️ **Выбери локацию для быстрого перехода:**\n\n"
    for i, location in enumerate(all_locations, 1):
        message_text += f"{i}. {location}\n"
    
    await update.message.reply_text(
        message_text,
        parse_mode='Markdown',
        reply_markup=reply_markup,
        disable_notification=True
    )

async def map_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет карту маршрута пользователю"""
    user = update.effective_user
    
    # Логируем действие
    log_user_action(user.id, "Команда /map")
    
    try:
        # Проверяем существование файла карты
        map_path = 'map.jpg'
        if not os.path.exists(map_path):
            await update.message.reply_text("❌ Карта маршрута не найдена!", disable_notification=True)
            return
        
        # Отправляем карту
        with open(map_path, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption="🗺️ **Карта маршрута**\n\nВот общая карта всех локаций экскурсии!",
                parse_mode='Markdown',
                disable_notification=True
            )
    except Exception as e:
        logger.error(f"Ошибка при отправке карты: {e}")
        await update.message.reply_text("❌ Ошибка при загрузке карты!", disable_notification=True)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет справку по командам"""
    user = update.effective_user
    
    # Логируем действие
    log_user_action(user.id, "Команда /help")
    
    help_text = """
🤖 Доступные команды:

/start - Начать работу с ботом
/show_all_locations - Показать все локации для быстрого перехода
/map - Показать карту маршрута
/help - Показать эту справку
    """
    await update.message.reply_text(help_text, disable_notification=True)

async def post_init(application: Application) -> None:
    """Функция для настройки бота после инициализации"""
    # Настраиваем меню команд
    commands = [
        ("start", "Начать работу с ботом"),
        ("show_all_locations", "Показать все локации"),
        ("map", "Показать карту маршрута"),
        ("help", "Показать справку")
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Меню команд настроено")

def main() -> None:
    """Запускает бота"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не найден! Проверь файл .env")
        return
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("show_all_locations", show_all_locations))
    application.add_handler(CommandHandler("map", map_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Добавляем обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Добавляем обработчик реакций
    application.add_handler(MessageReactionHandler(handle_reaction))
    
    # Запускаем бота
    logger.info("Бот запускается...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
