import os
from dotenv import load_dotenv
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
# Force .env to override any pre-set env vars to avoid drift across processes
load_dotenv(override=True)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from users.models import TelegramUser, ConsultationSlot, QuizResult

# TELEGRAM_BOT_TOKEN = '8265126857:AAEhwVCOVVDZqmuZCbqLzOmb0dLp0zJ5n5c'
# FRONTEND_BASE_URL = 'https://yandex-tma.vercel.app'

TELEGRAM_BOT_TOKEN = '7986098041:AAG7kR2rxwICzBRvP53yyUMtYonbceyW2Rg'
FRONTEND_BASE_URL = 'https://demisable-agueda-cloque.ngrok-free.dev'


# Debug: print masked token tail to ensure env consistency (remove in production)
try:
    _tt = TELEGRAM_BOT_TOKEN or ''
    print(f"[BOT] TELEGRAM_BOT_TOKEN len={len(_tt)} tail={_tt[-6:]}")
except Exception:
    pass

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


@sync_to_async
def _get_user_by_username_or_id(username=None, telegram_id=None):
    query = TelegramUser.objects
    if username:
        user = query.filter(username=username).first()
        if user:
            return user
    if telegram_id:
        return query.filter(telegram_id=telegram_id).first()
    return None


async def _ensure_registered_user(message: types.Message):
    """
    Проверяет, что пользователь есть в БД. Если нет — просит пройти регистрацию.
    Возвращает TelegramUser или None (если нужно прервать дальнейшую обработку).
    """
    user = await _get_user_by_username_or_id(
        username=message.from_user.username,
        telegram_id=message.from_user.id,
    )
    if not user:
        await message.answer(
            "Похоже, вы ещё не авторизованы. Нажмите /start и пройдите короткую регистрацию."
        )
        return None
    return user


fields = [
    ('first_name', 'Введите ваше имя:'),
    ('last_name', 'Введите вашу фамилию:'),
    ('username', 'Введите ваш никнейм (Telegram username):'),
    ('email', 'Введите вашу почту:'),
    ('workplace', 'Введите место работы:'),
    (
        'position',
        'Введите ваше направление в аналитике (дата-аналитика, продуктовая, BI или напишите свой вариант):',
    ),
]
user_state = {}

@sync_to_async
def get_or_create_user(username, data):
    return TelegramUser.objects.get_or_create(
        username=username,
        defaults={
            'telegram_id': data.get('telegram_id'),
            'first_name': data.get('first_name'),
            'last_name': data.get('last_name'),
            'email': data.get('email'),
            'workplace': data.get('workplace'),
            'position': data.get('position'),
            # Пользователь проходит явное согласие до регистрации
            'data_processing_agreement': True,
            'vacancies_interest': data.get('vacancies_interest'),
        }
    )

@sync_to_async
def update_user(user, data):
    for k, v in data.items():
        setattr(user, k, v)
    user.save()

@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    # Если уже есть эксперт — показываем приветствие и кнопку "Расписание"
    username = message.from_user.username
    tg_id = message.from_user.id
    user = await _get_user_by_username_or_id(username=username, telegram_id=tg_id)
    if user and user.is_expert:
        first_name = (user.first_name or '').strip()
        last_name = (user.last_name or '').strip()
        full_name = (first_name + (' ' + last_name if last_name else '')).strip()
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text='Расписание')]],
            resize_keyboard=True
        )
        await message.answer(f"Здравствуйте! Добро пожаловать, {full_name}.")
        await message.answer("Используйте кнопку ниже, чтобы открыть расписание.", reply_markup=keyboard)
        return

    # Стартовое приветствие и кнопка "Старт"
    intro_text = (
        "Это бот для участия в активностях стенда Yandex на конференции Metamarketing 2025! "
        "Регистрация для входа в приложение займет меньше минуты. Нажмите кнопку «Старт», чтобы начать!"
    )
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='Старт')]],
        resize_keyboard=True
    )
    await message.answer(intro_text, reply_markup=keyboard)

