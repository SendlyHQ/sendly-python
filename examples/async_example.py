"""
Example: Async Client Usage

Run with: python examples/async_example.py
"""

import asyncio
import os

from sendly import SANDBOX_TEST_NUMBERS, AsyncSendly


async def main():
    # Initialize async client
    api_key = os.environ.get("SENDLY_API_KEY", "sk_test_v1_xxx")

    async with AsyncSendly(api_key) as client:
        print(f"Running in {'TEST' if client.is_test_mode() else 'LIVE'} mode\n")

        # Example 1: Send multiple messages concurrently
        print("1. Sending multiple messages concurrently...")

        tasks = [
            client.messages.send(
                to=SANDBOX_TEST_NUMBERS.SUCCESS, text=f"Concurrent message #{i + 1}"
            )
            for i in range(3)
        ]

        messages = await asyncio.gather(*tasks)

        for msg in messages:
            print(f"   Sent: {msg.id} - {msg.status}")
        print()

        # Example 2: Send and immediately check status
        print("2. Send and list messages...")

        await client.messages.send(to=SANDBOX_TEST_NUMBERS.SUCCESS, text="Async test message")

        result = await client.messages.list(limit=5)
        print(f"   Found {result.count} recent messages:")
        for msg in result.data[:3]:
            print(f"   - {msg.to}: {msg.status}")
        print()

        # Example 3: Get specific message
        print("3. Get message details...")
        if result.data:
            msg = await client.messages.get(result.data[0].id)
            print(f"   ID: {msg.id}")
            print(f"   Status: {msg.status}")
            print(f"   Created: {msg.created_at}")

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
