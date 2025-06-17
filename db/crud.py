from models import Doctors  # проверь правильность импорта
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

async def get_doctor_name_by_id(session: AsyncSession, doctor_id: int) -> str:
    stmt = select(Doctors).where(Doctors.id == doctor_id)
    result = await session.execute(stmt)
    doctor = result.scalar_one_or_none()
    if doctor:
        return doctor.name  # или doctor.full_name — зависит от модели
    return "Неизвестный врач"
