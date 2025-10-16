import os
import django
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.types import WebAppInfo
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async
import re

# Настройка Django окружения
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from users.models import TelegramUser

TELEGRAM_BOT_TOKEN = '8429850519:AAHSSPY3TAhuyTJQEc0cqFQAelXPrD2qKAs'
FRONTEND_BASE_URL = os.getenv('FRONTEND_URL', 'https://demisable-agueda-cloque.ngrok-free.dev')

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

fields = [
    ('first_name', 'Введите ваше имя:'),
    ('last_name', 'Введите вашу фамилию:'),
    ('username', 'Введите ваш никнейм (Telegram username):'),
    ('email', 'Введите вашу почту:'),
    ('workplace', 'Введите место работы:'),
    ('position', 'Введите вашу должность:'),
    ('data_processing_agreement', 'Продолжая вы соглашаетесь на обработку данных'),
]
user_state = {}

@sync_to_async
def get_or_create_user(tg_id, data):
    return TelegramUser.objects.get_or_create(
        telegram_id=tg_id,
        defaults={
            'first_name': data.get('first_name'),
            'last_name': data.get('last_name'),
            'username': data.get('username'),
            'email': data.get('email'),
            'workplace': data.get('workplace'),
            'position': data.get('position'),
            'data_processing_agreement': data.get('data_processing_agreement'),
        }
    )

@sync_to_async
def update_user(user, data):
    for k, v in data.items():
        setattr(user, k, v)
    user.save()

@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    user_state[message.from_user.id] = {'step': 0, 'data': {}}
    await message.answer("Здравствуйте! Для входа в приложение заполните несколько полей.")
    await message.answer(fields[0][1])

