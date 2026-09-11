# sendly (Python)

## 4.0.0

**Upgrading from 3.40.0:** that release already contained the breaking changes below, published by mistake as a minor version. 4.0.0 carries them under the correct major. Relative to 3.40.0, the only new changes are under **Security**.

Webhook events are no longer decoded as messages. Every SDK used to force a webhook's
`data.object` into a message-shaped type. That is correct for `message.*` and wrong for
every lifecycle event — `rcs_*`, `whatsapp_*`, `call.*`, `brand.*`, `campaign.*`,
`assignment.*`, `number.*`, `port*`, `contact*`, `conversation.*`, `draft.*`,
`verification.*` — which carry a different object entirely. This release exposes the payload
as it arrived and makes the wrong read fail instead of returning a plausible-looking zero.

### Breaking Changes

- **`event.data` is now `None` for every event that is not a `message.*` event.** It used to
  be a fully-populated `WebhookMessageData` whatever arrived, assembled by reading message
  field names off a payload that never carried them. Parsing an `rcs_agent.live` event
  returned `id=''`, `status=''`, `to=''`, `from_=''`, `segments=1`, `credits_used=0`,
  `direction='outbound'` — every one of those invented by the SDK — and **raised no error**.
  A handler that logged `event.data.credits_used` recorded a `0` that meant nothing, and a
  handler that branched on `event.data.status` took the empty-string branch forever.

  Reading a message field off a lifecycle event now raises
  `AttributeError: 'NoneType' object has no attribute 'id'`. **That is the point of this
  release, not an accident.** The read was always wrong; it is now loud instead of silent,
  so you find every affected call site the first time such an event arrives rather than
  trusting a zero indefinitely.

  Your code today, on any non-`message.*` event:

  ```python
  event = Webhooks.parse_event(payload, signature, WEBHOOK_SECRET, timestamp=timestamp)

  if event.type == 'rcs_agent.live':
      agent_id = event.data.id        # was always '' - the payload has no `id` at all
      stage = event.data.status       # was always ''
  ```

  After upgrading, that raises. Read the payload off `event.object`, which carries
  `data.object` verbatim:

  ```python
  event = Webhooks.parse_event(payload, signature, WEBHOOK_SECRET, timestamp=timestamp)

  if event.type == 'rcs_agent.live':
      agent_id = event.object['agent_id']
      stage = event.object['stage']
  ```

  The edit is mechanical: on a lifecycle event, every `event.data.<field>` becomes
  `event.object['<key>']`, with the key spelled the way the API sends it rather than the way
  `WebhookMessageData` spelled it. There was no `event.object` before this release, so no
  correct version of this code existed to migrate from — check what your handler assumed
  rather than translating it field for field.

  If a handler touches `event.data` in several branches, guard the message-only path once.
  `if event.data is not None:` both narrows the type for a checker and marks the branch:

  ```python
  if event.data is not None:
      record_delivery(event.data.id, event.data.status)
  else:
      handle_lifecycle(event.type, event.object)
  ```

  `message.*` handlers otherwise need no change: `event.data` is still the message view
  there.

- **`contact.auto_flagged` reported the wrong id, and code keyed on it acted on the wrong
  record.** The payload is a contact — `{id, phone_number, invalid_reason, source,
  message_id, error_code}` — so the old decode put the *contact* id in `event.data.id`, and
  `event.data.message_id` (an alias for `id`) returned that same contact id. The message
  that actually failed was unreachable. If you wrote `mark_bounced(event.data.id)`, it has
  been handing a contact id to something that expects a message id:

  ```python
  # before - `event.data.id` is the CONTACT id, `event.data.message_id` is the same value
  if event.type == 'contact.auto_flagged':
      mark_bounced(event.data.id)

  # after - the two ids are distinct and never swapped
  if event.type == 'contact.auto_flagged':
      flag_contact(event.object['id'])
      mark_bounced(event.object['message_id'])
  ```

  Audit anything this handler wrote before you upgrade; the bad writes are already on disk.

- **`message.opt_in` and `message.opt_out` also return `event.data is None`.** They share the
  `message.` prefix but carry an opt-out record (`phone_number`, `keyword`, `from_number`,
  `timestamp`), not a message, so the old decode produced an all-default message here too.
  Read them from `event.object`. Use `is_message_event(event.type)` rather than testing the
  prefix yourself — it knows about these two.

