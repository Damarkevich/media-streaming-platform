import time

from redis import Redis

from tests.functional.settings import test_settings

REDIS_HOST = test_settings.redis_host
REDIS_PORT = test_settings.redis_port

if __name__ == "__main__":
    redis_client = Redis(host=REDIS_HOST, port=REDIS_PORT)
    while True:
        try:
            if redis_client.ping():
                break
        except Exception:
            pass
        print("Waiting for Redis to be available...")
        time.sleep(1)
