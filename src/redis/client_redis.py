import os

from dotenv import load_dotenv

import redis

load_dotenv()

redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST'),
    port=os.getenv('REDIS_PORT'),
    password=os.getenv('SENHA_REDIS'),
    db=0,
    decode_responses=True,
)
