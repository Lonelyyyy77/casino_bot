from aiogram.fsm.state import StatesGroup, State


class PaymentState(StatesGroup):
    waiting_for_jpc = State()