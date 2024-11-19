import os
import requests
from datetime import datetime
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

import utils
from telegram import get_posts, get_post

MONOBANK_URI = 'https://api.monobank.ua/personal'
MONOBANK_INFO_URI = f'{MONOBANK_URI}/client-info'

app = FastAPI()
app.mount("/ui", StaticFiles(directory="ui"), name="ui")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Заміни на домен твого фронтенду
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Config(BaseModel):
    post_id: str
    post_date: str = None
    post_author: str = None
    post_message: str = None
    post_img: str = None
    name: str = None
    description: str = None
    status: str = None
    interval: int = None
    start_datetime: str = None
    final_datetime: str = None
    last_comment: str = None
    ticket_price: int = None
    tickets_total: int = None
    is_active: int = None
    is_answer: int = None
    is_reaction: int = None


class PostToken(BaseModel):
    mb_token: str = None,
    mb_datetime: str = None,
    mb_current_jat: str = None,
    oa_token: str = None,
    oa_datetime: str = None,
    te_token: str = None,
    te_post_id: str = None


class GetPosts(BaseModel):
    offset: int = 0


messages = [{'id': i, 'content': f'Message {i}'} for i in range(100, 0, -1)]


@app.get("/")
async def homepage():
    return FileResponse(os.path.join('static', 'index.html'))


@app.post("/config")
async def save_config(data: Config):
    # secret = data.mb_token
    # timestamp = datetime.utcnow()
    giveaway_id = utils.get_giveaway_id({'id': data.post_id})
    response = utils.save_config(data, giveaway_id)
    return response


@app.get("/token")
async def get_token():
    response = {
        "mb_token": "*****",
        "mb_datetime": datetime.utcnow(),
        "oa_token": "*****",
        "oa_datetime": datetime.utcnow()
    }
    return response


@app.get("/jars")
async def ask_question():
    response = requests.get(MONOBANK_INFO_URI, headers={'X-Token': 'u2Q_K0AqJTBphTaVnBBGoh9XUspZhMlPJf25LoEs2hPg'})
    return response.get('jars', [])


@app.get("/posts")
async def get_messages(id: int = 0):
    response = await get_posts(id)
    posts = response[0].get('posts') if response and len(response) else None
    if posts:
        utils.add_existing_giveaways(posts)
    return JSONResponse(content=response[0])


@app.get("/current_post")
async def get_current_post():
    response = utils.get_config()
    if 'current_giveaway_id' not in response or not response['current_giveaway_id']:
        return JSONResponse(content=None)
    giveaway_id = response.get('current_giveaway_id')
    response = utils.get_giveaway(giveaway_id)
    return JSONResponse(content=response)


@app.post("/post")
async def set_current_post(id: int = 0):
    response = await get_post(id)
    response = utils.set_giveaways(response)
    utils.set_current_giveaway(response['id'])
    return JSONResponse(content=response)


@app.post("/delete/giveaway")
async def delete_giveaway(post: dict):
    _id = post.get('id')
    giveaway_id = utils.get_giveaway_id(post)
    config = utils.get_config()
    if 'current_giveaway_id' in config and config['current_giveaway_id'] == giveaway_id:
        utils.post_config({'current_giveaway_id': None})
    utils.delete_giveaways(utils.get_giveaway_id(post))
    post = post.copy()
    post['is_giveaway'] = False
    post['status'] = None
    response = {
        'post': post,
        'selected_post': None
    }
    config = utils.get_config()
    if 'current_giveaway_id' in config and config['current_giveaway_id']:
        giveaway_id = config.get('current_giveaway_id')
        giveaway = utils.get_giveaway(giveaway_id)
        response['selected_post'] = giveaway
    return JSONResponse(content=response)


@app.get('/messages')
async def get_message(giveawayid: str = None):
    if giveawayid is None:
        return JSONResponse(content={'messages': []})
    _messages = await utils.collect_messages(giveawayid)
    return JSONResponse(content={'messages': _messages})


@app.get('/photo')
async def get_photo(filename: str = None):
    if filename is None:
        return JSONResponse(content={'photo': None})
    img_base64 = utils.get_photo_as_base64(filename)
    return JSONResponse(content={'photo':  f"data:image/jpeg;base64,{img_base64}"})


@app.get('/recognize')
async def get_recognize(id: str = None):
    if id is None:
        return JSONResponse(content={'message': None})
    message, giveaway = utils.recognize_message(id)
    return JSONResponse(content={'giveaway': giveaway, 'message': message})


@app.get('/answer')
async def get_answer(id: str = None):
    if id is None:
        return JSONResponse(content={'answer': None})
    answer = utils.recognize_message(id)
    return JSONResponse(content={'answer': answer})


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8989)
    # encoded_value = Fernet.generate_key()
    # key = encoded_value.decode()
    # key = key.encode()
    # print(key)
