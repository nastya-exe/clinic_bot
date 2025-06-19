import asyncio


from aiogram.filters import Command, BaseFilter, CommandStart
from aiogram import Dispatcher, types, Bot, F
from aiogram.types import TelegramObject, Message, BotCommand, CallbackQuery, FSInputFile, InputMediaPhoto
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.models import Clinics, Doctors, DoctorSchedule
from config import BOT_TOKEN
from db.crud import get_doctor_name_by_id
from urllib.parse import quote


from db.db import async_session_maker

dp = Dispatcher()

async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="В начало"),
        BotCommand(command="appointment", description="Запись ко врачу"),
        BotCommand(command="my_appointments", description="Мои записи")
    ]
    await bot.set_my_commands(commands)

@dp.message(Command('start'))
async def cmd_start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👩‍⚕ Запись к врачу", callback_data="appointment"),
            InlineKeyboardButton(text="📋 Мои записи", callback_data="my_appointments")
        ]
    ])
    await message.answer(
        "Здравствуйте! Мы клиника МедКлиник.\nЗдесь можно записаться к специалисту, посмотреть свои записи.",
        reply_markup=keyboard
    )

# .............................................../appointment.........................................................................................................

class AppointmentStates(StatesGroup):
    choosing_specialization = State() # Специализация
    choosing_clinic = State() # Клиника
    choosing_mode = State() # Способ (врач / ближайшее время)
    choosing_doctor = State() # Выбор врача
    choosing_time = State() # Время
    confirming_appointment = State() # Подтверждение
    waiting_for_webapp = State()  # Ожидание WebApp

async def show_specialists(target, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Терапевт", callback_data="spec_therapist"),
            InlineKeyboardButton(text="Гинеколог", callback_data="spec_gynecologist"),
            InlineKeyboardButton(text="Хирург", callback_data="spec_surgeon")
        ],
        [
            InlineKeyboardButton(text="Уролог", callback_data="spec_urologist"),
            InlineKeyboardButton(text="Назад", callback_data="go_back_to_start")
        ]
    ])

    if isinstance(target, Message):
        await target.answer("Выберите специалиста к которому хотите записаться:", reply_markup=keyboard)
    elif isinstance(target, CallbackQuery):
        await target.message.edit_text("Выберите специалиста к которому хотите записаться:", reply_markup=keyboard)


@dp.callback_query(F.data == "appointment")
async def handle_appointment_callback(callback: CallbackQuery, state: FSMContext):
    await show_specialists(callback, state)


@dp.message(Command("appointment"))
async def handle_appointment_command(message: Message, state: FSMContext):
    await show_specialists(message, state)


@dp.callback_query(F.data == "go_back_to_start")
async def go_back_to_start_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👩‍⚕ Запись к врачу", callback_data="appointment"),
            InlineKeyboardButton(text="📋 Мои записи", callback_data="my_appointments")
        ]
    ])
    await callback.message.edit_text(
        "Здравствуйте! Мы клиника МедКлиник.\nЗдесь можно записаться к специалисту, посмотреть свои записи.",
        reply_markup=keyboard
    )
    await callback.answer()

SPECIALIZATIONS = {
    "spec_therapist": "Терапевт",
    "spec_gynecologist": "Гинеколог",
    "spec_surgeon": "Хирург",
    "spec_urologist": "Уролог",
}

@dp.callback_query(F.data.startswith("spec_"))
async def handle_specialist_selection(callback: CallbackQuery, state: FSMContext):
    specialist_code = callback.data
    specialization = SPECIALIZATIONS.get(specialist_code)

    if not specialization:
        await callback.answer("Неизвестная специальность")
        return

    await state.update_data(chosen_specialization=specialization)

    async with async_session_maker() as session: # создание асинхронной сессии SQLAlchemy для работы с БД.
        stmt = (
            select(Clinics)
            .join(Doctors)
            .where(
                Doctors.specialization == specialization,
                Doctors.is_active == True
            )
            .options(selectinload(Clinics.doctors))  # подгрузи врачей заранее (оптимизация)
        )
        result = await session.execute(stmt)
        clinics = result.scalars().unique().all()

    if not clinics:
        await callback.message.edit_text("Нет доступных клиник для выбранного специалиста.")
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=clinic.adress or "Без адреса", callback_data=f"clinic_{clinic.id}")]
            for clinic in clinics
        ] + [[InlineKeyboardButton(text="Назад", callback_data="appointment")]]
    )

    await callback.message.edit_text(
        f"Вы выбрали: {specialization}\n\nВыберите подходящую для Вас клинику:",
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith("clinic_"))
async def clinic_chosen_handler(callback: CallbackQuery, state: FSMContext):
    clinic_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    specialization_raw = data.get("chosen_specialization", "")
    specialization = specialization_raw.replace("spec_", "")

    await state.update_data(chosen_clinic=clinic_id, chosen_specialization=specialization)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Выбрать врача", callback_data="choose_doctor"),
            InlineKeyboardButton(text="⏱ Ближайшее время", callback_data="nearest_slot")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="go_back_to_clinics")
        ]
    ])
    await callback.message.edit_text("Как хотите записаться?", reply_markup=keyboard)
    await state.set_state(AppointmentStates.choosing_mode)

