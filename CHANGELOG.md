# sendly (Python)

## 3.33.0

### Patch Changes

- **Fixed a runtime `TypeError` on every write method across `contacts`, `campaigns`, `templates`, and `webhooks`.** Those resources called the internal HTTP client with a `json=` keyword, but `HttpClient.request()` / `AsyncHttpClient.request()` only accept `body=`. Every affected call site now passes `body=`, so creates/updates (e.g. `contacts.import_contacts`, `contacts.lookup`, `contacts.bulk_mark_valid`, `campaigns.create`, `templates.create`, `webhooks.create`) send their payloads correctly instead of raising.
- Reconciled the version to a single source of truth at `3.33.0`: `pyproject.toml`, `sendly.__version__`, and the `User-Agent` header (`SDK_VERSION` in `utils/http.py`, previously `1.0.5`) now all report `sendly-python/3.33.0`.

## 3.32.0

### Minor Changes

- New `business_upgrade` resource on `Sendly` / `AsyncSendly` — manages the toll-free entity-upgrade ("fork-with-new-number") flow. When a customer forms a new legal entity (e.g. an LLC), reserve a new toll-free number under that entity, submit it for carrier review, and atomically swap to it on approval. Outbound SMS keeps flowing through the old number during the 1-2 week review window.
- Seven methods, mirroring the Node SDK's `BusinessUpgradeResource`:
  - `preflight(**fields)` — advisory validation, no writes; returns issues + proposed auto-fixes.
  - `best_prefill()` — pull the most-recent non-empty messaging fields across the caller's verified workspaces.
  - `start(workspace_id, *, ein_doc=None, **fields)` — provision a new TFN + messaging profile and submit to the carrier. Multipart upload for the IRS confirmation letter.
  - `status(workspace_id)` — `{"pending": ...}` or `{"pending": None}`.
  - `cancel(workspace_id)` — idempotent release of the reserved number + stored EIN doc.
  - `resubmit(workspace_id, *, ein_doc=None, **fields)` — partial update for rejected / waiting-for-customer pendings.
  - `set_disposition(workspace_id, *, disposition, target_workspace_id=None)` — `"moved"` or `"released"` after approval.
- `ein_doc` accepts `bytes`, `(filename, bytes)`, `(filename, bytes, content_type)`, or a `{"buffer": bytes, "filename": str, "content_type": str}` dict — pick whichever feels natural for your call site.
- Field names use Python snake_case (`business_name`, `brn_type`, `entity_type`, ...); the SDK translates to the API's camelCase shape before sending.

## 3.31.0

### Patch Changes

- Version bump for unified release. No Python SDK code changes — this release exists for parity with sibling SDKs that shipped fixes in this cycle (PHP doc/code mismatch, Ruby positional constructor, Rust + Java added `suggest_replies` / `suggestReplies`).

## 3.30.0

### Minor Changes

- `enterprise.workspaces.submit_verification(workspace_id, **fields)`: rewritten to match the actual API shape (camelCase top-level, nested `address`/`contact` objects, `entityType` + `brn`/`brnType`/`brnCountry` instead of `business_type`/`ein`). The previous shape didn't match the server endpoint.
- **Partial-update friendly:** for resubmits on existing workspaces, send only the fields you want to change — everything else is filled from the existing record. Hosted page URLs (`/biz/`, `/opt-in/`, `/legal/`) generated during provision are auto-preserved.
- `enterprise.workspaces.resubmit_verification(workspace_id, **partial_updates)`: convenience alias for resubmits — same as `submit_verification` but reads more naturally for one-field-change use cases.
- Accepts either a `data` dict or kwargs for ergonomic use.

### Server-side fixes paired with this release

- `/api/v1/enterprise/workspaces/:id/verification/submit` now returns specific missing-field errors (e.g. `"Missing required fields: website"`) instead of listing every required field.
- Endpoint accepts both flat and `{"verification": {...}}` wrapped shapes (matches `/enterprise/provision`).
- `useCase` validation expanded from 23 entries to the full 43-value Telnyx enum.

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
