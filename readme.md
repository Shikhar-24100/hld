# Distributed Rate Limiter — Redis + Lua + FastAPI
 
A token bucket rate limiter that works correctly across multiple app
instances, using Redis for shared state and a Lua script for atomic
check-and-decrement operations.
 
**Live demo:** [https://nanosentry.onrender.com/]
 
## Why this stack
 
A rate limiter needs shared state. If each server instance tracked
request counts in memory, a client could get a fresh limit on every
server they happen to land on, and the limit would mean nothing.
Redis solves that by giving every instance one shared source of truth.
 
Sharing state introduces a race condition though. Checking "does this
client have tokens left?" and then decrementing the count are two
separate operations. If two requests run that check at the same
moment, both can see available tokens and both get approved, even
though the bucket only actually had one token left. Redis runs Lua
scripts atomically, as a single uninterruptible unit, so the whole
check-and-decrement happens without any other command able to slip
in the middle. That's the entire reason Lua is in this stack — not
performance, atomicity.
 
FastAPI is where the limiter gets wired into actual HTTP endpoints,
as a reusable dependency.
 
## How it works
 
1. A request hits a FastAPI endpoint that depends on the rate limiter.
2. The dependency identifies the client, by API key if present,
   falling back to IP address.
3. It calls a Lua script on Redis, passing the bucket key, capacity,
   refill rate, and current timestamp.
4. The script reads the bucket's current token count and last-refill
   timestamp, calculates how many tokens should have refilled since
   then based on elapsed time, and decides whether to allow the
   request — all as one atomic operation.
5. FastAPI returns the response, or a 429 with `Retry-After` and
   `X-RateLimit-*` headers if the bucket is empty.
If Redis is unreachable, the limiter fails open: requests are let
through rather than the whole API going down, with a header flagging
the degraded state so it's visible in monitoring.
 
## Tiers
 
Tier is looked up server-side from the API key, not accepted as a
client-supplied header — letting clients declare their own tier would
make the whole limiter trivially bypassable.
 
| Tier | Capacity | Refill rate |
|---|---|---|
| free | 5 | 1/sec |
| pro | 50 | 10/sec |
| enterprise | 500 | 100/sec |
 
## Running locally
 
```bash
# start redis
docker run -d --name redis-ratelimit -p 6379:6379 redis:latest
 
# set up the app
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
 
# run it
uvicorn main:app --reload
```
 
Then open `http://127.0.0.1:8000/` for the interactive demo, or
`http://127.0.0.1:8000/docs` for the API docs.
 
## Testing atomicity under load
 
```bash
python load_test.py
```
 
Fires 20 concurrent requests at a 5-token bucket and confirms exactly
5 get through, proving the Lua script prevents the race condition
described above.
 
## Known limitations
 
- Single Redis instance is a single point of failure. Production
  systems would use Redis Sentinel or Cluster for high availability.
- Timestamps come from the app server's clock, not Redis's own `TIME`
  command, so multi-region deployments with clock skew could see
  slightly inconsistent refill calculations.
- Token bucket allows a client to burst through their entire capacity
  instantly, then go silent, then burst again. A sliding-window
  algorithm would enforce smoother, more even limits, at the cost of
  more complexity.
- If Redis restarts, the Lua script cache is cleared, and calls using
  `EVALSHA` will briefly fail until the script is reloaded.
## Stack
 
Python, FastAPI, Redis, Lua (via `EVAL`/`EVALSHA`), `redis-py`, `httpx`
for load testing.
 
