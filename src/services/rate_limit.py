"""Спільний лімітер запитів.

Реєструється в :mod:`main` як ``app.state.limiter`` і застосовується
декоратором ``@limiter.limit(...)`` до окремих маршрутів.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

#: Лімітер, що рахує запити за IP-адресою клієнта.
limiter = Limiter(key_func=get_remote_address)