- **`WebhookEventType` is an enum, not a `Literal` union.** `sendly.webhooks` used to define
  its own `Literal[...]` of event-type strings, drifting from the `WebhookEventType` enum in
  `sendly.types`. There is now one definition: `sendly.webhooks.WebhookEventType` re-exports
  the enum, and `sendly.webhooks.WEBHOOK_EVENT_TYPES` is the tuple of its values. Runtime
  comparisons are unaffected (it is a `str` enum, so `event.type == 'message.delivered'` and
  `event.type == WebhookEventType.MESSAGE_DELIVERED` are both `True`), but an annotation like
  `event_type: WebhookEventType = 'message.delivered'` no longer type-checks. Use
  `WebhookEventType.MESSAGE_DELIVERED`, or annotate as `str`.

- **`message.queued` and `message.undelivered` are gone.** The API has never emitted either
  one and rejects both with a `400` on subscribe, so any `events` list containing them was
  subscribing to nothing and any handler branch on them was dead. They are no longer in
  `WebhookEventType` or `WEBHOOK_EVENT_TYPES`; `WebhookEventType.MESSAGE_QUEUED` now raises
  `AttributeError`. Delete them from your `webhooks.create()` / `webhooks.update()` calls.
  `'queued'` and `'undelivered'` are still valid message *statuses* on `event.data.status` —
  only the event types were removed.

- **`WebhookMessageData` fields no longer carry invented defaults.** Every field is now
  `Optional` and defaults to `None`. On a `message.*` payload that omitted a key you used to
  get `''` for `id` / `status` / `to` / `from_`, `1` for `segments`, `0` for `credits_used`
  and `'outbound'` for `direction`; you now get `None`, so an absent value is
  distinguishable from a real one. Code that did `if not event.data.to:` still works; code
  that did `event.data.to.startswith('+')` or `event.data.segments + 1` unguarded will now
  raise on a sparse payload. `WebhookVerificationData` lost its invented defaults the same
  way (`delivery_status='queued'`, `attempts=0`, `max_attempts=3` are all `None` now).

### Minor Changes

- **`event.object`** — `data.object` exactly as it arrived, on every event type. Keys are
  verbatim (`camelCase` stays `camelCase`), JSON `null` stays `None`, and nothing the payload
  did not carry is added. `event.raw_object` is an alias for it.
- **`event.object_as(cls)`** — decode the payload into a shape of your own: a dataclass, a
  pydantic v2 model, or `dict`. `event.object_as()` with no argument returns a plain dict
  copy. Only keys the payload actually carried are passed through, so a field it did not send
  keeps its default rather than being invented, and a trailing underscore maps a reserved
  word (`from_` reads `from`).
- **`is_message_event(event_type)`** — whether an event type carries a message-shaped
  `data.object`. Takes a `WebhookEventType` or a raw string, including one this SDK version
  has never heard of.
- **`WebhookVerificationData`** — a ready-made shape for `verification.*` payloads.
  `parse_event()` does not produce it for you; pass it to
  `event.object_as(WebhookVerificationData)` when you want it.
- **An event type this SDK version does not know is delivered, not rejected.** `event.type`
  keeps the raw string and `event.object` still carries the payload, so a new event released
  after this version reaches your handler.
- `WebhookEventType` gains the types that were missing everywhere: `conversation.*`,
  `draft.*`, `rcs_brand.*`, `rcs_agent.*`, `whatsapp_account.*`, `whatsapp_template.*` and
  `call.*`. There was previously no typed way to subscribe to RCS, WhatsApp or voice events.

### Patch Changes

- A `data.object` that is not a JSON object now fails with a message that says so —
  `Failed to parse webhook payload: Invalid event structure: data.object must be an object,
  got str` — instead of surfacing an internal `'str' object has no attribute 'get'`. It
  raised before too; only the message changed.


### Security

- **Path parameters are percent-encoded.** Every id you pass is now encoded (`urllib.parse.quote(..., safe="")`) before it goes into the request path. An id containing `/`, `?` or `#` used to change which endpoint the request reached: an id of `../../account/keys` left its collection and hit another endpoint carrying your API key. Ordinary ids are sent byte-for-byte as before.

## 3.38.0

### Minor Changes

