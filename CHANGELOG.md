# sendly (Python)

## 3.29.0

### Minor Changes

- `contacts.bulk_mark_valid(ids=..., list_id=...)` / async equivalent: clear the invalid flag on many contacts at once (up to 10,000 per call).
- `WebhookEventType` enum gains four list-health values: `CONTACT_AUTO_FLAGGED`, `CONTACT_MARKED_VALID`, `CONTACTS_LOOKUP_COMPLETED`, `CONTACTS_BULK_MARKED_VALID`. Also adds the missing `MESSAGE_RECEIVED`, `MESSAGE_OPT_OUT`, `MESSAGE_OPT_IN`.
- New `ListHealthEventSource` enum (frozen): `SEND_FAILURE | CARRIER_LOOKUP | USER_ACTION | BULK_MARK_VALID`.
- `Contact` gains `user_marked_valid_at` — when a user manually cleared an auto-flag. Respected by future carrier re-checks.
- `check_numbers()` response carries `already_running` / `alreadyRunning` when a rapid re-trigger was collapsed against an in-flight lookup.

## 3.28.0

### Minor Changes

- `contacts.mark_valid(contact_id)` / async equivalent: clear the auto-exclusion flag on a contact.
- `contacts.check_numbers(list_id=None, force=False)` / async equivalent: trigger a background carrier lookup.
- `Contact` model gains `line_type`, `carrier_name`, `line_type_checked_at`, `invalid_reason`, `invalidated_at`.

## 3.18.1

### Patch Changes

- fix: webhook signature verification and payload parsing now match server implementation
  - `verify_signature()` accepts optional `timestamp` parameter for HMAC on `timestamp.payload` format
  - `parse_event()` handles `data.object` nesting (with flat `data` fallback for backwards compat)
  - `WebhookEvent` adds `livemode` field, `created` as union type (int or string)
  - `WebhookMessageData` renamed `message_id` to `id` (with `message_id` property alias)
  - Added `direction`, `organization_id`, `text`, `message_format`, `media_urls` fields
  - `generate_signature()` accepts optional `timestamp` parameter
  - 5-minute timestamp tolerance check prevents replay attacks

## 3.18.0

### Minor Changes

- Add MMS support for US/CA domestic messaging
- Add `media_urls` parameter on `messages.send()` for sending MMS

## 3.17.0

### Minor Changes

- Add structured error classification and automatic message retry
- New `error_code` field with 13 structured codes (E001-E013, E099)
- New `retry_count` field tracks retry attempts
- New `retrying` status and `message.retrying` webhook event

## 3.16.0

### Minor Changes

- Add `transfer_credits()` for moving credits between workspaces

## 3.15.2

### Patch Changes

- Add metadata support to batch message items and request/response types

## 3.13.0

### Minor Changes

- Campaigns, Contacts & Contact Lists resources with full CRUD
- Template clone method
