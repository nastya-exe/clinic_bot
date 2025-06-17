from typing import List, Optional

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKeyConstraint, Integer, PrimaryKeyConstraint, String, Text, Time, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import datetime

class Base(DeclarativeBase):
    pass


class Clinics(Base):
    __tablename__ = 'clinics'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='clinics_pkey'),
        {'schema': 'public'}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    adress: Mapped[Optional[str]] = mapped_column(Text)
    phone: Mapped[Optional[str]] = mapped_column(Text)

    doctors: Mapped[List['Doctors']] = relationship('Doctors', back_populates='public')


class Patients(Base):
    __tablename__ = 'patients'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='patients_pkey'),
        UniqueConstraint('telegram_id', name='patients_telegram_id_key'),
        {'schema': 'public'}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(Text)
    phone: Mapped[str] = mapped_column(Text)
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

    appointments: Mapped[List['Appointments']] = relationship('Appointments', back_populates='patient')


class Doctors(Base):
    __tablename__ = 'doctors'
    __table_args__ = (
        ForeignKeyConstraint(['clinic_id'], ['public.clinics.id'], ondelete='CASCADE', name='doctors_clinic_id_fkey'),
        PrimaryKeyConstraint('id', name='doctors_pkey'),
        {'schema': 'public'}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(Text)
    clinic_id: Mapped[Optional[int]] = mapped_column(Integer)
    specialization: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('true'))

    public: Mapped[Optional['Clinics']] = relationship('Clinics', back_populates='doctors')
    appointments: Mapped[List['Appointments']] = relationship('Appointments', back_populates='doctor')
    doctor_schedule: Mapped[List['DoctorSchedule']] = relationship('DoctorSchedule', back_populates='doctor')


class Appointments(Base):
    __tablename__ = 'appointments'
    __table_args__ = (
        CheckConstraint("channel = ANY (ARRAY['telegram'::text, 'phone'::text, 'website'::text])", name='appointments_channel_check'),
        ForeignKeyConstraint(['doctor_id'], ['public.doctors.id'], ondelete='CASCADE', name='appointments_doctor_id_fkey'),
        ForeignKeyConstraint(['patient_id'], ['public.patients.id'], ondelete='CASCADE', name='appointments_patient_id_fkey'),
        PrimaryKeyConstraint('id', name='appointments_pkey'),
        {'schema': 'public'}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appointment_time: Mapped[datetime.datetime] = mapped_column(DateTime)
    patient_id: Mapped[Optional[int]] = mapped_column(Integer)
    doctor_id: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    channel: Mapped[Optional[str]] = mapped_column(Text, server_default=text("'telegram'::text"))

    doctor: Mapped[Optional['Doctors']] = relationship('Doctors', back_populates='appointments')
    patient: Mapped[Optional['Patients']] = relationship('Patients', back_populates='appointments')
    notifications: Mapped[List['Notifications']] = relationship('Notifications', back_populates='appointment')


class DoctorSchedule(Base):
    __tablename__ = 'doctor_schedule'
    __table_args__ = (
        ForeignKeyConstraint(['doctor_id'], ['public.doctors.id'], name='doctor_schedule_doctor_id_fkey'),
        PrimaryKeyConstraint('id', name='doctor_schedule_pkey'),
        {'schema': 'public'}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(Integer)
    day_of_week: Mapped[str] = mapped_column(String(10))
    start_time: Mapped[datetime.time] = mapped_column(Time)
    end_time: Mapped[datetime.time] = mapped_column(Time)

    doctor: Mapped['Doctors'] = relationship('Doctors', back_populates='doctor_schedule')


class Notifications(Base):
    __tablename__ = 'notifications'
    __table_args__ = (
        ForeignKeyConstraint(['appointment_id'], ['public.appointments.id'], ondelete='CASCADE', name='notifications_appointment_id_fkey'),
        PrimaryKeyConstraint('id', name='notifications_pkey'),
        {'schema': 'public'}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    notify_time: Mapped[datetime.datetime] = mapped_column(DateTime)
    appointment_id: Mapped[Optional[int]] = mapped_column(Integer)
    sent: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('false'))

    appointment: Mapped[Optional['Appointments']] = relationship('Appointments', back_populates='notifications')