@dp.message(F.text == 'Открыть приложение')
async def open_app(message: types.Message):
    # Если пользователь уже есть — выдадим WebApp кнопку
    username = message.from_user.username
    tg_id = message.from_user.id
    user = await _get_user_by_username_or_id(username=username, telegram_id=tg_id)
    if user and not user.is_expert:
        ikb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text='Открыть приложение', web_app=WebAppInfo(url=FRONTEND_BASE_URL))]]
        )
        await message.answer('Нажмите кнопку ниже, чтобы открыть приложение:', reply_markup=ikb)
        return
    if user and user.is_expert:
        first_name = (user.first_name or '').strip()
        last_name = (user.last_name or '').strip()
        full_name = (first_name + (' ' + last_name if last_name else '')).strip()
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text='Расписание')]],
            resize_keyboard=True
        )
        await message.answer(f'Здравствуйте! Добро пожаловать, {full_name}. Нажмите "Расписание" для просмотра.', reply_markup=keyboard)
        return
    # Если почему-то нет пользователя
    await message.answer("Начните с команды /start")

@dp.message(F.text == 'Расписание')
async def show_schedule(message: types.Message):
    try:
        print(f"Schedule button pressed by user {message.from_user.id}")
        username = message.from_user.username
        tg_id = message.from_user.id
        user = await _get_user_by_username_or_id(username=username, telegram_id=tg_id)
        print(f"User found: {user}, is_expert: {user.is_expert if user else 'No user'}")
        if user and user.is_expert:
            # Build schedule text
            def build_schedule_text(slots):
                if not slots:
                    return "На сегодня записей на консультации нет."
                lines = [
                    "📅 Ваши забронированные консультации:",
                    "",
                ]
                for s in slots:
                    date_part = s.start_time.strftime('%d.%m.%Y')
                    time_str = f"{s.start_time.strftime('%H:%M')} - {s.end_time.strftime('%H:%M')}"
                    # Safely handle missing booked_by
                    if s.booked_by:
                        bn = s.booked_by
                        user_name = f"{bn.first_name or ''} {bn.last_name or ''}".strip() or "Без имени"
                        username = f"@{bn.username}" if bn.username else "без username"
                    else:
                        user_name = "—"
                        username = "—"
                    topic_name = getattr(getattr(s, 'topic', None), 'name', '—')
                    lines.append(f"📆 {date_part} • 🕐 {time_str}")
                    lines.append(f"👤 {user_name} ({username})")
                    lines.append(f"📋 Тема: {topic_name}")
                    lines.append("📍 Место встречи: стойка информации на стенде Яндекса, 1 этаж")
                    lines.append("─" * 30)
                return "\n".join(lines)

            slots = await sync_to_async(list)(
                ConsultationSlot.objects.select_related('topic', 'booked_by').filter(expert=user, is_booked=True).order_by('start_time')
            )
            print(f"Found {len(slots)} booked consultation slots for expert {user.id}")
            schedule_text = build_schedule_text(slots)
            print(f"Schedule text: {schedule_text}")
            keyboard = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text='Расписание')]],
                resize_keyboard=True
            )
            await message.answer(schedule_text, reply_markup=keyboard)
        else:
            await message.answer("Эта функция доступна только экспертам.", reply_markup=ReplyKeyboardRemove())
    except Exception as e:
        # Ensure bot responds even if there is an unexpected error
        print(f"Error while building schedule: {e}")
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text='Расписание')]],
            resize_keyboard=True
        )
        await message.answer("Не удалось загрузить расписание. Попробуйте позже.", reply_markup=keyboard)

@dp.message(F.text == 'Старт')
async def start_consent_flow(message: types.Message):
    # Сообщения согласия и кнопка подтверждения
    await message.answer(
        "Прежде чем мы начнём, просим вас ознакомиться с согласием на обработку персональных данных и подтвердить его. "
        "Это нужно, чтобы мы могли связаться с вами, если вы войдёте в топ участников и получите свой приз!",
        reply_markup=ReplyKeyboardRemove()
    )
    await message.answer(
        '<a href="https://yandex.ru/legal/hr_privacy/ru/">Политика конфиденциальности</a>',
        parse_mode="HTML"
    )
    await message.answer(
        "Я даю согласие ООО «Яндекс» (119021, Россия, г. Москва, ул. Льва Толстого, д. 16) и его аффилированным лицам "
        "на обработку моих персональных данных в целях направления мне приглашений на мероприятия, проводимые Яндексом, "
        "и иных сообщений рекламного характера."
    )
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='Я прочитал(а) и даю согласие')]],
        resize_keyboard=True
    )
    await message.answer("Подтвердите, пожалуйста:", reply_markup=kb)

