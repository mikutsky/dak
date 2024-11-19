import os
import sqlite3
import base64
import hashlib
import re

import llm
import telegram
from cryptography.fernet import Fernet

# todo: delete key
INTERNAL_SECRET = 'VAOkIjMWTO3kuKu2Qx5ZiF_OClSO0jqZ5MLGoScALcY='
EXTERNAL_SECRET = os.getenv('SECRET', INTERNAL_SECRET).encode()
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILENAME = os.path.join(PROJECT_DIR, 'configuration.db')
SECRET_FIELDS = ['secret', 'token', 'key']
INDENT = 2
STATUS = {
    'CREATED': 'created'
}

SECRET = base64.urlsafe_b64encode(hashlib.sha256(f'{EXTERNAL_SECRET}.{INTERNAL_SECRET}'.encode()).digest()[:32])
CRYPTO = Fernet(SECRET)
DB = sqlite3.connect(DB_FILENAME)


GIVEAWAYS_FIELDS = [
    "id",
    "name",
    "description",
    "status",
    "post_id",
    "post_date",
    "post_author",
    "post_message",
    "post_img",
    "interval",
    "start_datetime",
    "final_datetime",
    "last_message_id",
    "ticket_price",
    "answer",
    "tickets_total",
    "is_active",
    "is_answer",
    "is_reaction"
]

MESSAGES_FIELDS = [
    "id",
    "giveaway_id",
    "date",
    "edit_date",
    "sender_id",
    "message",
    "is_answer",
    "is_edit",
    "is_media",
    "is_reply",
    "is_sticker",
    "media_filename",
    "reply_id",
    "answer_id",
    "answer",
    "is_recognized",
    "is_reacted",
    "is_answered",
    "is_donate",
    "donate",
    "ticket_from",
    "ticket_count"
]


