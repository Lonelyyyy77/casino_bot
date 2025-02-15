from aiogram.fsm.state import StatesGroup, State


class PaymentState(StatesGroup):
    waiting_for_jpc = State()


class TransferState(StatesGroup):
    enter_username = State()
    enter_amount = State()
    confirm_transfer = State()