@dp.message(F.text == 'Я прочитал(а) и даю согласие')
async def vacancies_question(message: types.Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='Да, мне интересны вакансии Яндекса')],
            [KeyboardButton(text='Нет, я просто хочу запустить бота')],
        ],
        resize_keyboard=True
    )
    await message.answer(
        "Мы в Яндексе всегда рады профессионалам, готовым присоединиться к нашей команде. "
        "Хотели бы вы получать информацию о наших вакансиях?",
        reply_markup=kb
    )

async def proceed_to_registration(message: types.Message):
    user_id = message.from_user.id
    # Сохраняем vacancies_interest из предыдущего состояния, если оно есть
    old_state = user_state.get(user_id, {})
    old_data = old_state.get('data', {})
    vacancies_interest = old_data.get('vacancies_interest')
    
    user_state[user_id] = {'step': 0, 'data': {}}
    if vacancies_interest is not None:
        user_state[user_id]['data']['vacancies_interest'] = vacancies_interest
    
    await message.answer("Здравствуйте! Для входа в приложение заполните несколько полей.", reply_markup=ReplyKeyboardRemove())
    await message.answer(fields[0][1])

@dp.message(F.text == 'Да, мне интересны вакансии Яндекса')
async def vacancies_interest_yes(message: types.Message):
    tg_id = message.from_user.id
    username = message.from_user.username
    user = await _get_user_by_username_or_id(username=username, telegram_id=tg_id)
    if user:
        user.vacancies_interest = True
        await sync_to_async(user.save)()
    else:
        if tg_id not in user_state:
            user_state[tg_id] = {'step': -1, 'data': {}}
        user_state[tg_id]['data']['vacancies_interest'] = True
    await message.answer(
        "Отлично! Мы будем присылать информацию о вакансиях.",
        reply_markup=ReplyKeyboardRemove()
    )
    await proceed_to_registration(message)

@dp.message(F.text == 'Нет, я просто хочу запустить бота')
async def proceed_without_vacancies(message: types.Message):
    # Сохраняем выбор о вакансиях
    tg_id = message.from_user.id
    username = message.from_user.username
    user = await _get_user_by_username_or_id(username=username, telegram_id=tg_id)
    if user:
        user.vacancies_interest = False
        await sync_to_async(user.save)()
    else:
        if tg_id not in user_state:
            user_state[tg_id] = {'step': -1, 'data': {}}
        user_state[tg_id]['data']['vacancies_interest'] = False
    
    await message.answer("Хорошо!", reply_markup=ReplyKeyboardRemove())
    await proceed_to_registration(message)

