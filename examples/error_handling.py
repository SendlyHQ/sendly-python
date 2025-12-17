"""
Example: Error Handling

Run with: python examples/error_handling.py
"""

import os
import time

from sendly import (
    SANDBOX_TEST_NUMBERS,
    AuthenticationError,
    InsufficientCreditsError,
    NotFoundError,
    RateLimitError,
    Sendly,
    SendlyError,
    ValidationError,
)


def main():
    api_key = os.environ.get("SENDLY_API_KEY", "sk_test_v1_xxx")
    client = Sendly(api_key)

    # Example 1: Comprehensive error handling
    print("1. Comprehensive error handling:\n")

    try:
        client.messages.send(
            to=SANDBOX_TEST_NUMBERS.INVALID,  # This will fail
            text="Test message",
        )
    except AuthenticationError as e:
        print("   Authentication Error:")
        print(f"   Code: {e.code}")
        print(f"   Message: {e.message}")
        print("   Action: Check your API key\n")
    except RateLimitError as e:
        print("   Rate Limit Error:")
        print(f"   Message: {e.message}")
        print(f"   Retry after: {e.retry_after} seconds")
        print("   Action: Wait and retry\n")
    except InsufficientCreditsError as e:
        print("   Insufficient Credits Error:")
        print(f"   Credits needed: {e.credits_needed}")
        print(f"   Current balance: {e.current_balance}")
        print("   Action: Purchase more credits\n")
    except ValidationError as e:
        print("   Validation Error:")
        print(f"   Code: {e.code}")
        print(f"   Message: {e.message}")
        print("   Action: Fix the request\n")
    except NotFoundError as e:
        print("   Not Found Error:")
        print(f"   Message: {e.message}")
        print("   Action: Check the resource ID\n")
    except SendlyError as e:
        print("   Sendly Error:")
        print(f"   Code: {e.code}")
        print(f"   Status: {e.status_code}")
        print(f"   Message: {e.message}\n")

    # Example 2: Simple error code check
    print("2. Simple error code check:\n")

    try:
        client.messages.send(
            to="+invalid",
            text="Test",
        )
    except SendlyError as e:
        if e.code == "invalid_request":
            print("   Bad request - check your input")
        elif e.code in ("unauthorized", "invalid_api_key"):
            print("   Authentication failed")
        elif e.code == "insufficient_credits":
            print("   Need more credits")
        elif e.code == "rate_limit_exceeded":
            print("   Slow down!")
        else:
            print(f"   Error: {e.code}")
    print()

    # Example 3: Retry with backoff
    print("3. Retry with backoff (rate limit):\n")

    def send_with_retry(to: str, text: str, max_retries: int = 3):
        for attempt in range(1, max_retries + 1):
            try:
                message = client.messages.send(to=to, text=text)
                print(f"   Success on attempt {attempt}: {message.id}")
                return message
            except RateLimitError as e:
                if attempt < max_retries:
                    print(f"   Rate limited, waiting {e.retry_after}s...")
                    time.sleep(e.retry_after)
                else:
                    raise
        return None

    try:
        send_with_retry(SANDBOX_TEST_NUMBERS.SUCCESS, "Hello!")
    except Exception as e:
        print(f"   Failed after retries: {e}")

    # Clean up
    client.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
