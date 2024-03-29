import os

import redis
from rq import Worker, Queue, Connection

redis_url = os.getenv('REDISCLOUD_URL', 'redis://localhost:6379')

conn = redis.from_url(redis_url)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(Queue("default", connection=conn))
        worker.work()
