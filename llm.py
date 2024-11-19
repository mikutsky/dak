import os
import base64
from pydantic import BaseModel
from openai import OpenAI

LLM_KEY = os.getenv('LLM_KEY')
LLM_MODEL = os.getenv('LLM_MODEL', 'gpt-4o-2024-08-06')
LLM_PROMPT = '''Analyze the image, it should be a print screen of the money transfer. You need to return JSON, 
which contains the amount without fee and time of the transfer in ISO format. If the data cannot be found, do not invent 
anything, return null in the corresponding field.'''

OPENAI_CLIENT = OpenAI(api_key=LLM_KEY)


class Response_Format(BaseModel):
    amount: int
    datetime: str


def parse_image(filename):
    with open(filename, 'rb') as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    completion = OPENAI_CLIENT.beta.chat.completions.parse(
        model=LLM_MODEL,
        messages=
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": LLM_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "low"
                            }
                        }
                    ]
                }
            ],
        response_format=Response_Format,
    )

    data = completion.choices[0].message.parsed
    return data
