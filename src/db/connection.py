import os

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()


def get_vector_conn():
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST'),
        port=os.getenv('POSTGRES_PORT'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
        dbname=os.getenv('POSTGRES_DB'),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