@dp.callback_query(F.data == "go_back_to_clinics")
async def go_back_to_clinics_handler(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    specialization = data.get("chosen_specialization")

    if not specialization:
        await callback.message.edit_text("Ошибка: специализация не выбрана. Пожалуйста, выберите специалиста заново.")
        await state.set_state(AppointmentStates.choosing_specialization)
        await callback.answer()
        return

    async with async_session_maker() as session:
        stmt = (
            select(Clinics)
            .join(Doctors)
            .where(
                Doctors.specialization == specialization,
                Doctors.is_active == True
            )
            .options(selectinload(Clinics.doctors))
        )
        result = await session.execute(stmt)
        clinics = result.scalars().unique().all()

    if not clinics:
        await callback.message.edit_text("Нет доступных клиник для выбранного специалиста.")
        await callback.answer()
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=clinic.adress or "Без адреса", callback_data=f"clinic_{clinic.id}")]
            for clinic in clinics
        ] + [[InlineKeyboardButton(text="Назад", callback_data="go_back_to_specialists")]]
    )

    await callback.message.edit_text(
        f"Вы выбрали: {specialization}\n\nВыберите подходящую для Вас клинику:",
        reply_markup=keyboard
    )
    await state.set_state(AppointmentStates.choosing_clinic)
    await callback.answer()


@dp.callback_query(F.data == "nearest_slot")
async def nearest_slot_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Показываю ближайшие доступные окна...")
    await state.set_state(AppointmentStates.choosing_time)

@dp.callback_query(F.data == "go_back_to_clinics")
async def go_back_to_clinics_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Возвращаемся к выбору клиники...")
    await state.set_state(AppointmentStates.choosing_clinic)


@dp.callback_query(F.data == "choose_doctor")
async def choose_doctor_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    clinic_id = data.get("chosen_clinic")
    specialization = data.get("chosen_specialization")

    if not clinic_id or not specialization:
        await callback.message.answer("Ошибка: не выбраны клиника или специализация.")
        return

    async with async_session_maker() as session:
        result = await session.execute(
            select(Doctors)
            .where(
                Doctors.clinic_id == clinic_id,
                Doctors.specialization == specialization,
                Doctors.is_active == True
            )
        )
        doctors = result.scalars().all()

    if not doctors:
        await callback.message.answer("К сожалению, по выбранной специализации в этой клинике нет доступных врачей.")
        return

    # Формируем инлайн-кнопки
    keyboard = InlineKeyboardBuilder()
    for doctor in doctors:
        keyboard.button(
            text=f"{doctor.full_name}",
            callback_data=f"doctor_{doctor.id}"
        )
    keyboard.button(text="🔙 Назад", callback_data="go_back_to_mode")
    keyboard.adjust(1)

    await callback.message.edit_text("Выберите врача:", reply_markup=keyboard.as_markup())
    await state.set_state(AppointmentStates.choosing_doctor)

@dp.callback_query(F.data == "go_back_to_mode")
async def go_back_to_mode_handler(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Выбрать врача", callback_data="choose_doctor"),
            InlineKeyboardButton(text="⏱ Ближайшее время", callback_data="nearest_slot")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="go_back_to_clinics")
        ]
    ])
    await callback.message.edit_text("Как хотите записаться?", reply_markup=keyboard)
    await state.set_state(AppointmentStates.choosing_mode)


@dp.callback_query(F.data.startswith("doctor_"))
async def doctor_chosen_handler(callback: CallbackQuery, state: FSMContext):
    doctor_id = int(callback.data.split("_")[1])

    # Сохраняем выбор врача в состояние
    async with async_session_maker() as session:
        doctor_name = await get_doctor_name_by_id(session, doctor_id)

    doctor_name_encoded = quote(doctor_name)
    telegram_user_id = callback.from_user.id

    webapp_url = f"""https://medclinicbot.ru/?doctor_id={doctor_id}
                     &doctor_name={doctor_name_encoded}
                     &patient_id={telegram_user_id}"""

    await state.update_data(chosen_doctor=doctor_id, chosen_doctor_name=doctor_name)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть расписание врача", web_app=WebAppInfo(url=webapp_url))],
        [InlineKeyboardButton(text="Назад", callback_data="choose_doctor")]
    ])

    await callback.message.edit_text(
        "Нажмите кнопку ниже, чтобы открыть расписание и выбрать время:",
        reply_markup=keyboard
    )
    await state.set_state(AppointmentStates.waiting_for_webapp)












async def main():
    bot = Bot(token=BOT_TOKEN)
    await set_commands(bot)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())