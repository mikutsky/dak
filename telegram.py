import os
import asyncio
import base64
from io import BytesIO
import utils
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest, GetRepliesRequest

from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import PeerChannel
from PIL import Image


TELEGRAM_APP_ID = int(os.getenv('TELEGRAM_APP_ID'))
TELEGRAM_APP_HASH = os.getenv('TELEGRAM_APP_HASH')
TELEGRAM_APP_TITLE = os.getenv('TELEGRAM_APP_TITLE')
TELEGRAM_APP_SHORT_NAME = os.getenv('TELEGRAM_APP_SHORT_NAME')
TELEGRAM_PHONE = os.getenv('TELEGRAM_PHONE')

TELEGRAM_MESSAGE_LIMIT = 5
TICKET_PRICE = 200
THUMB_SIZE = (128, 128)

TELEGRAM = TelegramClient(TELEGRAM_PHONE, TELEGRAM_APP_ID, TELEGRAM_APP_HASH)
TELEGRAM_CHANNEL_ID = None


async def get_peer_channel_id():
    global TELEGRAM_CHANNEL_ID
    if not TELEGRAM.is_connected():
        await TELEGRAM.start()
    if TELEGRAM_CHANNEL_ID is None:
        entity = await TELEGRAM.get_entity(TELEGRAM_APP_TITLE)
        TELEGRAM_CHANNEL_ID = entity.id
    return TELEGRAM_CHANNEL_ID


async def get_comments_by_post_id(message_id, offset_id=None):
    if not TELEGRAM.is_connected():
        await TELEGRAM.start()
    offset_id = offset_id if isinstance(offset_id, int) and offset_id > 0 else 0
    peer_channel_id = await get_peer_channel_id()
    replies = await TELEGRAM(GetRepliesRequest(
        peer=PeerChannel(peer_channel_id),
        msg_id=message_id,
        offset_id=offset_id,
        offset_date=None,
        add_offset=0,
        limit=TELEGRAM_MESSAGE_LIMIT,
        max_id=0,
        min_id=0,
        hash=0
    ))
    messages = replies.messages
    if isinstance(messages, list) and len(messages):
        offset_id = messages[-1].id
    else:
        messages = []
    return replies, messages, offset_id


async def get_media_message(messages):
    for message in messages:
        _filename = utils.get_filename(message)
        if _filename:
            await TELEGRAM.download_media(message, file=_filename)
    return messages


async def get_posts(offset_id=None, count=None):
    if not TELEGRAM.is_connected():
        await TELEGRAM.start()
    offset_id = offset_id if isinstance(offset_id, int) and offset_id > 0 else 0
    count = count if isinstance(count, int) else TELEGRAM_MESSAGE_LIMIT
    peer_channel_id = await get_peer_channel_id()
    history = await TELEGRAM(GetHistoryRequest(
        peer=PeerChannel(peer_channel_id),
        offset_id=offset_id,
        offset_date=None,
        add_offset=0,
        limit=count,
        max_id=0,
        min_id=0,
        hash=0
    ))
    posts = history.messages
    offset_id = offset_id if not posts else posts[-1].id
    response = {
        'posts': [{
            'id': p.id,
            'date': p.date.isoformat(),
            'post_author': p.post_author,
            'message': p.message,
            'img_base64': ''
        } for p in posts],
        'lastId': offset_id
    }
    if posts:
        for idx, post in enumerate(posts):
            if post.media:
                image_path = f'posts_media/{post.id}.jpg'
                image_thumb_path = f'posts_media/{post.id}_thumb.jpg'
                await TELEGRAM.download_media(post, file=image_path)
                with Image.open(image_path) as img:
                    img_ratio = img.width / img.height
                    target_ratio = THUMB_SIZE[0] / THUMB_SIZE[1]
                    if img_ratio > target_ratio:
                        new_height = img.height
                        new_width = int(target_ratio * img.height)
                        left = (img.width - new_width) / 2
                        right = (img.width + new_width) / 2
                        img = img.crop((left, 0, right, new_height))
                    elif img_ratio < target_ratio:
                        new_width = img.width
                        new_height = int(img.width / target_ratio)
                        top = (img.height - new_height) / 2
                        bottom = (img.height + new_height) / 2
                        img = img.crop((0, top, new_width, bottom))
                    img = img.resize(THUMB_SIZE)
                    img.save(image_thumb_path, format='JPEG', quality=60, progressive=True)
                    buffer = BytesIO()
                    img.save(buffer, format='JPEG', quality=60, progressive=True)
                    buffer.seek(0)
                    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                    img_base64 = f"data:image/jpeg;base64,{img_base64}"
                    response['posts'][idx]['img_base64'] = img_base64

    return response, history, posts, offset_id


