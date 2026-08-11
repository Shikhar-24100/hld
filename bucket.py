import time


class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        """
        capacity: max tokens the bucket can hold
        refill_rate: tokens added per second
        """

        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity #starting-full(can change according to design require)
        self.last_refill = time.monotonic()

    
    def _refill(self):
        now = time.monotonic()
        elapsed = now - self.last_refill
        refill_amount = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + refill_amount)
        self.last_refill = now

    def allow_request(self) -> bool:
        self._refill()
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        else:
            return False

    def get_tokens(self) -> float:
        self._refill()
        return self.tokens

if __name__ == "__main__":
    bucket = TokenBucket(capacity=5, refill_rate=1)  # 5 tokens max, refills 1/sec

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