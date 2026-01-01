# sendly

Official Python SDK for the [Sendly](https://sendly.live) SMS API.

## Installation

```bash
# pip
pip install sendly

# poetry
poetry add sendly

# pipenv
pipenv install sendly
```

## Requirements

- Python 3.8+
- A Sendly API key ([get one here](https://sendly.live/dashboard))

## Quick Start

```python
from sendly import Sendly

# Initialize with your API key
client = Sendly('sk_live_v1_your_api_key')

# Send an SMS
message = client.messages.send(
    to='+15551234567',
    text='Hello from Sendly!'
)

print(f'Message sent: {message.id}')
print(f'Status: {message.status}')
```

## Prerequisites for Live Messaging

Before sending live SMS messages, you need:

1. **Business Verification** - Complete verification in the [Sendly dashboard](https://sendly.live/dashboard)
   - **International**: Instant approval (just provide Sender ID)
   - **US/Canada**: Requires carrier approval (3-7 business days)

2. **Credits** - Add credits to your account
   - Test keys (`sk_test_*`) work without credits (sandbox mode)
   - Live keys (`sk_live_*`) require credits for each message

3. **Live API Key** - Generate after verification + credits
   - Dashboard → API Keys → Create Live Key

### Test vs Live Keys

| Key Type | Prefix | Credits Required | Verification Required | Use Case |
|----------|--------|------------------|----------------------|----------|
| Test | `sk_test_v1_*` | No | No | Development, testing |
| Live | `sk_live_v1_*` | Yes | Yes | Production messaging |

> **Note**: You can start development immediately with a test key. Messages to sandbox test numbers are free and don't require verification.

## Features

- ✅ Full type hints (PEP 484)
- ✅ Sync and async clients
- ✅ Automatic retries with exponential backoff
- ✅ Rate limit handling
- ✅ Pydantic models for data validation
- ✅ Python 3.8+ support

## Usage

### Sending Messages

```python
from sendly import Sendly

client = Sendly('sk_live_v1_xxx')

# Basic usage (marketing message - default)
message = client.messages.send(
    to='+15551234567',
    text='Check out our new features!'
)

# Transactional message (bypasses quiet hours)
message = client.messages.send(
    to='+15551234567',
    text='Your verification code is: 123456',
    message_type='transactional'
)

# With custom sender ID (international)
message = client.messages.send(
    to='+447700900123',
    text='Hello from MyApp!',
    from_='MYAPP'
)
```

### Listing Messages

```python
# Get recent messages (default limit: 50)
result = client.messages.list()
print(f'Found {result.count} messages')

# Get last 10 messages
result = client.messages.list(limit=10)

# Iterate through messages
for msg in result.data:
    print(f'{msg.to}: {msg.status}')
```

### Getting a Message

```python
message = client.messages.get('msg_xxx')

print(f'Status: {message.status}')
print(f'Delivered: {message.delivered_at}')
```

### Scheduling Messages

```python
# Schedule a message for future delivery
scheduled = client.messages.schedule(
    to='+15551234567',
    text='Your appointment is tomorrow!',
    scheduled_at='2025-01-15T10:00:00Z'
)

print(f'Scheduled: {scheduled.id}')
print(f'Will send at: {scheduled.scheduled_at}')

# List scheduled messages
result = client.messages.list_scheduled()
for msg in result.data:
    print(f'{msg.id}: {msg.scheduled_at}')

# Get a specific scheduled message
msg = client.messages.get_scheduled('sched_xxx')

# Cancel a scheduled message (refunds credits)
result = client.messages.cancel_scheduled('sched_xxx')
print(f'Refunded: {result.credits_refunded} credits')
```

### Batch Messages

```python
# Send multiple messages in one API call (up to 1000)
batch = client.messages.send_batch(
    messages=[
        {'to': '+15551234567', 'text': 'Hello User 1!'},
        {'to': '+15559876543', 'text': 'Hello User 2!'},
        {'to': '+15551112222', 'text': 'Hello User 3!'}
    ]
)

print(f'Batch ID: {batch.batch_id}')
print(f'Queued: {batch.queued}')
print(f'Failed: {batch.failed}')
print(f'Credits used: {batch.credits_used}')

# Get batch status
status = client.messages.get_batch('batch_xxx')

# List all batches
result = client.messages.list_batches()
```

### Rate Limit Information

```python
# After any API call, check rate limit status
client.messages.send(to='+1555...', text='Hello!')

rate_limit = client.get_rate_limit_info()
if rate_limit:
    print(f'{rate_limit.remaining}/{rate_limit.limit} requests remaining')
    print(f'Resets in {rate_limit.reset} seconds')
```

## Async Client

For async/await support, use `AsyncSendly`:

```python
import asyncio
from sendly import AsyncSendly

async def main():
    async with AsyncSendly('sk_live_v1_xxx') as client:
        # Send a message
        message = await client.messages.send(
            to='+15551234567',
            text='Hello from async!'
        )
        print(message.id)

        # List messages
        result = await client.messages.list(limit=10)
        for msg in result.data:
            print(f'{msg.to}: {msg.status}')

asyncio.run(main())
```

## Configuration

```python
from sendly import Sendly, SendlyConfig

# Using keyword arguments
client = Sendly(
    api_key='sk_live_v1_xxx',
    base_url='https://sendly.live/api/v1',  # Optional
    timeout=60.0,  # Optional: seconds (default: 30)
    max_retries=5  # Optional: (default: 3)
)

# Using config object
config = SendlyConfig(
    api_key='sk_live_v1_xxx',
    timeout=60.0,
    max_retries=5
)
client = Sendly(config=config)
```

## Webhooks

Manage webhook endpoints to receive real-time delivery status updates.

```python
# Create a webhook endpoint
webhook = client.webhooks.create(
    url='https://example.com/webhooks/sendly',
    events=['message.delivered', 'message.failed']
)

print(f'Webhook ID: {webhook.id}')
print(f'Secret: {webhook.secret}')  # Store this securely!

# List all webhooks
webhooks = client.webhooks.list()

# Get a specific webhook
wh = client.webhooks.get('whk_xxx')

# Update a webhook
client.webhooks.update('whk_xxx',
    url='https://new-endpoint.example.com/webhook',
    events=['message.delivered', 'message.failed', 'message.sent']
)

# Test a webhook (sends a test event)
result = client.webhooks.test('whk_xxx')
print(f'Test {"passed" if result.success else "failed"}')

# Rotate webhook secret
rotation = client.webhooks.rotate_secret('whk_xxx')
print(f'New secret: {rotation.secret}')

# View delivery history
deliveries = client.webhooks.get_deliveries('whk_xxx')

# Retry a failed delivery
client.webhooks.retry_delivery('whk_xxx', 'del_yyy')

# Delete a webhook
client.webhooks.delete('whk_xxx')
```

### Verifying Webhook Signatures

```python
from sendly import Webhooks

webhooks = Webhooks('your_webhook_secret')

# In your webhook handler (Flask example)
@app.route('/webhooks/sendly', methods=['POST'])
def handle_webhook():
    signature = request.headers.get('X-Sendly-Signature')
    payload = request.get_data(as_text=True)

    try:
        event = webhooks.verify_and_parse(payload, signature)
        
        if event.type == 'message.delivered':
            print(f'Message {event.data.id} delivered')
        elif event.type == 'message.failed':
            print(f'Message {event.data.id} failed: {event.data.error_code}')
        
        return 'OK', 200
    except Exception as e:
        print(f'Invalid signature: {e}')
        return 'Invalid signature', 400
```

## Account & Credits

```python
# Get account information
account = client.account.get()
print(f'Email: {account.email}')

# Check credit balance
credits = client.account.get_credits()
print(f'Available: {credits.available_balance} credits')
print(f'Reserved (scheduled): {credits.reserved_balance} credits')
print(f'Total: {credits.balance} credits')

# View credit transaction history
result = client.account.get_credit_transactions()
for tx in result.data:
    print(f'{tx.type}: {tx.amount} credits - {tx.description}')

# List API keys
result = client.account.list_api_keys()
for key in result.data:
    print(f'{key.name}: {key.prefix}*** ({key.type})')

# Get API key usage stats
usage = client.account.get_api_key_usage('key_xxx')
print(f'Messages sent: {usage.messages_sent}')
print(f'Credits used: {usage.credits_used}')
```

## Error Handling

The SDK provides typed exception classes:

```python
from sendly import (
    Sendly,
    SendlyError,
    AuthenticationError,
    RateLimitError,
    InsufficientCreditsError,
    ValidationError,
    NotFoundError,
)

client = Sendly('sk_live_v1_xxx')

try:
    message = client.messages.send(
        to='+15551234567',
        text='Hello!'
    )
except AuthenticationError as e:
    print(f'Invalid API key: {e.message}')
except RateLimitError as e:
    print(f'Rate limited. Retry after {e.retry_after} seconds')
except InsufficientCreditsError as e:
    print(f'Need {e.credits_needed} credits, have {e.current_balance}')
except ValidationError as e:
    print(f'Invalid request: {e.message}')
except NotFoundError as e:
    print(f'Resource not found: {e.message}')
except SendlyError as e:
    print(f'API error [{e.code}]: {e.message}')
```

## Testing (Sandbox Mode)

Use a test API key (`sk_test_v1_xxx`) for testing:

```python
from sendly import Sendly, SANDBOX_TEST_NUMBERS

client = Sendly('sk_test_v1_xxx')

# Check if in test mode
print(client.is_test_mode())  # True

# Use sandbox test numbers
message = client.messages.send(
    to=SANDBOX_TEST_NUMBERS.SUCCESS,  # +15005550000
    text='Test message'
)

# Test error scenarios
message = client.messages.send(
    to=SANDBOX_TEST_NUMBERS.INVALID,  # +15005550001
    text='This will fail'
)
```

### Available Test Numbers

| Number | Behavior |
|--------|----------|
| `+15005550000` | Success (instant) |
| `+15005550001` | Fails: invalid_number |
| `+15005550002` | Fails: unroutable_destination |
| `+15005550003` | Fails: queue_full |
| `+15005550004` | Fails: rate_limit_exceeded |
| `+15005550006` | Fails: carrier_violation |

## Pricing Tiers

```python
from sendly import CREDITS_PER_SMS, SUPPORTED_COUNTRIES, PricingTier

# Credits per SMS by tier
print(CREDITS_PER_SMS[PricingTier.DOMESTIC])  # 1 (US/Canada)
print(CREDITS_PER_SMS[PricingTier.TIER1])     # 8 (UK, Poland, etc.)
print(CREDITS_PER_SMS[PricingTier.TIER2])     # 12 (France, Japan, etc.)
print(CREDITS_PER_SMS[PricingTier.TIER3])     # 16 (Germany, Italy, etc.)

# Supported countries by tier
print(SUPPORTED_COUNTRIES[PricingTier.DOMESTIC])  # ['US', 'CA']
print(SUPPORTED_COUNTRIES[PricingTier.TIER1])     # ['GB', 'PL', ...]
```

## Utilities

The SDK exports validation utilities:

```python
from sendly import (
    validate_phone_number,
    get_country_from_phone,
    is_country_supported,
    calculate_segments,
)

# Validate phone number format
validate_phone_number('+15551234567')  # OK
validate_phone_number('555-1234')  # Raises ValidationError

# Get country from phone number
get_country_from_phone('+447700900123')  # 'GB'
get_country_from_phone('+15551234567')   # 'US'

# Check if country is supported
is_country_supported('GB')  # True
is_country_supported('XX')  # False

# Calculate SMS segments
calculate_segments('Hello!')  # 1
calculate_segments('A' * 200)  # 2
```

## Type Hints

The SDK is fully typed. Import types for your IDE:

```python
from sendly import (
    SendlyConfig,
    SendMessageRequest,
    Message,
    MessageStatus,
    ListMessagesOptions,
    MessageListResponse,
    RateLimitInfo,
    PricingTier,
)
```

## Context Manager

Both sync and async clients support context managers:

```python
# Sync
with Sendly('sk_live_v1_xxx') as client:
    message = client.messages.send(to='+1555...', text='Hello!')

# Async
async with AsyncSendly('sk_live_v1_xxx') as client:
    message = await client.messages.send(to='+1555...', text='Hello!')
```

## API Reference

### `Sendly` / `AsyncSendly`

#### Constructor

```python
Sendly(
    api_key: str,
    base_url: str = 'https://sendly.live/api/v1',
    timeout: float = 30.0,
    max_retries: int = 3,
)
```

#### Properties

- `messages` - Messages resource
- `base_url` - Configured base URL

#### Methods

- `is_test_mode()` - Returns `True` if using a test API key
- `get_rate_limit_info()` - Returns current rate limit info
- `close()` - Close the HTTP client

### `client.messages`

#### `send(to, text, from_=None) -> Message`

Send an SMS message.

#### `list(limit=None) -> MessageListResponse`

List sent messages.

#### `get(id) -> Message`

Get a specific message by ID.

## Support

- 📚 [Documentation](https://sendly.live/docs)
- 💬 [Discord](https://discord.gg/sendly)
- 📧 [support@sendly.live](mailto:support@sendly.live)

## License

MIT
