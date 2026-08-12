import time
from bucket import TokenBucket

if __name__ == "__main__":
    bucket = TokenBucket(capacity=5, refill_rate=1)  # 5tokens max, refills 1/sec

    # fire 7 requests instantly — expect first 5 to pass, next 2 to fail
    for i in range(7):
        result = bucket.allow_request()
        print(f"Request {i+1}: {'ALLOWED' if result else 'DENIED'}")

    print("\nWaiting 3 seconds for refill...\n")
    time.sleep(3)

    # bucket should have ~3 tokens now
    for i in range(4):
        result = bucket.allow_request()
        print(f"Request {i+1}: {'ALLOWED' if result else 'DENIED'}")