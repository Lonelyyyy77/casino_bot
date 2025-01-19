from aiogram.fsm.state import StatesGroup, State


class MailingState(StatesGroup):
    enter_text = State()
    add_media = State()
    confirm = State()
    enter_reward_amount = State()
    enter_reward_uses = State()


class ReferralSettingsState(StatesGroup):
    change_percent_all = State()
    change_percent_user = State()


class SetPercentageStates(StatesGroup):
    waiting_for_percentage = State()
