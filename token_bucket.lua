
-- if we did "read tokens" then "write tokens" as two separate Python-to-Redis calls, another request could sneak in between them.
-- Two requests could both read "3 tokens left," both decide to allow, both decrement — and now you've let through a request that 
-- shouldn't have been allowed. That's a race condition. Lua scripts run atomically in Redis — the whole thing executes as one 
-- uninterruptible block. Nothing else touches that key while it's running.



-- KEYS[1] = the bucket's Redis key, e.g. "bucket:user123"
-- ARGV[1] = capacity (max tokens)
-- ARGV[2] = refill_rate (tokens per second)
-- ARGV[3] = current timestamp (seconds, as a float)


local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])


--READ EXISTING STATE
local bucket = redis.call("HMGET", key, "tokens", "last_refill")
local tokens = tonumber(bucket[1])
local last_refill = tonumber(bucket[2])


--if bucket doesn exist yet, start full
if tokens == nil then
    tokens = capacity
    last_refill = now
end



--calcuate refill based onn elapsed time
local elapsed = math.max(0, now-last_refill)
local refill_amount = elapsed * refill_rate
tokens = math.min(capacity, tokens + refill_amount)


--decide: allow or deny
local allowed = 0
if tokens >= 1 then
    tokens = tokens - 1
    allowed = 1
end


--write updated state back
redis.call("HMSET", key, "tokens", tokens, "last_refill", now)


--let the key epire if unused for a while so we dont leak memory forever
redis.call("EXPIRE", key, 3600)

return {allowed, tokens}
