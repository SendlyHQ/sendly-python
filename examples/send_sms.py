"""
Example: Sending SMS Messages

Run with: python examples/send_sms.py
"""

import os

from sendly import SANDBOX_TEST_NUMBERS, Sendly


def main():
    # Initialize client with your API key
    api_key = os.environ.get("SENDLY_API_KEY", "sk_test_v1_xxx")
    client = Sendly(api_key)

    print(f"Running in {'TEST' if client.is_test_mode() else 'LIVE'} mode\n")

    # Example 1: Basic SMS
    print("1. Sending basic SMS...")
    message = client.messages.send(
        to=SANDBOX_TEST_NUMBERS.SUCCESS,
        text="Hello from Sendly! This is a test message.",
    )
    print(f"   Message ID: {message.id}")
    print(f"   Status: {message.status}")
    print(f"   Segments: {message.segments}")
    print(f"   Credits Used: {message.credits_used}\n")

    # Example 2: SMS with custom sender ID
    print("2. Sending SMS with custom sender ID...")
    message = client.messages.send(
        to=SANDBOX_TEST_NUMBERS.SUCCESS,
        text="Your verification code is: 123456",
        from_="MYAPP",
    )
    print(f"   Message ID: {message.id}")
    print(f"   From: {message.from_}\n")

    # Example 3: Long message (multi-segment)
    print("3. Sending long message (multi-segment)...")
    long_text = "This is a longer message that will be split into multiple segments. " * 5
    message = client.messages.send(
        to=SANDBOX_TEST_NUMBERS.SUCCESS,
        text=long_text,
    )
    print(f"   Message ID: {message.id}")
    print(f"   Text length: {len(long_text)} characters")
    print(f"   Segments: {message.segments}\n")

    # Example 4: Check rate limit info
    print("4. Rate limit info:")
    rate_limit = client.get_rate_limit_info()
    if rate_limit:
        print(f"   Limit: {rate_limit.limit} requests/minute")
        print(f"   Remaining: {rate_limit.remaining}")
        print(f"   Resets in: {rate_limit.reset} seconds\n")

    # Clean up
    client.close()
    print("Done!")


if __name__ == "__main__":
    main()
