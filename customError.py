class IsNot200Error(Exception):
    """Ответ сервера не 200."""

    pass


class HomeworksKeyError(KeyError):
    """Отсутствует ключ "homeworks"."""

    pass


class NotDictTypeError(TypeError):
    """Неверный формат словаря."""

    pass


class NotListTypeError(TypeError):
    """Неверный формат списка."""

    pass


class ZeroHomeworksError(Exception):
    """Пустой список."""

    pass


class HomeworkNameKeyError(KeyError):
    """Отсутствует ключ "homework_name"."""

    pass


class StatusKeyError(KeyError):
    """Отсутствует ключ "status"."""

    pass


class NotStatusError(Exception):
    """Неверный статус."""

    pass


class NotNewStatusError(Exception):
    """Отсутствуют новые статусы."""

    pass
