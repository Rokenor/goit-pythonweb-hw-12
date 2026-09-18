from slowapi import Limiter
from slowapi.util import get_remote_address

# Спільний лімітер: реєструється в `main.py` як `app.state.limiter`
limiter = Limiter(key_func=get_remote_address)
