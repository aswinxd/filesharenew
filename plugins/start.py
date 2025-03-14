#(©)CodeXBotz

import os
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated 
from database.database import check_join_request

from bot import Bot
from config import (
    ADMINS, FORCE_MSG, START_MSG, CUSTOM_CAPTION, DISABLE_CHANNEL_BUTTON, 
    PROTECT_CONTENT, START_PIC, AUTO_DELETE_TIME, AUTO_DELETE_MSG, 
    JOIN_REQUEST_ENABLE, FORCE_SUB_CHANNELS # WAIT_MSG, REPLY_ERROR
)
from database.database import add_user, present_user, add_join_request, full_userbase, del_user
from helper_func import subscribed, encode, decode, get_messages, delete_file
from pyrogram.types import ChatJoinRequest

async def get_join_buttons(client):
    buttons = []
    for channel_id in FORCE_SUB_CHANNELS:
        if JOIN_REQUEST_ENABLE:
            invite = await client.create_chat_invite_link(
                chat_id=channel_id,
                creates_join_request=True
            )
            ButtonUrl = invite.invite_link
        else:
            ButtonUrl = client.invite_links.get(channel_id, f"https://t.me/{channel_id}")
        buttons.append([InlineKeyboardButton(text="Join Channel", url=ButtonUrl)])
    return buttons

@Bot.on_message(filters.command('start') & filters.private)
async def not_joined(client: Client, message: Message):
    if await subscribed(client, message):
        return await start_command(client, message)
    
    buttons = await get_join_buttons(client)
    try:
        buttons.append([
            InlineKeyboardButton(
                text='Try Again',
                url=f"https://t.me/{client.username}?start={message.command[1]}"
            )
        ])
    except IndexError:
        pass

    await message.reply(
        text=FORCE_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=f"@{message.from_user.username}" if message.from_user.username else None,
            mention=message.from_user.mention,
            id=message.from_user.id
        ),
        reply_markup=InlineKeyboardMarkup(buttons),
        quote=True,
        disable_web_page_preview=True
    )

@Bot.on_message(filters.command('start') & filters.private & subscribed)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    if not await present_user(user_id):
        await add_user(user_id)
    
    text = message.text
    if len(text) > 7:
        try:
            base64_string = text.split(" ", 1)[1]
            decoded_string = await decode(base64_string)
            argument = decoded_string.split("-")
        except:
            return
        
        ids = []
        try:
            if len(argument) == 3:
                start = int(argument[1]) // abs(client.db_channel.id)
                end = int(argument[2]) // abs(client.db_channel.id)
                ids = range(min(start, end), max(start, end) + 1)
            elif len(argument) == 2:
                ids = [int(argument[1]) // abs(client.db_channel.id)]
        except:
            return

        temp_msg = await message.reply("Please wait...")
        try:
            messages = await get_messages(client, ids)
        except:
            await message.reply_text("Something went wrong..!")
            return
        
        await temp_msg.delete()
        track_msgs = []

        for msg in messages:
            caption = (CUSTOM_CAPTION.format(
                previouscaption=msg.caption.html if msg.caption else "", 
                filename=msg.document.file_name
            ) if CUSTOM_CAPTION and msg.document else msg.caption.html if msg.caption else "")
            
            reply_markup = msg.reply_markup if DISABLE_CHANNEL_BUTTON else None

            try:
                copied_msg = await msg.copy(
                    chat_id=message.from_user.id, caption=caption,
                    parse_mode=ParseMode.HTML, reply_markup=reply_markup,
                    protect_content=PROTECT_CONTENT
                )
                if AUTO_DELETE_TIME > 0:
                    track_msgs.append(copied_msg)
                await asyncio.sleep(0.5)
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception as e:
                print(f"Error copying message: {e}")

        if track_msgs:
            delete_data = await client.send_message(
                chat_id=message.from_user.id,
                text=AUTO_DELETE_MSG.format(time=AUTO_DELETE_TIME)
            )
            asyncio.create_task(delete_file(track_msgs, client, delete_data))

        return
    
    reply_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("😊 About Me", callback_data="about"),
            InlineKeyboardButton("🔒 Close", callback_data="close")
        ]
    ])

    if START_PIC:
        await message.reply_photo(
            photo=START_PIC,
            caption=START_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=f"@{message.from_user.username}" if message.from_user.username else None,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=reply_markup,
            quote=True
        )
    else:
        await message.reply_text(
            text=START_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=f"@{message.from_user.username}" if message.from_user.username else None,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            quote=True
        )



@Bot.on_message(filters.command('users') & filters.private & filters.user(ADMINS))
async def get_users(client: Bot, message: Message):
    msg = await client.send_message(chat_id=message.chat.id, text=WAIT_MSG)
    users = await full_userbase()
    await msg.edit(f"{len(users)} users are using this bot")

@Bot.on_message(filters.private & filters.command('broadcast') & filters.user(ADMINS))
async def send_text(client: Bot, message: Message):
    if message.reply_to_message:
        query = await full_userbase()
        broadcast_msg = message.reply_to_message
        total = 0
        successful = 0
        blocked = 0
        deleted = 0
        unsuccessful = 0
        
        pls_wait = await message.reply("<i>Broadcasting Message.. This will Take Some Time</i>")
        for chat_id in query:
            try:
                await broadcast_msg.copy(chat_id)
                successful += 1
            except FloodWait as e:
                await asyncio.sleep(e.x)
                await broadcast_msg.copy(chat_id)
                successful += 1
            except UserIsBlocked:
                await del_user(chat_id)
                blocked += 1
            except InputUserDeactivated:
                await del_user(chat_id)
                deleted += 1
            except:
                unsuccessful += 1
                pass
            total += 1
        
        status = f"""<b><u>Broadcast Completed</u>

Total Users: <code>{total}</code>
Successful: <code>{successful}</code>
Blocked Users: <code>{blocked}</code>
Deleted Accounts: <code>{deleted}</code>
Unsuccessful: <code>{unsuccessful}</code></b>"""
        
        return await pls_wait.edit(status)

    else:
        msg = await message.reply(REPLY_ERROR)
        await asyncio.sleep(8)
        await msg.delete()

from pyrogram import Client, filters
from pyrogram.types import ChatJoinRequest
import os


@Bot.on_chat_join_request(filters.chat(FORCE_SUB_CHANNELS))
async def handle_chat_join_request(client: Client, join_request: ChatJoinRequest):
    user_id = join_request.from_user.id
    group_id = join_request.chat.id
    print(f"Join request received from {user_id} in {group_id}")
    if not await check_join_request(group_id, user_id):
        print(f"User {user_id} is not in database. Adding...")
        await add_join_request(group_id, user_id)
    else:
        print(f"User {user_id} already exists in database.")