async def get_post(post_id=None):
    if not TELEGRAM.is_connected():
        await TELEGRAM.start()
    post_id = post_id if isinstance(post_id, int) and post_id > 0 else 0
    post = await TELEGRAM.get_messages(
        TELEGRAM_APP_TITLE,
        ids=post_id
    )
    response = None
    if post:
        response = {
            'id': post.id,
            'date': post.date.isoformat(),
            'post_author': post.post_author,
            'message': post.message,
            'img_base64': ''
        }
        if post.media:
            image_path = f'posts_media/{post.id}.jpg'
            image_thumb_path = f'posts_media/{post.id}_thumb.jpg'
            await TELEGRAM.download_media(post, file=image_path)
            with Image.open(image_path) as img:
                img_ratio = img.width / img.height
                target_ratio = THUMB_SIZE[0] / THUMB_SIZE[1]
                if img_ratio > target_ratio:
                    new_height = img.height
                    new_width = int(target_ratio * img.height)
                    left = (img.width - new_width) / 2
                    right = (img.width + new_width) / 2
                    img = img.crop((left, 0, right, new_height))
                elif img_ratio < target_ratio:
                    new_width = img.width
                    new_height = int(img.width / target_ratio)
                    top = (img.height - new_height) / 2
                    bottom = (img.height + new_height) / 2
                    img = img.crop((0, top, new_width, bottom))
                img = img.resize(THUMB_SIZE)
                img.save(image_thumb_path, format='JPEG', quality=60, progressive=True)
                buffer = BytesIO()
                img.save(buffer, format='JPEG', quality=60, progressive=True)
                buffer.seek(0)
                img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                img_base64 = f"data:image/jpeg;base64,{img_base64}"
                response['img_base64'] = img_base64
    return response


async def send_answer(message):
    if not TELEGRAM.is_connected():
        await TELEGRAM.start()
    reply_id = int(message.get('id'))
    text = message.get('answer')

    peer_channel_id = await get_peer_channel_id()
    channel = await TELEGRAM.get_entity(peer_channel_id)

    full_channel = await TELEGRAM(GetFullChannelRequest(channel))
    discussion_chat_id = full_channel.full_chat.linked_chat_id

    try:
        replies = await TELEGRAM.send_message(
            entity=discussion_chat_id,
            message=text,
            reply_to=reply_id
        )
        result = replies.message
        # result = await TELEGRAM(SendReactionRequest(
        #     peer=PeerChannel(peer_channel_id),
        #     msg_id=reply_id,
        #     add_to_recent=True,
        #     reaction=[ReactionEmoji(emoticon='❤️')]
        # ))
        return result
    except BaseException as _:
        return False


if __name__ == "__main__":
    asyncio.run(send_answer({'id': '69', 'answer': 'Test reaction'}))
    # idx = 8
    # import asyncio
    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)
    # offset_id = None
    # page = 0
    # all_posts = []
    # while True:
    #     print(f'==> {page}')
    #     _, _, posts, offset_id = loop.run_until_complete(get_posts(offset_id))
    #     if not posts:
    #         break
    #     all_posts.extend(posts)
    #     for p in posts:
    #         print(f'ID: {p.id}')
    #         print(f'DATE: {p.date}')
    #         print(f'AUTHOR: {p.post_author}')
    #         print(f'MESSAGE: {p.message}')
    #         print()
    #     page += 1
    #     time.sleep(1)
    #
    # print('================')
    # post_id = all_posts[idx].id
    # print(f'post_id {idx}: {post_id}')
    # print('================')
    # message_offset_id = None
    # message_part = 0
    # all_messages = []
    # last_ticket = 0
    # while True:
    #     print(f'\tMessage part: {message_part}')
    #     _, messages, message_offset_id = loop.run_until_complete(get_comments_by_post_id(post_id, message_offset_id))
    #     if not messages:
    #         break
    #     for m in messages:
    #         if m.media:
    #             filename = f'messages_media/{post_id}/{m.id}.jpg'
    #             data = parse_image(filename)
    #             if isinstance(data.amount, (float, int)):
    #                 text = None
    #                 tickets = []
    #                 _ticket_num = last_ticket
    #                 for t in range(data.amount // TICKET_PRICE):
    #                     _ticket_num = last_ticket + t + 1
    #                     tickets.append(str(_ticket_num))
    #                 last_ticket = _ticket_num
    #                 if len(tickets) == 1:
    #                     text = f'Ваш 🎟 квиточок: {tickets[0]}'
    #                 elif 1 < len(tickets) <= 4:
    #                     text = f'Ваші 🎟 квиточки: {", ".join(tickets)}'
    #                 elif len(tickets) > 4:
    #                     text = f'Ваші 🎟 квиточки від {tickets[0]} до {tickets[len(tickets) - 1]}'
    #                 else:
    #                     text = 'Дякую за донат'
    #                 print(f'\t[{data.datetime}] --> amount: {data.amount} uah\nANSWER: "{text}"')
    #             else:
    #                 print(f'\t!!! SEND NOTIFICATION !!!')
    #         else:
    #             print(f'\tAmount: None')
    #         print(f'ID: {m.id}')
    #         print(f'DATE: {m.date}')
    #         print(f'AUTHOR: {m.post_author}')
    #         print(f'MESSAGE: {m.message}')
    #         print()
    #     message_part += 1
    #     time.sleep(1)
    #
    #
