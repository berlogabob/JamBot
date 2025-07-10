import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
import os

# Токен из переменной окружения
TOKEN = os.getenv("BOT_TOKEN")

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect("jams.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS requests
                 (user_id INTEGER, username TEXT, artist TEXT, song TEXT, instrument TEXT, tonality TEXT, link TEXT, city TEXT)''')
    conn.commit()
    conn.close()

init_db()

# Состояния для FSM
class AddRequest(StatesGroup):
    artist = State()
    song = State()
    instrument = State()
    tonality = State()
    link = State()
    city = State()

# Меню
def get_main_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(KeyboardButton("Добавить заявку"))
    keyboard.add(KeyboardButton("Список заявок"))
    return keyboard

# Команда /start
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.reply(
        "Привет! Это бот для музыкантов Лиссабона. Добавляй заявку на песню или смотри, кто хочет джемить!",
        reply_markup=get_main_menu()
    )

# Добавление заявки
@dp.message(lambda message: message.text == "Добавить заявку")
async def add_request_start(message: types.Message, state: FSMContext):
    await message.reply("Назови исполнителя (например, Nirvana):")
    await state.set_state(AddRequest.artist)

@dp.message(AddRequest.artist)
async def process_artist(message: types.Message, state: FSMContext):
    await state.update_data(artist=message.text)
    await message.reply("Назови песню (например, Smells Like Teen Spirit):")
    await state.set_state(AddRequest.song)

@dp.message(AddRequest.song)
async def process_song(message: types.Message, state: FSMContext):
    await state.update_data(song=message.text)
    await message.reply("Какой инструмент ты играешь? (например, Барабаны):")
    await state.set_state(AddRequest.instrument)

@dp.message(AddRequest.instrument)
async def process_instrument(message: types.Message, state: FSMContext):
    await state.update_data(instrument=message.text)
    await message.reply("Укажи тональность (например, E minor, или 'Не знаю'):")
    await state.set_state(AddRequest.tonality)

@dp.message(AddRequest.tonality)
async def process_tonality(message: types.Message, state: FSMContext):
    await state.update_data(tonality=message.text)
    await message.reply("Добавь ссылку на версию песни (или 'Нет'):")
    await state.set_state(AddRequest.link)

@dp.message(AddRequest.link)
async def process_link(message: types.Message, state: FSMContext):
    await state.update_data(link=message.text)
    await message.reply("Укажи город (например, Лиссабон):")
    await state.set_state(AddRequest.city)

@dp.message(AddRequest.city)
async def process_city(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    city = message.text

    # Сохранение заявки
    conn = sqlite3.connect("jams.db")
    c = conn.cursor()
    c.execute("INSERT INTO requests (user_id, username, artist, song, instrument, tonality, link, city) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              (user_id, username, user_data["artist"], user_data["song"], user_data["instrument"], user_data["tonality"], user_data["link"], city))
    conn.commit()

    # Проверка совпадений
    c.execute("SELECT user_id, username, instrument FROM requests WHERE artist = ? AND song = ? AND city = ? AND user_id != ?",
              (user_data["artist"], user_data["song"], city, user_id))
    matches = c.fetchall()
    conn.close()

    # Уведомления о совпадениях
    if matches:
        for match in matches:
            match_user_id, match_username, match_instrument = match
            await bot.send_message(
                match_user_id,
                f"Новое совпадение! @{username} хочет сыграть {user_data['artist']} - {user_data['song']} на {user_data['instrument']} в {city}. Напиши: @{username}"
            )
        await message.reply(f"Найдены совпадения! Уведомления отправлены {len(matches)} музыкантам.")
    else:
        await message.reply("Заявка добавлена! Жди совпадений.")

    await state.clear()
    await message.reply("Готово! Что дальше?", reply_markup=get_main_menu())

# Список заявок
@dp.message(lambda message: message.text == "Список заявок")
async def list_requests(message: types.Message):
    conn = sqlite3.connect("jams.db")
    c = conn.cursor()
    c.execute("SELECT artist, song, instrument, tonality, link, city, username FROM requests WHERE city = 'Лиссабон'")
    requests = c.fetchall()
    conn.close()

    if requests:
        response = "Заявки в Лиссабоне:\n\n"
        for req in requests:
            artist, song, instrument, tonality, link, city, username = req
            response += f"@{username}: {artist} - {song}\nИнструмент: {instrument}\nТональность: {tonality}\nСсылка: {link}\nГород: {city}\n---\n"
        await message.reply(response[:4000])  # Ограничение длины сообщения
    else:
        await message.reply("Заявок пока нет.")
    await message.reply("Что дальше?", reply_markup=get_main_menu())

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
