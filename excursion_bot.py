import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
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

def load_route_data():
    """Загружает данные маршрута из route.json"""
    try:
        with open('route.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("Файл route.json не найден!")
        return None
    except json.JSONDecodeError:
        logger.error("Ошибка при чтении route.json!")
        return None

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

def get_navigation_stack(context: ContextTypes.DEFAULT_TYPE):
    """Получает стек навигации из контекста"""
    if 'navigation_stack' not in context.user_data:
        context.user_data['navigation_stack'] = []
    return context.user_data['navigation_stack']

def push_to_navigation_stack(context: ContextTypes.DEFAULT_TYPE, location_name: str):
    """Добавляет локацию в стек навигации"""
    stack = get_navigation_stack(context)
    if not stack or stack[-1] != location_name:  # Не добавляем дубликаты
        stack.append(location_name)

def pop_from_navigation_stack(context: ContextTypes.DEFAULT_TYPE):
    """Удаляет последнюю локацию из стека и возвращает предыдущую"""
    stack = get_navigation_stack(context)
    if len(stack) > 1:
        stack.pop()  # Удаляем текущую локацию
        return stack[-1] if stack else None
    return None

def get_message_history(context: ContextTypes.DEFAULT_TYPE):
    """Получает историю сообщений из контекста"""
    if 'message_history' not in context.user_data:
        context.user_data['message_history'] = []
    return context.user_data['message_history']

def add_to_message_history(context: ContextTypes.DEFAULT_TYPE, message_id: int):
    """Добавляет ID сообщения в историю"""
    history = get_message_history(context)
    history.append(message_id)

def clear_message_history(context: ContextTypes.DEFAULT_TYPE):
    """Очищает историю сообщений"""
    context.user_data['message_history'] = []

async def delete_previous_messages(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Удаляет все предыдущие сообщения из истории"""
    history = get_message_history(context)
    for message_id in history:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение {message_id}: {e}")
    clear_message_history(context)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение при команде /start"""
    user = update.effective_user
    
    # Очищаем историю сообщений при команде /start
    clear_message_history(context)
    
    # Создаем кнопку
    keyboard = [[InlineKeyboardButton("Начнём! 🚀", callback_data='start_excursion')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    start_message = await update.message.reply_html(
        f"Привет, {user.mention_html()}! 👋\n\n"
        f"Добро пожаловать в наш туристический бот! 🗺️\n"
        f"Я готов помочь тебе с путешествиями и туризмом.\n\n"
        f"Нажми кнопку ниже, чтобы начать экскурсию!",
        reply_markup=reply_markup,
        disable_notification=True
    )
    
    # Добавляем ID приветственного сообщения в историю
    add_to_message_history(context, start_message.message_id)

async def show_location(update: Update, context: ContextTypes.DEFAULT_TYPE, location_name: str, is_back_navigation: bool = False) -> None:
    """Показывает информацию о локации с кнопками навигации"""
    # Получаем текст локации
    location_text = get_location_text(location_name)
    if not location_text:
        await update.callback_query.edit_message_text("❌ Ошибка при загрузке информации о локации!")
        return
    
    # Загружаем данные маршрута для получения доступных локаций
    route_data = load_route_data()
    if not route_data:
        await update.callback_query.edit_message_text("❌ Ошибка при загрузке маршрута!")
        return
    
    # Обновляем стек навигации
    if not is_back_navigation:
        push_to_navigation_stack(context, location_name)
    
    # Получаем доступные локации для текущей локации
    available_locations = route_data.get(location_name, [])
    
    # Создаем кнопки для навигации
    keyboard = []
    if available_locations:
        for loc in available_locations:
            keyboard.append([InlineKeyboardButton(f"📍 {loc}", callback_data=f'location_{loc}')])
    
    # Добавляем кнопку "Назад" если есть предыдущая локация в стеке
    stack = get_navigation_stack(context)
    if len(stack) > 1:
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='back_navigation')])
    
    # Добавляем кнопку "Начать заново" если это конечная локация
    end_location = route_data.get('end')
    if location_name == end_location:
        keyboard.append([InlineKeyboardButton("🔄 Начать заново", callback_data='start_excursion')])
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    # Получаем изображения и аудио локации
    images = get_location_images(location_name)
    audio_file = get_location_audio(location_name)
    
    # Отправляем информацию о локации
    message = f"🎯 **{location_name}**\n\n{location_text}"
    
    # Сохраняем старую историю сообщений для удаления
    old_message_history = get_message_history(context).copy()
    
    # Очищаем историю для новых сообщений
    clear_message_history(context)
    
    try:
        # Отправляем изображения если есть
        if images:
            # Создаем медиа-группу из всех изображений
            media_group = []
            for image_path in images:
                with open(image_path, 'rb') as photo:
                    media_group.append(InputMediaPhoto(media=photo))
            
            # Отправляем все изображения группой
            sent_messages = await context.bot.send_media_group(
                chat_id=update.effective_chat.id,
                media=media_group,
                disable_notification=True
            )
            
            # Добавляем ID всех отправленных изображений в историю
            for sent_message in sent_messages:
                add_to_message_history(context, sent_message.message_id)
        
        # Отправляем текстовое сообщение с кнопками
        text_message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            parse_mode='Markdown',
            reply_markup=reply_markup,
            disable_notification=True
        )
        
        # Добавляем ID текстового сообщения в историю
        add_to_message_history(context, text_message.message_id)
        
        # Отправляем аудиофайл если есть
        if audio_file:
            with open(audio_file, 'rb') as audio:
                audio_message = await context.bot.send_audio(
                    chat_id=update.effective_chat.id,
                    audio=audio,
                    disable_notification=True
                )
                add_to_message_history(context, audio_message.message_id)
        
        # Удаляем только старые сообщения
        for message_id in old_message_history:
            try:
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message_id)
            except Exception as e:
                logger.warning(f"Не удалось удалить старое сообщение {message_id}: {e}")
                
    except Exception as e:
        logger.error(f"Ошибка при отправке медиа: {e}")
        # Если ошибка с медиа, отправляем только текст
        text_message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            parse_mode='Markdown',
            reply_markup=reply_markup,
            disable_notification=True
        )
        add_to_message_history(context, text_message.message_id)
        
        # Удаляем только старые сообщения даже при ошибке
        for message_id in old_message_history:
            try:
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message_id)
            except Exception as e:
                logger.warning(f"Не удалось удалить старое сообщение {message_id}: {e}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатие кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'start_excursion':
        # Очищаем стек навигации при начале новой экскурсии
        context.user_data['navigation_stack'] = []
        
        # Загружаем данные маршрута
        route_data = load_route_data()
        if not route_data:
            await query.edit_message_text("❌ Ошибка при загрузке маршрута!")
            return
        
        # Получаем стартовую локацию
        start_location = route_data.get('start')
        if not start_location:
            await query.edit_message_text("❌ Стартовая локация не найдена!")
            return
        
        # Показываем стартовую локацию (show_location сама удалит предыдущие сообщения)
        await show_location(update, context, start_location)
    
    elif query.data.startswith('location_'):
        # Извлекаем название локации из callback_data
        location_name = query.data.replace('location_', '')
        
        # Показываем новую локацию
        await show_location(update, context, location_name)
    
    elif query.data == 'back_navigation':
        # Возвращаемся к предыдущей локации
        previous_location = pop_from_navigation_stack(context)
        if previous_location:
            await show_location(update, context, previous_location, is_back_navigation=True)
        else:
            await query.edit_message_text("❌ Нет предыдущей локации!")

async def show_all_locations(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает все доступные локации с кнопками для быстрого перехода"""
    # Загружаем данные маршрута
    route_data = load_route_data()
    if not route_data:
        await update.message.reply_text("❌ Ошибка при загрузке маршрута!")
        return
    
    # Получаем все локации (исключаем 'start' и 'end', но включаем их значения)
    all_locations = []
    for key in route_data.keys():
        if key not in ['start', 'end']:
            all_locations.append(key)
    
    # Добавляем стартовую и конечную локации по их значениям
    start_location = route_data.get('start')
    end_location = route_data.get('end')
    
    if start_location and start_location not in all_locations:
        all_locations.append(start_location)
    if end_location and end_location not in all_locations:
        all_locations.append(end_location)
    
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
    
    # Очищаем историю сообщений
    clear_message_history(context)
    
    location_message = await update.message.reply_text(
        message_text,
        parse_mode='Markdown',
        reply_markup=reply_markup,
        disable_notification=True
    )
    
    # Добавляем ID сообщения в историю
    add_to_message_history(context, location_message.message_id)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет справку по командам"""
    help_text = """
🤖 Доступные команды:

/start - Начать работу с ботом
/show_all_locations - Показать все локации для быстрого перехода
/help - Показать эту справку

Нажми кнопку "Начнём!" чтобы начать экскурсию! 🚀
    """
    await update.message.reply_text(help_text, disable_notification=True)

async def post_init(application: Application) -> None:
    """Функция для настройки бота после инициализации"""
    # Настраиваем меню команд
    commands = [
        ("start", "Начать работу с ботом"),
        ("show_all_locations", "Показать все локации"),
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
    application.add_handler(CommandHandler("help", help_command))
    
    # Добавляем обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Запускаем бота
    logger.info("Бот запускается...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
