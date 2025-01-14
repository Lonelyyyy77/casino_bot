from aiogram.fsm.state import StatesGroup, State


class MailingState(StatesGroup):
    enter_text = State()
    add_media = State()
    confirm = State()
    enter_reward_amount = State()
    enter_reward_uses = State()