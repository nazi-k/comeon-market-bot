class NotEnoughQuantity(Exception):
    message = "Легше... В нас більше немає!"


class EditToEmptyCart(Exception):
    message = "Кошик порожній!\nАле ви можете це виправити😉"