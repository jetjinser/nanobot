from typing import Any

class SingletonMeta(type):
    _instances = {}
    def __call__(cls, *args: Any, **kwds: Any) -> Any:
        if cls not in cls._instances:
            instances = super().__call__(*args, **kwds)
            cls._instances[cls] = instances
        return cls._instances[cls]
