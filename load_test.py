import asyncio
import httpx

URL = "http://127.0.0.1:8000/ping"
CONCURRENT_REQUESTS = 20 #fire 20 requests at the exact same time


async def make_request(client: httpx.AsyncClient, request_num: int):
    response = await client.get(URL, headers = {"X-API-Key": "localtest"})
    return request_num, response.status_code


async def main():
    async with httpx.AsyncClient() as client:
        #asyncio.gatther fires all these coroutines concurrently
        tasks = [make_request(client, i) for i in range(CONCURRENT_REQUESTS)]
        results = await asyncio.gather(*tasks)

    
    allowed = sum(1 for _, status in results if status == 200)
    denied = sum(1 for _, status in results if status == 429)

    print(f"\nTotal requests fired: {CONCURRENT_REQUESTS}")
    print(f"Allowed (200): {allowed}")
    print(f"Denied (429): {denied}")
    print(f"\nExpected allowed: 5 (free tier capacity)")

    if allowed > 5:
        print("\n⚠️  RACE CONDITION DETECTED — more requests got through than the bucket allows!")
    else:
        print("\n✅ No race condition — atomicity held.")



if __name__ == "__main__":
    asyncio.run(main())