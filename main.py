import time
import redis
import redis as redis_lib

from fastapi import FastAPI, HTTPException, Request, Depends, Response


app = FastAPI()


from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_demo():
    return FileResponse("static/index.html")


#one shared redis connection for the whole app
r = redis.Redis(host="localhost", port=6379, decode_responses=True)
r = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses = True,
    socket_connect_timeout=2, # max seconds to wait when establishing connection
    socket_timeout=2,           # max seconds to wait for a response once connected
)

with open("token_bucket.lua", "r", encoding="utf-8") as f:
    lua_script = f.read()

token_bucket_script = r.register_script(lua_script)


#config - hardcoded for now, (will make it flexible later on)
# CAPACITY = 5
# REFILL_RATE = 1

# flexed->
TIER_LIMITS = {
    "free": (5,1),
    "pro": (50, 10),
    "enterprise": (500, 100)
}

DEFAULT_TIER = "free"

def get_client_tier(request: Request) -> str:
    #in a real system this wuld look up an api-key in the db, for now
    #we fake it with a header so we can test different tiers

    tier = request.headers.get("X-Tier", DEFAULT_TIER)
    if tier not in TIER_LIMITS:
        tier = DEFAULT_TIER
    return tier


# the identifier should probably include the tier, or you get a subtle 
# bug — if the same client somehow sends different X-Tier headers across 
# requests, they'd be sharing one bucket but with inconsistent limits applied to it.
def check_rate_limit(identifier: str, tier: str, capacity: int, refill_rate: float):
    key = f"bucket:{identifier}"
    now = time.time()

    result = token_bucket_script(
        keys=[key],
        args=[capacity, refill_rate,now]
    )

    allowed, tokens_remaining = result
    return bool(allowed), float(tokens_remaining)

def get_client_identifier(request: Request) ->str:
    #prefer an api key if the client provided one
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"key:{api_key}"

    
    #fallback - back to IP -> CHECK x-fORWADED-FOR first, since a proxy
    #sit in front of real deployments and overwrites request.client.host

    forwarded_for  = request.headers.get("X-Forwarded-For")

    if forwarded_for:
        #this header can be a comma separated chain of IPs
        #the first one is the origina client

        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host
    
    return f"ip:{client_ip}"



def rate_limiter_dependency(request: Request, response: Response):
    #for now, identify clients by IP(will rectify later)
    # client_ip = request.client.host
    # allowed, remaining = check_rate_limit(client_ip)

    #rectified->
    identifier = get_client_identifier(request)
    tier = get_client_tier(request)
    
    capacity, refill_rate = TIER_LIMITS[tier]
    # allowed, remaining = check_rate_limit(identifier, tier, capacity, refill_rate)

    try:
        allowed, remaining = check_rate_limit(identifier, tier, capacity, refill_rate)
    except redis_lib.exceptions.RedisError as e:
        # Redis is unreachable or erroring — decide fail-open vs fail-closed here.
        # FAIL OPEN (current choice): let the request through, but log it loudly,
        # since silent failures here are how outages go unnoticed.
        print(f"WARNING: rate limiter Redis error, failing open: {e}")
        response.headers["X-RateLimit-Status"] = "degraded"
        return None
        # if switching from fail open to fail close use below->
        # raise HTTPException(status_code=503, detail="Rate limiter unavailable.")

    #always tell the client how many tokens are left
    response.headers["X-RateLimit-Remaining"] = str(int(remaining))
    response.headers["X-RateLimit-Limit"] = str(capacity)
    response.headers["X-RateLimit-Tier"] = tier

    if not allowed:
        retry_after = round(1/refill_rate, 2);
        raise HTTPException(
            status_code = 429,
            detail="Too many requests. Slow down.",
            headers = {"Retry-After": str(retry_after)}
        )
    return remaining

@app.get("/ping")
def ping(remaining: float = Depends(rate_limiter_dependency)):
    return {"message": "pong", "tokens_remaining": remaining}