@dp.message(~F.text.startswith('/'))
async def collect_data(message: types.Message):
    user_id = message.from_user.id
    state = user_state.get(user_id)
    if not state:
        # Игнорируем нажатие кнопки "Открыть приложение" здесь — есть отдельный хендлер
        if message.text and message.text.strip() == 'Открыть приложение':
            return
        # Игнорируем нажатие кнопки "Расписание" здесь — есть отдельный хендлер
        if message.text and message.text.strip() == 'Расписание':
            return
        # Игнорируем кнопки онбординга
        if message.text and message.text.strip() in {
            'Старт',
            'Я прочитал(а) и даю согласие',
            'Да, мне интересны вакансии Яндекса',
            'Нет, я просто хочу запустить бота',
        }:
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
            await message.answer("Имя должно содержать минимум 2 буквы и только буквы. Попробуйте ещё раз:", reply_markup=ReplyKeyboardRemove())
            return
        data[field] = value
        step += 1
        state['step'] = step
        await message.answer(fields[step][1], reply_markup=ReplyKeyboardRemove())
        return

    # LAST_NAME validation
    if field == 'last_name':
        if not (len(value) >= 2 and value.isalpha()):
            await message.answer("Фамилия должна содержать минимум 2 буквы и только буквы. Попробуйте ещё раз:", reply_markup=ReplyKeyboardRemove())
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
            await message.answer("Пожалуйста, введите корректный email, например user@email.com", reply_markup=ReplyKeyboardRemove())
            return
        data[field] = value
        step += 1
        state['step'] = step
        await message.answer(fields[step][1], reply_markup=ReplyKeyboardRemove())
        return

    # WORKPLACE validation
    if field == 'workplace':
        if len(value) < 2:
            await message.answer("Место работы должно быть не короче 2 символов. Попробуйте снова:", reply_markup=ReplyKeyboardRemove())
            return
        data[field] = value
        step += 1
        state['step'] = step
        await message.answer(fields[step][1], reply_markup=ReplyKeyboardRemove())
        return

    # POSITION validation
    if field == 'position':
        if len(value) < 2:
            await message.answer("Должность должна быть не короче 2 символов. Попробуйте снова:", reply_markup=ReplyKeyboardRemove())
            return
        data[field] = value
        step += 1
        state['step'] = step
        # Дальше обработается общий переход к завершению

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
        else:
            await message.answer(next_prompt, reply_markup=ReplyKeyboardRemove())
    else:
        username = message.from_user.username
        data['telegram_id'] = message.from_user.id
        user, created = await get_or_create_user(username, data)
        if not created:
            await update_user(user, data)
        user_state.pop(user_id, None)
        ikb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text='Открыть приложение', web_app=WebAppInfo(url=FRONTEND_BASE_URL))]]
        )
        await message.answer('Спасибо, регистрация завершена!', reply_markup=ReplyKeyboardRemove())
        if user.is_expert:
            first_name = (user.first_name or '').strip()
            last_name = (user.last_name or '').strip()
            full_name = (first_name + (' ' + last_name if last_name else '')).strip()
            keyboard = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text='Расписание')]],
                resize_keyboard=True
            )
            await message.answer(f'Здравствуйте! Добро пожаловать, {full_name}. Нажмите "Расписание" для просмотра.', reply_markup=keyboard)
        else:
            await message.answer('Нажмите кнопку ниже, чтобы открыть приложение:', reply_markup=ikb)

QUIZ_COMMANDS = {
    "quiz-20": "2025-11-20",
    "quiz20": "2025-11-20",
    "quiz-21": "2025-11-21",
    "quiz21": "2025-11-21",
}


@sync_to_async
def get_quiz_top_by_date(quiz_date: str, limit: int = 10):
    queryset = (
        QuizResult.objects.select_related('user')
        .filter(quiz_date=quiz_date)
        .order_by('-correct_answers', 'completed_at')[:limit]
    )
    top = []
    for result in queryset:
        user = result.user
        top.append({
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "correct_answers": result.correct_answers,
            "total_questions": result.total_questions,
            "completed_at": result.completed_at.strftime('%d.%m.%Y %H:%M'),
        })
    return top


def _build_quiz_winner_text(quiz_date: str, players):
    from datetime import datetime
    formatted_date = datetime.fromisoformat(quiz_date).strftime('%d.%m.%Y')
    header = f"🏆 <b>ТОП-10 участников квиза {formatted_date}</b>"
    lines = [header, ""]
    for idx, player in enumerate(players, start=1):
        full_name = f"{player['first_name']} {player['last_name']}".strip() or "—"
        username = f"@{player['username']}" if player['username'] else "—"
        lines.append(f"{idx}. {full_name} ({username})")
        lines.append(
            f"   ✅ {player['correct_answers']} из {player['total_questions']} • 🕒 {player['completed_at']}"
        )
        lines.append("")
    return "\n".join(lines).strip()


async def _handle_quiz_top(message: types.Message, quiz_date: str) -> None:
    top_players = await get_quiz_top_by_date(quiz_date)
    if not top_players:
        await message.answer("Пока никто не прошёл квиз 😢")
        return
    await message.answer(
        _build_quiz_winner_text(quiz_date, top_players),
        parse_mode="HTML"
    )


@dp.message(Command(commands=["quiz-20", "quiz20"], ignore_case=True, ignore_mention=True))
async def quiz_20(message: types.Message):
    user = await _ensure_registered_user(message)
    if not user:
        return
    await _handle_quiz_top(message, QUIZ_COMMANDS["quiz-20"])


@dp.message(Command(commands=["quiz-21", "quiz21"], ignore_case=True, ignore_mention=True))
async def quiz_21(message: types.Message):
    user = await _ensure_registered_user(message)
    if not user:
        return
    await _handle_quiz_top(message, QUIZ_COMMANDS["quiz-21"])


if __name__ == '__main__':
    asyncio.run(dp.start_polling(bot))