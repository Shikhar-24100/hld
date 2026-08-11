import time
import redis

from fastapi import FastAPI, HTTPException, Request, Depends, Response


app = FastAPI()


#one shared redis connection for the whole app
r = redis.Redis(host="localhost", port=6379, decode_responses=True)

with open("token_bucket.lua", "r", encoding="utf-8") as f:
    lua_script = f.read()

token_bucket_script = r.register_script(lua_script)


#config - hardcoded for now, (will make it flexible later on)
CAPACITY = 5
REFILL_RATE = 1


def check_rate_limit(identifier: str):
    key = f"bucket:{identifier}"
    now = time.time()

    result = token_bucket_script(
        keys=[key],
        args=[CAPACITY,REFILL_RATE,now]
    )

    allowed, tokens_remaining = result
    return bool(allowed), float(tokens_remaining)




def rate_limiter_dependency(request: Request, response: Response):
    #for now, identify clients by IP(will rectify later)
    client_ip = request.client.host
    allowed, remaining = check_rate_limit(client_ip)


    #always tell the client how many tokens are left
    response.headers["X-RateLimit-Remaining"] = str(int(remaining))
    response.headers["X-RateLimit-Limit"] = str(CAPACITY)


    if not allowed:
        retry_after = round(1/REFILL_RATE, 2);
        raise HTTPException(
            status_code = 429,
            detail="Too many requests. Slow down.",
            headers = {"Retry-After": str(retry_after)}
        )
    
    return remaining


@app.get("/ping")
def ping(remaining: float = Depends(rate_limiter_dependency)):
    return {"message": "pong", "tokens_remaining": remaining}