def init_db():
    cursor = DB.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key CHAR(32) PRIMARY KEY NOT NULL,
            value TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS giveaways (
            id CHAR(32) PRIMARY KEY,
            name CHAR(32) DEFAULT "",
            description CHAR(255) DEFAULT "",
            status CHAR(16) DEFAULT "created",
            post_id CHAR(24) DEFAULT "",
            post_date CHAR(28) DEFAULT "",
            post_author CHAR(64) DEFAULT "",
            post_message TEXT DEFAULT "",
            post_img BLOB DEFAULT NULL,
            interval INTEGER DEFAULT 0,
            start_datetime CHAR(28) DEFAULT NULL,
            final_datetime CHAR(28) DEFAULT NULL,
            last_message_id CHAR(32) DEFAULT NULL,
            ticket_price REAL DEFAULT 0.00,
            answer TEXT DEFAULT "",
            tickets_total INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 0,
            is_answer INTEGER DEFAULT 0,
            is_reaction INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id CHAR(32) PRIMARY KEY,
            giveaway_id CHAR(32) DEFAULT NULL,
            date CHAR(28) DEFAULT "",
            edit_date CHAR(28) DEFAULT "",
            sender_id CHAR(32) DEFAULT NULL,
            message CHAR(4096) DEFAULT NULL,
            is_answer INTEGER DEFAULT 0,
            is_edit INTEGER DEFAULT 0,
            is_media INTEGER DEFAULT 0,
            is_reply INTEGER DEFAULT 0,
            is_sticker INTEGER DEFAULT 0,
            media_filename CHAR(255) DEFAULT NULL,
            reply_id CHAR(32) DEFAULT NULL,
            answer_id CHAR(32) DEFAULT NULL,
            answer CHAR(255) DEFAULT "",
            is_recognized INTEGER DEFAULT 0,
            is_reacted INTEGER DEFAULT 0,
            is_answered INTEGER DEFAULT 0,
            is_donate INTEGER DEFAULT 0,
            donate REAL DEFAULT 0.00,
            ticket_from INTEGER DEFAULT 0,
            ticket_count INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id CHAR(32) PRIMARY KEY,
            money REAL DEFAULT 0.00,
            ticket_start INTEGER DEFAULT 0,
            tickets_count INTEGER DEFAULT 0,
            answer CHAR(255) DEFAULT "",
            is_bill INTEGER DEFAULT 0,
            is_answer INTEGER DEFAULT 0,
            is_reaction INTEGER DEFAULT 0
        )
    ''')
    DB.commit()
    cursor.close()


def reset_db():
    cursor = DB.cursor()
    cursor.execute('DROP TABLE IF EXISTS config')
    cursor.execute('DROP TABLE IF EXISTS giveaways')
    cursor.execute('DROP TABLE IF EXISTS messages')
    DB.commit()
    cursor.close()


def encrypt(data):
    _data = data.copy()
    for k, v in data.items():
        if any((t in k) for t in SECRET_FIELDS):
            _data[k] = CRYPTO.encrypt(v.encode()).decode()
    return _data


def decrypt(data):
    _data = data.copy()
    for k, v in data.items():
        if any((t in k) for t in SECRET_FIELDS):
            _data[k] = CRYPTO.decrypt(v.encode()).decode()
    return _data


def convert_dict(data):
    return [dict(zip('a', row)) for row in data]


def get_config():
    cursor = DB.cursor()
    cursor.execute('SELECT * FROM config')
    data = cursor.fetchall()
    decrypt_data = decrypt({k: v for (k, v) in data})
    return decrypt_data


def post_config(data):
    encrypted_data = encrypt(data)
    cursor = DB.cursor()
    for key, value in encrypted_data.items():
        cursor.execute('''
            INSERT OR REPLACE INTO config (key, value)
            VALUES (?, ?)
        ''', (key, value))
    DB.commit()
    cursor.close()


def get_filename(message):
    if not hasattr(message, 'id') or not hasattr(message, 'media') or message.media is None or \
            not hasattr(message.media, 'photo') or not hasattr(message.media.photo, 'id'):
        return None
    return f'messages_media/{message.id}/{message.media.photo.id}.jpg'


def get_giveaway_id(post):
    return f'gi_{telegram.TELEGRAM_APP_TITLE[:8]}:{post.get("id")}'


def get_post_id(giveaway_id):
    return giveaway_id.split(':')[1]


def get_dict(record, fields):
    def convert(v):
        if isinstance(v, bytes):
            v = v.decode('utf-8')
        return v
    return {k: convert(record[i]) for i, k in enumerate(fields)}


def get_giveaway(post_id):
    cursor = DB.cursor()
    cursor.execute("SELECT * FROM giveaways WHERE id = ?", (post_id,))
    record = cursor.fetchone()
    if not record:
        return None
    return get_dict(record, GIVEAWAYS_FIELDS)


def save_config(data, giveaway_id):
    cursor = DB.cursor()
    _data = data.dict()
    fields = []
    values = ()
    for k in _data:
        if _data[k] is not None:
            fields += [f'{k} = ?']
            values += (_data[k],)
    fields = ', '.join(fields)
    values += (giveaway_id,)
    cursor.execute(f"""
        UPDATE giveaways
        SET {fields}
        WHERE id = ?
    """, values)
    DB.commit()
    cursor.execute("""
        SELECT * FROM giveaways WHERE id = ?
    """, (giveaway_id,))
    updated_record = cursor.fetchone()

    return updated_record


def set_giveaways(post):
    post_id = get_giveaway_id(post)
    record = get_giveaway(post_id)
    cursor = DB.cursor()
    if record:
        return record
    _id = get_giveaway_id(post)
    post_id = str(post.get('id'))
    post_date = post.get('date', '')
    post_author = post.get('post_author', '')
    post_message = post.get('message', '')
    post_img = post.get('img_base64', '')
    post_img = post_img.encode('utf-8') if len(post_img) else None
    name = f'{post_message[:24]}...'
    description = f'{post_message[:250]}...'
    status = STATUS['CREATED']
    interval = post.get('interval', 60000)
    start_datetime = post.get('start_datetime', post.get('date', ''))
    final_datetime = post.get('final_datetime', post.get('date', ''))
    last_message_id = None
    ticket_price = post.get('ticket_price', 100.0)
    answer = post.get('answer', 'Ваш{-і} 🎫 квиточ{ок-ки}: {%tickets}')
    tickets_total = 0
    is_active = 0
    is_answer = 0
    is_reaction = 0
    record = (
        _id,
        name,
        description,
        status,
        post_id,
        post_date,
        post_author,
        post_message,
        post_img,
        interval,
        start_datetime,
        final_datetime,
        last_message_id,
        ticket_price,
        answer,
        tickets_total,
        is_active,
        is_answer,
        is_reaction
    )
    cursor.execute('''INSERT INTO giveaways (id, name, description, status, post_id, post_date, post_author,
            post_message, post_img, interval, start_datetime, final_datetime, last_message_id, ticket_price, answer,
            tickets_total, is_active, is_answer, is_reaction)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', record)
    DB.commit()
    cursor.fetchone()
    return get_giveaway(_id)


