import redis
import time

r_broken = redis.Redis(
    host="localhost",
    port=6390,  # nothing listens here
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)

start = time.time()
try:
    r_broken.ping()
except Exception as e:
    print(f"Failed after {time.time() - start:.1f} seconds")
    print(f"Error: {e}")