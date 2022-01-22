import nonebot
from tortoise.exceptions import IntegrityError
from tortoise import Tortoise
from typing import Dict, Set

from ..subchan.models import Suber
from ..subchan.utils import SingletonMeta


class SubDB(metaclass=SingletonMeta):
    def __init__(self):
        self._subs: Dict[str, Set[int]] = {}

    async def _fresh(self):
        subs = await Suber.all().values()
        for sub in subs:
            self._subs.setdefault(sub["chan"], set()).add(sub["group"])

    async def insert_sub(self, chan: str, group: int):
        try:
            await Suber.create(chan=chan, group=group)
            self._subs.setdefault(chan, set()).add(group)
        except IntegrityError:
            pass
        return self._subs[chan]

    async def delete_sub(self, chan: str, group: int):
        await Suber.filter(group=group, chan=chan).delete()
        self._subs.setdefault(chan, set()).discard(group)
        return self._subs[chan]

    def get_subs(self):
        return self._subs

    def get_groups(self, chan: str):
        return self._subs.setdefault(chan, set())

    def get_chans(self, group: int):
        # TODO https://t.me/channel
        return {chan for chan, groups in self._subs.items() if group in groups}

async def init():
    from . import models
    await Tortoise.init(
            db_url = "sqlite://data/substore.sqlite3", # TODO env path
            modules = {
                "models": [locals()["models"]]
                }
            )
    await Tortoise.generate_schemas()
    await SubDB()._fresh()

driver = nonebot.get_driver()
# driver.on_startup(init)
driver.on_shutdown(Tortoise.close_connections)
