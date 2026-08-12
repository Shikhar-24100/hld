import redis
import time

r = redis.Redis(host="localhost", port = 6379, decode_responses = True)


#load lua's file contents
with open("token_bucket.lua", "r", encoding="utf-8") as f:
    lua_script = f.read()


#regiter it->this return a callable script object
#under the hood, redis-py uses SCRIPT LOAD + EVALSHA so the----
#script text isnt resent over the wire on every call

token_bucket_script = r.register_script(lua_script)

def check_rate_limit(user_id: str, capacity: int, refill_rate: float):
    key = f"bucket:{user_id}"
    now = time.time()

    result = token_bucket_script(
        keys=[key],
        args=[capacity, refill_rate, now]
    )


    allowed, tokens_remaining = result
    return bool(allowed), float(tokens_remaining)



if __name__ == "__main__":
    # clean slate
    r.delete("bucket:pyuser")

    for i in range(7):
        allowed, remaining = check_rate_limit("pyuser", capacity=5, refill_rate=1)
        print(f"Request {i+1}: {'ALLOWED' if allowed else 'DENIED'} (tokens left: {remaining:.2f})")