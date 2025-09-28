# run with: python -m app.worker
import multiprocessing
multiprocessing.set_start_method('spawn', force=True)  # macOS fix for RQ + Twilio TTS

from rq import Worker, Queue
from redis import Redis
from .config import Config

listen = ['default']
redis_conn = Redis.from_url(Config.REDIS_URL)

if __name__ == '__main__':
    worker = Worker([Queue(name, connection=redis_conn) for name in listen])
    worker.work()
