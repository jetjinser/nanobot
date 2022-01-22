import asyncio
from functools import partial
from io import BytesIO
from typing import Callable, Dict, Optional, Set, Union
import nonebot
from nonebot.adapters.cqhttp.message import MessageSegment, Message
from telethon import TelegramClient, events
from telethon.errors.rpcerrorlist import UsernameNotOccupiedError
from telethon.events.newmessage import NewMessage
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import Channel, PeerChannel

from ..subchan.db import SubDB, init
from ..subchan.utils import SingletonMeta

class Ham(metaclass=SingletonMeta):
    def __init__(self) -> None:
        self._handlers: Dict[int, Callable] = {}

    @staticmethod
    def _hash(groups: Set[int]):
        return hash("".join([str(group) for group in groups]))

    def save(self, groups: Set[int], handler: Callable):
        self._handlers[Ham._hash(groups)] = handler

    def pop(self, groups: Set[int]):
        return self._handlers.pop(Ham._hash(groups), None)


class Ct(metaclass=SingletonMeta):
    def __init__(self):
        config = nonebot.get_driver().config
        app_id = int(config.app_id)
        api_hash = config.api_hash

        tp_type = config.tp_type
        tp_host = config.tp_host
        tp_port = config.tp_port
        proxy = (tp_type, tp_host, tp_port)

        self.client = TelegramClient("subchan", app_id, api_hash, proxy=proxy, loop=asyncio.get_running_loop())

driver = nonebot.get_driver()

@driver.on_startup
async def _():
    from ..subchan.db import init
    await init()

    client = Ct().client
    await client.connect()
    db = SubDB()
    ham = Ham()
    subs = db.get_subs()
    print(subs)
    for chan, groups in subs.items():
        handler = partial(_handler, groups.copy())
        ham.save(groups, handler)
        client.add_event_handler(handler, events.NewMessage(chats=[chan]))


@driver.on_shutdown
async def _():
    dis = Ct().client.disconnect()
    if dis:
        await dis


class NotChanException(Exception):
    pass

# class JoinedException(Exception):
#     pass

class Chan(object):
    def __init__(self, chan_id: str, client: TelegramClient):
        self._chan_id = chan_id
        self._chan: Optional[Channel] = None
        self._client = client
        self._db = SubDB()
        self._groups = set()

    async def _is_chan(self) -> bool:
        try:
            chan = await self._client.get_entity(self._chan_id)
            if isinstance(chan, Channel):
                self._chan = chan
                return True
            return False
        except UsernameNotOccupiedError:
            return False

    async def _is_joined(self) -> bool:
        chan = self._chan
        if not chan:
            chan = await self._client.get_entity(self._chan_id)
        async for dialog in self._client.iter_dialogs():
            if chan.id == dialog.entity.id:
                return True
        return False

    async def join_chan(self):
        if not await self._is_chan():
            raise NotChanException()

        if not await self._is_joined():
            await self._client(JoinChannelRequest(self._chan)) # type: ignore

    async def sub_chan(self, group: int) -> Optional[Channel]:
        await self.join_chan()
        subs = self._db.get_subs()
        groups = subs.setdefault(self._chan_id, set())
        if group in groups:
            return None

        ham = Ham()
        handler = ham.pop(groups)
        if handler:
            self._client.remove_event_handler(handler)

        groups = await self._db.insert_sub(self._chan_id, group)
        han = partial(_handler, groups.copy())
        ham.save(groups, han)
        self._client.add_event_handler(han, events.NewMessage(chats=[self._chan_id]))
        return self._chan
    

    async def unsub_chan(self, group: int):
        groups = self._db.get_groups(self._chan_id)
        if len(groups) == 0:
            return False

        ham = Ham()
        handler = ham.pop(groups)
        if handler:
            self._client.remove_event_handler(handler)

        groups = await self._db.delete_sub(self._chan_id, group)
        if len(groups) > 0:
            han = partial(_handler, groups.copy())
            ham.save(groups, han)
            self._client.add_event_handler(han, events.NewMessage(chats=[self._chan_id]))

        return True


async def _handler(groups: Set[int], event: NewMessage.Event):
    for _, bot in nonebot.get_bots().items():
        for group in groups:
            msg = await _format(event)
            await bot.send_group_msg(group_id=group, message=msg)

async def _format(event: NewMessage.Event) -> Union[Message, MessageSegment]:
    # TODO pritter
    client = Ct().client

    msg = event.message
    ctx = MessageSegment.text(msg.message)
    if hasattr(event, "photo") and event.photo:
        photo = BytesIO()
        await client.download_media(msg, file=photo)
        ctx += "\n"
        ctx += MessageSegment.image(photo.getvalue())

    peer: PeerChannel = msg.peer_id
    entity = await client.get_entity(peer)
    if isinstance(entity, Channel):
        ctx += "\n\n"

        title = entity.title
        username = entity.username

        ctx += f"from channel【{title} @{username}】"
    return ctx
