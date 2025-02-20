#(©)Codexbotz

import base64
import re
import asyncio
import logging
from typing import Union
from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from pyrogram.errors import FloodWait
from config import (
    FORCE_SUB_CHANNELS,
    ADMINS,
    AUTO_DELETE_TIME,
    JOIN_REQUEST_ENABLE,
    AUTO_DEL_SUCCESS_MSG
)
from database.database import check_join_request


async def is_subscribed(filter, client, update) -> bool:
    if not FORCE_SUB_CHANNELS or update.from_user.id in ADMINS:
        return True

    user_id = update.from_user.id
    return all(await check_each(client, group_id, user_id) for group_id in FORCE_SUB_CHANNELS)


async def check_each(client, group_id: int, user_id: int) -> bool:
    try:
        membership = await check_membership(client, group_id, user_id)
        join_request_status = await check_join_request(group_id, user_id)

        return membership or (JOIN_REQUEST_ENABLE and join_request_status)
    except Exception:
        return False


async def check_membership(client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id=chat_id, user_id=user_id)
        return member.status in [
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.MEMBER,
        ]
    except UserNotParticipant:
        return False


async def encode(string: str) -> str:
    return base64.urlsafe_b64encode(string.encode()).decode().strip("=")


async def decode(base64_string: str) -> str:
    base64_string = base64_string.strip("=") 
    return base64.urlsafe_b64decode(base64_string + "=" * (-len(base64_string) % 4)).decode()


async def get_messages(client, message_ids: list):
    messages = []
    total_messages = 0

    while total_messages < len(message_ids):
        temp_ids = message_ids[total_messages : total_messages + 200]
        try:
            msgs = await client.get_messages(chat_id=client.db_channel.id, message_ids=temp_ids)
        except FloodWait as e:
            await asyncio.sleep(e.value)
            msgs = await client.get_messages(chat_id=client.db_channel.id, message_ids=temp_ids)
        except Exception:
            continue

        total_messages += len(temp_ids)
        messages.extend(msgs)

    return messages


async def get_message_id(client, message) -> int:
    if message.forward_from_chat and message.forward_from_chat.id == client.db_channel.id:
        return message.forward_from_message_id
    elif message.text:
        match = re.match(r"https://t.me/(?:c/)?(.*)/(\d+)", message.text)
        if match:
            channel_id, msg_id = match.groups()
            if channel_id.isdigit() and f"-100{channel_id}" == str(client.db_channel.id):
                return int(msg_id)
            elif channel_id == client.db_channel.username:
                return int(msg_id)
    return 0


def get_readable_time(seconds: int) -> str:
    time_suffix_list = ["s", "m", "h", "days"]
    time_list = []
    count = 0

    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60 if count < 3 else 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(f"{int(result)}{time_suffix_list[count - 1]}")
        seconds = int(remainder)

    return ":".join(reversed(time_list))


async def delete_file(messages, client, process):
    """Deletes messages after a set time and edits the process message."""
    await asyncio.sleep(AUTO_DELETE_TIME)

    for msg in messages:
        try:
            if msg:
                await client.delete_messages(chat_id=msg.chat.id, message_ids=[msg.id])
                print(f"Successfully deleted message {msg.id}")
        except Exception as e:
            print(f"Failed to delete message {msg.id}: {e}")

    try:
        await process.edit_text(AUTO_DEL_SUCCESS_MSG)
    except Exception as e:
        print(f"Failed to edit process message: {e}")


subscribed = filters.create(is_subscribed)