- **Every POST now carries an idempotency key automatically.** The client generates a unique `Idempotency-Key` per request and reuses that same key across its own timeout and network-error retries, so a retry of a request that already reached the API returns the original result instead of sending and charging a second time. The server records a key only once the first attempt has finished, so this narrows the duplicate-send window rather than closing it: a retry that fires while the original is still running is not seen as a repeat. You do not have to do anything to get this. After a `5xx` the generated key is rotated, so the retry is a fresh attempt rather than a repeat of the failed one. The server does not record a 5xx against a key either, so a retry re-executes on both counts. The key is honored by the endpoints where a duplicate costs you money: single sends, scheduled sends, group sends, batch sends, verification starts and workspace provisioning.
- **New `idempotency_key` argument** on `messages.send()`, `messages.schedule()`, `messages.send_group()` and `messages.send_batch()`, sync and async. Supply your own key when the guarantee has to outlive the process, for example a job queue that re-runs your handler after a crash. Reusing a key within 24 hours returns the original response; reusing it with a different body returns `422 idempotency_key_mismatch`, so derive keys from something stable in your domain such as an order id. Keys must be 1 to 255 printable ASCII characters, and anything else raises `ValidationError` before a request leaves the process. An empty or whitespace-only string counts as no key at all, so the automatic one still applies.
- `send_batch()` deliberately sends no automatic key. The batch endpoint already collapses identical retried batches by hashing their contents, and an auto-generated key would bypass that net. Pass `idempotency_key` yourself if you want an explicit one on a batch.
- Multipart uploads (`media.upload()`, enterprise verification documents, the business-upgrade EIN letter) now send a single-use key per attempt. Those calls are not retried by the client, so the key labels the upload but does not protect you against a timeout on one.
- `BatchMessageResponse` gains `delivered`, `credits_reserved` and `credits_refunded`. The batch status and list endpoints have always returned these and the model dropped them on the floor.

### Patch Changes

- **`messages.send_batch()` could not succeed against the real API, and now does.** `BatchMessageResponse` required `queued` and `created_at`, which the send endpoint does not return (only the batch status endpoint does), so every live batch send raised `invalid_response` after the batch had already been accepted and the messages were on their way out. Both fields are now optional. No mocked test could catch this, because the shared fixtures invented both fields; the regression test is pinned to the payload production really sends. If you built a retry loop around this failure, check that you are not re-sending batches that already went.
- **`messages.get_batch()` and `messages.list_batches()` could never parse a response either.** Both endpoints key the batch as `id`, while only the send endpoint uses `batchId`, and the list response omits per-message results altogether. `batch_id` now accepts either spelling and `messages` defaults to an empty list, so both calls return real data. `model_dump(by_alias=True)` still writes `batchId`.
- Know which batch response you are holding. A large batch is accepted as `processing`, and that send response carries an empty `messages` list with `queued`, `delivered`, `credits_reserved` and `created_at` all `None`. Poll `get_batch(batch.batch_id)` for the per-message results and those counters. `credits_refunded` is on every batch response, the send included.
- **API key management was pointed at paths the server does not serve.** `list_api_keys()`, `get_api_key()` and `get_api_key_usage()` requested `/keys...` and got a 404 every time. They now use `/account/keys...`, and the list unwraps the `{"keys": [...]}` envelope the server actually returns.
- **`revoke_api_key()` never revoked anything.** It sent `DELETE` to a path that only answers `GET`, so it raised a not-found error and the key stayed live. It now sends `PATCH /account/keys/{id}/revoke` and really does revoke the key. If you have code that calls it and tolerates the failure, that call takes effect from this version on, so check it is aimed at the key you mean.
- Scheduled message IDs are `schd_...`, but the client-side ID validator accepted only `msg_...` and bare UUIDs. Passing the ID you got back from `schedule()` into `get_scheduled()` or `cancel_scheduled()` raised `ValidationError` before any request was made. `schd_` IDs are now accepted. Batch IDs are still not message IDs; `get_batch()` validates those itself.
- `cancel_scheduled()` now returns instead of raising. `CancelledMessageResponse.cancelled_at` was required, but the cancel endpoint returns only `id`, `status` and `creditsRefunded`, so a cancellation that really took effect still came back to you as an `invalid_response` error. The field is now optional and will always be `None`, because the API does not send it. Use your own clock if you need the time of cancellation.
- `ApiKey.last_four` is now optional and will always be `None`. No API key endpoint returns that field, so while it was required it would have failed to parse even once the requests were aimed at the right routes. Use `prefix` to tell keys apart.

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
- `useCase` validation expanded from 23 entries to the full 43-value carrier use-case enum.

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