def update_giveaway(_giveaway):
    record = get_giveaway(_giveaway['id'])
    cursor = DB.cursor()
    _id = _giveaway.get('id', None)
    post_id = str(_giveaway.get('post_id'))
    post_date = _giveaway.get('post_date')
    post_author = _giveaway.get('post_author', record.get('post_author', ''))
    post_message = _giveaway.get('post_message', record.get('post_message'))
    post_img = _giveaway.get('post_img', record.get('post_img', ''))
    post_img = post_img.encode('utf-8') if len(post_img) else None
    name = f'{post_message[:24]}...'
    description = f'{post_message[:250]}...'
    status = 'progress'
    interval = _giveaway.get('interval', record.get('interval', 60000))
    start_datetime = _giveaway.get('start_datetime', record.get('start_datetime', record.get('date', '')))
    final_datetime = _giveaway.get('final_datetime', record.get('final_datetime', record.get('date', '')))
    last_message_id = _giveaway.get('last_message_id', record.get('last_message_id'))
    ticket_price = _giveaway.get('ticket_price', record.get('ticket_price', 100.0))
    answer = _giveaway.get('answer', record.get('answer', 'Ваш{-і} 🎫 квиточ{ок-ки}: {%tickets}'))
    tickets_total = _giveaway.get('tickets_total', record.get('tickets_total', 0))
    is_active = _giveaway.get('is_active', record.get('is_active', 0))
    is_answer = _giveaway.get('is_answer', record.get('is_answer', 0))
    is_reaction = _giveaway.get('is_reaction', record.get('is_reaction', 0))
    record = (
        _id,
        name,
        description,
        status,
        post_id,
        post_date,
        post_author,
        post_message,
        post_img,
        interval,
        start_datetime,
        final_datetime,
        last_message_id,
        ticket_price,
        answer,
        tickets_total,
        is_active,
        is_answer,
        is_reaction
    )
    cursor.execute('''INSERT OR REPLACE INTO giveaways (id, name, description, status, post_id, post_date, post_author,
            post_message, post_img, interval, start_datetime, final_datetime, last_message_id, ticket_price, answer,
            tickets_total, is_active, is_answer, is_reaction)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', record)
    DB.commit()
    cursor.fetchone()
    return get_giveaway(_id)


def delete_giveaways(giveaways_id):
    cursor = DB.cursor()
    cursor.execute('''DELETE FROM giveaways WHERE id=?''', (giveaways_id,))
    DB.commit()
    return True


def add_existing_giveaways(posts):
    if not posts:
        return []
    for i, p in enumerate(posts):
        post_id = get_giveaway_id(p)
        giveaway = get_giveaway(post_id)
        posts[i]['is_giveaway'] = bool(giveaway)
        posts[i]['status'] = giveaway['status'] if posts[i]['is_giveaway'] else None
    return posts


def set_current_giveaway(post_id):
    post_config({'current_giveaway_id': post_id})
    return None


def get_message_record(message, giveaway_id=None):
    _file_path = get_filename(message)
    _id = message.id
    _date = message.date.isoformat()
    _edit_date = message.edit_date.isoformat() if message.edit_date is not None else None
    _sender_id = message.sender_id
    _message = message.message
    _is_reply = message.reply_to.reply_to_top_id is not None
    _is_answer = _sender_id is None and _is_reply and len(_message)
    _is_edit = _edit_date is not None
    _is_media = message.media is not None
    _is_sticker = message.sticker is not None
    _media_filename = _file_path if isinstance(_file_path, str) and os.path.exists(_file_path) else None
    _reply_id = message.reply_to_msg_id if _is_reply else None
    _answer_id = None
    _answer = None
    _is_recognized = False
    _is_reacted = False
    _is_answered = False
    _is_donate = False
    _donate = 0
    _ticket_from = 0
    _ticket_count = 0
    return {
        'id': str(_id),
        'giveaway_id': giveaway_id,
        'date': _date,
        'edit_date': _edit_date,
        'sender_id': _sender_id,
        'message': _message,
        'is_answer': _is_answer,
        'is_edit': _is_edit,
        'is_media': _is_media,
        'is_reply': _is_reply,
        'is_sticker': _is_sticker,
        'media_filename': _media_filename,
        'reply_id': _reply_id,
        'answer_id': _answer_id,
        'answer': _answer,
        'is_recognized': _is_recognized,
        'is_reacted': _is_reacted,
        'is_answered': _is_answered,
        'is_donate': _is_donate,
        'donate': _donate,
        'ticket_from': _ticket_from,
        'ticket_count': _ticket_count
    }


def get_messages(giveaway_id):
    cursor = DB.cursor()
    cursor.execute("SELECT * FROM messages WHERE giveaway_id = ? ORDER BY date ASC", (giveaway_id,))
    record = cursor.fetchall()
    if not isinstance(record, list):
        return []
    return [get_dict(r, MESSAGES_FIELDS) for r in record]


def get_one_message(id):
    cursor = DB.cursor()
    cursor.execute("SELECT * FROM messages WHERE id = ?", (id,))
    record = cursor.fetchone()
    if not record:
        return None
    return get_dict(record, MESSAGES_FIELDS)


def insert_messages(giveaway_id, messages):
    cursor = DB.cursor()
    for message in messages:
        record = ()
        for f in MESSAGES_FIELDS:
            record += (message[f],)
        cursor.execute(f'''INSERT INTO messages ({', '.join(MESSAGES_FIELDS)})
                VALUES ({', '.join(['?' for _ in MESSAGES_FIELDS])})''', record)
    DB.commit()
    cursor.fetchone()
    return get_messages(giveaway_id)


def update_message(message):
    cursor = DB.cursor()
    record = ()
    for f in MESSAGES_FIELDS:
        record += (message[f],)
    cursor.execute(f'''INSERT OR REPLACE INTO messages ({', '.join(MESSAGES_FIELDS)})
        VALUES ({', '.join(['?' for _ in MESSAGES_FIELDS])})
    ''', record)
    DB.commit()
    cursor.fetchone()
    return message


async def collect_messages(giveaway_id):
    _collected_messages = []
    giveaway = get_giveaway(giveaway_id)
    if not giveaway:
        return _collected_messages
    post_id = giveaway.get('post_id')
    if not isinstance(post_id, (str, int)):
        return _collected_messages
    old_messages = get_messages(giveaway_id)
    post_id = int(post_id)
    _last_message_id = None
    if isinstance(old_messages, list) and len(old_messages) > 0:
        _collected_messages = old_messages.copy()
        _last_message = old_messages[-1]
        _last_message_id = _last_message.get('id')
    offset_id = None
    _new_messages = []
    while True:
        _is_done = False
        replies, messages, offset_id = await telegram.get_comments_by_post_id(post_id, offset_id)
        messages = await telegram.get_media_message(messages)
        _messages = [get_message_record(m, giveaway_id) for m in messages]
        if _last_message_id is not None:
            for i, m in enumerate(_messages):
                if m['id'] == _last_message_id:
                    _messages = _messages[:i]
                    _is_done = True
                    break
        insert_messages(giveaway_id, _messages)
        if _is_done or not isinstance(messages, list) or len(messages) == 0:
            break
    return get_messages(giveaway_id)


def get_answer(template, ticket_from, ticket_count):
    _result = template
    _tickets = []
    for t in range(ticket_count):
        _tickets.append(str(t + ticket_from))
    is_few = False
    is_many = False
    _ticket_str = ''
    if len(_tickets) == 1:
        _ticket_str = f'{_tickets[0]}'
    elif 1 < len(_tickets) <= 4:
        is_few = True
        _ticket_str = ", ".join(_tickets)
    elif len(_tickets) > 4:
        is_many = True
        _ticket_str = f'від {_tickets[0]} до {_tickets[len(_tickets) - 1]}'
    else:
        return 'Дякую за донат!'
    _result = _result.replace('{%tickets}', _ticket_str)
    matches = re.findall(r'{(.*?)}', _result)
    for m in matches:
        if not isinstance(m, str):
            continue
        _m = m.split('-')
        _t = _m[1] if is_few or is_many else _m[0]
        _result = _result.replace('{' + m + '}', _t)
    return _result


def add_donate_info_into_message(message, giveaway, amount):
    _giveaway = giveaway.copy()
    _message = message.copy()
    _message['is_recognized'] = 1
    ticket_last = _giveaway['tickets_total']
    ticket_price = _giveaway['ticket_price']
    if amount:
        _message['is_donate'] = 1
        _message['donate'] = float(amount)
        _message['ticket_from'] = ticket_last + 1
        _message['ticket_count'] = round(_message['donate'] // ticket_price)
        _message['answer'] = get_answer(_giveaway.get('answer', '{%tickets}'),
                                        _message['ticket_from'], _message['ticket_count'])
        _giveaway['last_message_id'] = message.get('id')
        _giveaway['tickets_total'] += _message['ticket_count']
    _message = update_message(_message)
    _giveaway = update_giveaway(_giveaway)
    return _message, _giveaway


def recognize_message(message_id):
    message = get_one_message(message_id)
    if not message['is_media'] or not message['sender_id']:
        return None, None
    if message['is_recognized']:
        return message, None
    giveaway_id = message.get('giveaway_id')
    giveaway = get_giveaway(giveaway_id)
    try:
        parse_data = llm.parse_image(message['media_filename'])
        amount = parse_data.amount
        message, giveaway = add_donate_info_into_message(message, giveaway, amount)
        return message, giveaway
    except BaseException as _:
        return message, giveaway


def answer_message(message_id):
    message = get_one_message(message_id)
    if not message['is_media'] or not message['sender_id']:
        return None
    if not message['is_recognized'] or not message['answer']:
        return None
    try:
        answer = telegram.send_answer(message)

        return answer
    except BaseException as _:
        return None


def get_photo_as_base64(filename: str):
    try:
        with open(filename, 'rb') as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return encoded_string
    except FileNotFoundError:
        return None


if __name__ == '__main__':
    reset_db()
    # init_db()
