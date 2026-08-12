import redis


r = redis.Redis(host='localhost', port=6379, decode_responses=True)
#decode_responses = true means that the responses from Redis will be returned as strings instead of bytes


#connectivity check
print("Ping", r.ping())  # should return True if Redis is running


#set/get 
r.set("greeting", "hellow world")
print("Get:", r.get("greeting"))


#expire - set a TTL on a key (in seconds)
r.set("temp_key", "I will expire in 5 seconds", ex = 5)
print("ttl on temp_key:" ,r.ttl("temp_key"))  # should return 5


#HASH(waht we'll use for buckets)
#lets us store multiple fields under one key, like a dictionary
r.hset("bucket:user123", mapping={"tokens": 5, "last_refill" : "1234567890"})
print("hash contents", r.hgetall("bucket:user123"))


#cleanup
r.delete("greeting", "temp_key", "bucket:user123")
print("cleanup done, keys deleted")