@dp.message()
async def collect_data(message: types.Message):
    user_id = message.from_user.id
    state = user_state.get(user_id)
    if not state:
        # Игнорируем нажатие кнопки "Открыть приложение" здесь — есть отдельный хендлер
        if message.text and message.text.strip() == 'Открыть приложение':
            return
        # Не шлём повторно подсказки, чтобы не спамить после завершения регистрации
        return

    step = state['step']
    data = state['data']
    field, prompt = fields[step]
    value = message.text.strip()

    # FIRST_NAME validation
    if field == 'first_name':
        if not (len(value) >= 2 and value.isalpha()):
            await message.answer("Имя должно содержать минимум 2 буквы и только буквы. Попробуйте ещё раз:")
            return
        data[field] = value
        step += 1
        state['step'] = step
        await message.answer(fields[step][1], reply_markup=ReplyKeyboardRemove())
        return

    # LAST_NAME validation
    if field == 'last_name':
        if not (len(value) >= 2 and value.isalpha()):
            await message.answer("Фамилия должна содержать минимум 2 буквы и только буквы. Попробуйте ещё раз:")
            return
        data[field] = value
        step += 1
        state['step'] = step
        # Для username нужна спец. обработка ниже

    # ВЫБОР username кнопкой
    if field == 'username':
        telegram_username = message.from_user.username
        USERNAME_PATTERN = r'^[A-Za-z0-9_]{3,}$'
        if not telegram_username:
            data[field] = None
            step += 1
            state['step'] = step
            await message.answer(fields[step][1], reply_markup=ReplyKeyboardRemove())
            return
        if value == telegram_username:
            # username — валидация
            if not re.fullmatch(USERNAME_PATTERN, value):
                await message.answer("Никнейм может содержать только латинские буквы, цифры, подчёркивания и должен быть не менее 3 символов. Попробуйте ещё раз.", reply_markup=ReplyKeyboardRemove())
                return
            data[field] = value
            step += 1
            state['step'] = step
            await message.answer(fields[step][1], reply_markup=ReplyKeyboardRemove())
            return
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=telegram_username)]],
            resize_keyboard=True
        )
        await message.answer(
            'Нажмите кнопку с вашим никнеймом для подтверждения:',
            reply_markup=keyboard
        )
        return

    # EMAIL validation
    if field == 'email':
        EMAIL_PATTERN = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
        if not re.fullmatch(EMAIL_PATTERN, value):
            await message.answer("Пожалуйста, введите корректный email, например user@email.com")
            return
        data[field] = value
        step += 1
        state['step'] = step
        await message.answer(fields[step][1], reply_markup=ReplyKeyboardRemove())
        return

    # WORKPLACE validation
    if field == 'workplace':
        if len(value) < 2:
            await message.answer("Место работы должно быть не короче 2 символов. Попробуйте снова:")
            return
        data[field] = value
        step += 1
        state['step'] = step
        await message.answer(fields[step][1], reply_markup=ReplyKeyboardRemove())
        return

    # POSITION validation
    if field == 'position':
        if len(value) < 2:
            await message.answer("Должность должна быть не короче 2 символов. Попробуйте снова:")
            return
        data[field] = value
        step += 1
        state['step'] = step
        # Следующий шаг обработает data_processing_agreement

    # СОГЛАСИЕ
    if field == 'data_processing_agreement':
        if value == 'Продолжить':
            data[field] = True
            step += 1
            state['step'] = step
            if step < len(fields):
                await message.answer(fields[step][1], reply_markup=ReplyKeyboardRemove())
            else:
                tg_id = user_id
                user, created = await get_or_create_user(tg_id, data)
                if not created:
                    await update_user(user, data)
                user_state.pop(user_id, None)
                ikb = InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text='Открыть приложение', web_app=WebAppInfo(url=FRONTEND_BASE_URL))]]
                )
                await message.answer('Спасибо, регистрация завершена!', reply_markup=ReplyKeyboardRemove())
                await message.answer('Нажмите кнопку ниже, чтобы открыть приложение:', reply_markup=ikb)
            return
        else:
            keyboard = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text='Продолжить')]],
                resize_keyboard=True
            )
            await message.answer(
                'Продолжая вы соглашаетесь на обработку данных',
                reply_markup=keyboard
            )
            return

    # Следующий шаг для "средних" (без спец. клавиатуры)
    if step < len(fields):
        state['step'] = step
        next_field, next_prompt = fields[step]
        if next_field == 'username':
            telegram_username = message.from_user.username
            if telegram_username:
                keyboard = ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text=telegram_username)]],
                    resize_keyboard=True
                )
                await message.answer(
                    'Нажмите кнопку с вашим никнеймом для подтверждения:',
                    reply_markup=keyboard
                )
                return
        elif next_field == 'data_processing_agreement':
            keyboard = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text='Продолжить')]],
                resize_keyboard=True
            )
            await message.answer(
                'Продолжая вы соглашаетесь на обработку данных',
                reply_markup=keyboard
            )
            return
        else:
            await message.answer(next_prompt, reply_markup=ReplyKeyboardRemove())
    else:
        tg_id = user_id
        user, created = await get_or_create_user(tg_id, data)
        if not created:
            await update_user(user, data)
        user_state.pop(user_id, None)
        ikb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text='Открыть приложение', web_app=WebAppInfo(url=FRONTEND_BASE_URL))]]
        )
        await message.answer('Спасибо, регистрация завершена!', reply_markup=ReplyKeyboardRemove())
        await message.answer('Нажмите кнопку ниже, чтобы открыть приложение:', reply_markup=ikb)

@dp.message(F.text == 'Открыть приложение')
async def open_app(message: types.Message):
    # Если пользователь уже есть — выдадим WebApp кнопку
    tg_id = message.from_user.id
    user = await sync_to_async(TelegramUser.objects.filter(telegram_id=tg_id).first)()
    if user:
        ikb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text='Открыть приложение', web_app=WebAppInfo(url=FRONTEND_BASE_URL))]]
        )
        await message.answer('Нажмите кнопку ниже, чтобы открыть приложение:', reply_markup=ikb)
        return
    # Если почему-то нет пользователя
    await message.answer("Начните с команды /start")

if __name__ == '__main__':
    asyncio.run(dp.start_polling(bot))
