from functools import partial
from io import BytesIO
from nonebot.adapters import Event, Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.message import MessageSegment
from nonebot.plugin import on_command
from nonebot.typing import T_State

from ..subchan.db import SubDB
from ..subchan.telechan import Chan, Ct, NotChanException, _handler

sub = on_command("sub")
unsub = on_command("unsub")
chan = on_command("chan")
stats = on_command("stats")

@sub.handle()
async def _(bot: Bot, event: Event, state: T_State):
    if not isinstance(event, GroupMessageEvent):
        await sub.finish("目前仅支持群聊")

    chan_id = str(event.get_message()).strip()
    if chan_id:
        state["chan_id"] = chan_id

@sub.got("chan_id", "channel id")
async def _(bot: Bot, event: Event, state: T_State):
    if not isinstance(event, GroupMessageEvent):
        await sub.finish()

    client = Ct().client
    chan_id = state["chan_id"]
    chan = Chan(chan_id, client)

    try:
        await chan.join_chan()
    except NotChanException:
        await sub.finish("这不是一个频道的id")
    else:
        real_chan = await chan.sub_chan(event.group_id)
        if not real_chan:
            await sub.finish("用户名错误或已订阅过")

        photo = BytesIO()
        await client.download_profile_photo(real_chan, file=photo)
        title = f"\\{real_chan.title}\\" + "\n"
        title = MessageSegment.text(title)
        photo = MessageSegment.image(photo.getvalue())
        await sub.finish(title + photo + "\n订阅成功")

@unsub.handle()
async def _(bot: Bot, event: Event, state: T_State):
    if not isinstance(event, GroupMessageEvent):
        await unsub.finish("目前仅支持群聊")

    chan_id = str(event.get_message()).strip()
    if chan_id:
        state["chan_id"] = chan_id

@unsub.got("chan_id", "channel id")
async def _(bot: Bot, event: Event, state: T_State):
    if not isinstance(event, GroupMessageEvent):
        await unsub.finish("目前仅支持群聊")

    chan_id = state["chan_id"]
    chan = Chan(chan_id, Ct().client)

    succ = await chan.unsub_chan(event.group_id)
    if succ:
        await unsub.finish(f"{chan_id} 取订成功")
    else:
        await unsub.finish(f"{chan_id} 未订阅过")

@chan.handle()
async def _(bot: Bot, event: Event, state: T_State):
    # TODO random choise, database? or request each time?
    test = Ct().client.list_event_handlers()
    msg = ""
    for i in test:
        msg += str(i)
        msg += "\n"
    if msg:
        await chan.finish(msg.strip())
    else:
        await chan.finish("Empty")


@stats.handle()
async def _(bot: Bot, event: Event, state: T_State):
    if not isinstance(event, GroupMessageEvent):
        await unsub.finish("目前仅支持群聊")

    db = SubDB()
    chans = db.get_chans(event.group_id)
    if chans:
        msg = "\n".join(chans)
    else:
        msg = "不可 Liyuu"
    await stats.finish(msg)
