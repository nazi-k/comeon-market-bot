from aiogram.dispatcher.filters.state import State, StatesGroup


class CreateOrder(StatesGroup):
    waiting_for_region = State()
    waiting_for_city = State()
    waiting_for_nova_poshta_number = State()
