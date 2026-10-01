# sendly (Python)

## 4.3.0

### Minor Changes

- **Options and fields the API already supported, now in the Python SDK.**
  - `account.create_api_key(name, type='live', scopes=[...])`: keyword-only `type` (`'test'` or `'live'`) and `scopes`. Without `type` the request body is unchanged and the API creates a test key. A live key needs a verified business and a credit balance; the API answers 403 `verification_required` or 402 `credits_required` otherwise.
  - `account.get_credit_transactions(type='refund')` filters by type. `TransactionType` gains `TRANSFER`, `ADMIN_GRANT` and `ADMIN_SEED`, and a type this version does not know is kept instead of raising: its `value` is the string the API sent and its `name` is `UNKNOWN`. Auto-recharges are recorded as `PURCHASE`; `ADJUSTMENT` is never recorded.
  - `Account` gains `organization`, `credits`, `verification`, `api_key` and `limits`. `ApiKey` gains `is_active` and `revoked_at`.
  - `webhooks.get_deliveries(id, limit=..., offset=..., status=...)`, where `status` is a `DeliveryStatus` or its value. `WebhookSecretRotation` gains `secret` (the same value as `new_secret`), `success`, `id`, `new_secret_version`, `grace_period_hours` and `rotated_at`.
  - `messages.list()` takes `offset`, `status`, `direction`, `to`, `page`, `q` and `sandbox`, and `list_all()` takes `offset`, `status`, `direction`, `to`, `q` and `sandbox`; `status` is a `MessageStatus` or its value. `MessageListResponse` gains `pagination` (`MessageListPagination`: `total`, `limit`, `offset`, `page`, `total_pages`, `has_more`); `count` is the size of the page.
  - `messages.send_batch()` and `preview_batch()` accept up to 10,000 messages, the API's limit, exported as `MAX_BATCH_MESSAGES`.
  - `GroupMessageResponse.recipients` lists each `GroupRecipient` with its delivery status on a live group send.
  - `SenderType` gains `EXPLICIT`, and `ScheduledMessageStatus` gains `DELIVERED` and `BOUNCED`. Both keep a value they do not know the same way as `TransactionType`, with the API's string as its `value`. None of the three has an `UNKNOWN` member to compare with, as `MessageStatus` does: check `.name == 'UNKNOWN'`.
  - `RcsAgent.stage` and `RcsMessageDetails.fallback_reason`.
  - `campaigns.send(id, from_=...)` returns a `CampaignSendResult`. `CampaignPreview` gains `opted_out_count`, `invalid_count` and `sample_recipients`, and `CampaignStatus` gains `COMPLETED`, what a sent campaign becomes.
  - `rules.update(id, enabled=False)` switches a rule off, and `Rule` gains `enabled`.
  - `TemplatePreview` gains `character_count` and `segment_count`.
  - Enterprise: `workspaces.inherit_verification(id, source_id, purchase_new_number=True)` orders the workspace its own toll-free number. `analytics.credits()` returns `total_balance`, `total_lifetime`, `total_used` and `workspace_count`. `EnterpriseWorkspaceDetail` gains `verification_type`, `key_count` and `created_at`. `webhooks.set(url, events=..., workspaces=...)`, and `EnterpriseWebhook` gains `signing_secret` (returned once, by the first `set()`), `events` and `workspaces`. The async client gains `workspaces.resubmit_verification()`.
- `OwnedNumber.reported_monthly_cost_cents` is the monthly cost as the API reported it, or None when the number has no recorded price.
- New types: `CampaignSendResult`, `GroupRecipient`, `MessageListPagination` and `UpdatedContact`.
- **WhatsApp sender extras and adding a number by code.** Sync and async clients.
  - `whatsapp.senders.upload_profile_photo(phone_number, file, content_type='image/jpeg')` uploads a JPEG or PNG of up to 5 MB (a binary file or bytes, sent as the multipart field `file`), and `delete_profile_photo(phone_number)` removes it. Both return the `WhatsAppSenderProfile`.
  - `whatsapp.senders.get_conversational_components(phone_number)` and `update_conversational_components(phone_number, ice_breakers=..., commands=...)` read and replace the ice breakers (up to 4) and "/" commands (up to 30) as a `WhatsAppConversationalComponents`. `commands` takes dicts or the `WhatsAppCommand` objects a read returned. Each list you pass replaces the stored one and `[]` clears it; passing neither raises `ValidationError` before anything is sent.
  - `whatsapp.senders.set_calling(phone_number, enabled=True)` switches WhatsApp calling on or off and returns a `WhatsAppCallingSettings`. Turning it on needs calls switched on for the number (`voice_not_enabled` otherwise). There is no API for placing WhatsApp calls.
  - `WhatsAppSender` gains `business_account_id`, `business_name` (None while `pending`, or when the account has no business name on file), `calling_enabled` and `outbound_calling_allowed` (False for +1, +20, +84 and +234 numbers).
  - `whatsapp.signup.create(phone_number, business_account_id=..., verification_method=..., display_name=...)` adds a number to a WhatsApp Business Account the workspace already connected, without the Facebook step. Same $19 fee, refunded if it fails. It returns a `WhatsAppSignup` with status `verifying` and no `connect_url`; `create(phone_number)` still returns a `WhatsAppSignupSession`, and overloads type both. An empty `business_account_id`, or `verification_method` or `display_name` without one, raises `ValidationError` before anything is sent.
  - `whatsapp.signup.verify(id, code)` submits the 6-digit code and returns the `active` signup; `whatsapp.signup.resend(id, verification_method=None)` asks for a new code (at least 30 seconds apart; leaving out the method sends a text).
  - `WhatsAppSignup` gains `verification_method`, `verification_attempts_remaining` and, from `get()`, `verification_code`, the code read from the number's texts or None. Signups can be `verifying`, and fail with `verification_start_failed`, `verification_failed` or `verification_expired`. `ApiErrorResponse` gains `attempts_remaining`, set on a wrong code.
  - `signup.create()` with a `business_account_id`, `signup.verify()` and `senders.upload_profile_photo()` raise a 5xx, a timeout or a network error at once instead of retrying it: a retried add-by-code start can begin a new $19 signup, every code submission uses one of the 5 attempts (and a 502 `whatsapp_activation_pending` means WhatsApp already accepted the code), and the API keeps no idempotency record for a code submission or a photo upload. Only a 429 the API never ran is still waited out and retried, when its wait is 60 seconds or less: `rate_limit_exceeded`, `provision_rate_limit` or `too_many_concurrent_verifications` for `signup.create()` and `signup.verify()`, and only `too_many_concurrent_verifications` for the photo upload. `signup.resend()` and every other call keep the usual retry policy.
- `Call` gains `channel` (`phone`, `whatsapp` or `browser`, kept as a string so a value added later is not lost; see the new `CallChannel` enum), and the `call.started`, `call.completed` and `call.recording.ready` webhook objects carry it too.
- New types: `WhatsAppConversationalComponents`, `WhatsAppCommand`, `WhatsAppCallingSettings` and `CallChannel`.

### Patch Changes

- **Methods that failed on every call now work.** Each was checked against the handler it calls.
  - `account.get()` raised a validation error: the API nests `id`, `email` and `createdAt` under `user`.
  - `account.get_credit_transactions()` iterated the keys of the `{transactions}` envelope and raised `AttributeError`, and rows with a `transfer` or `admin_grant` type or no description would not have parsed.
  - `webhooks.get_deliveries()` iterated the keys of the `{deliveries, pagination}` envelope and raised `AttributeError`.
  - `webhooks.rotate_secret()` raised after the API had rotated, so the new secret, shown only once, was lost. If a rotation response still cannot be read, the error keeps the body, secret included, on `e.response.model_extra`.
  - `conversations.add_labels()` raised `invalid_response` after the labels were applied, and `conversations.remove_label()` raised `TypeError` on the empty 204 after the label was removed.
  - `messages.send()` raised `invalid_response` after a live message was sent and charged, when the API reported `senderType` `explicit` (a number of yours). `messages.send_group()` did the same after every live group send, and `list_scheduled()` and `get_scheduled()` failed once a scheduled message was delivered or bounced.
  - `numbers.list()` failed for any workspace with a number that has no recorded price, country or type, such as the toll-free number provisioned with a verification; `get()` and `update()` failed for that number. Such a number reads `monthly_cost_cents` 0 and an empty `country_code` or `phone_number_type`, and `reported_monthly_cost_cents` is None when no price is recorded.
  - `campaigns.send()` raised `KeyError('id')` after the campaign was sent, and `campaigns.preview()` raised `KeyError('id')`.
  - `media.upload()` sent its multipart body labelled `application/json`, so every upload failed.
  - `contacts.update()` raised a validation error after saving, because the response has no `created_at`. It returns an `UpdatedContact` with the fields the response carries.
  - `templates.preview()` raised `KeyError('id')`: the API returns `template_id` and `rendered_text`.
  - `enterprise.webhooks.get()` raised pydantic's `ValidationError` when no webhook was set; it raises `NotFoundError` instead. The async `enterprise.workspaces.submit_verification()` sent a snake_case body the API never reads, so a first submit always failed.
- **An id of `..`, `.` or an empty string is refused before anything is sent.** Quoting an id leaves its dots alone, so the URL resolved `..` as a step up a level and sent the request to the parent endpoint: `enterprise.workspaces.revoke_key('ws_1', '..')` sent `DELETE /enterprise/workspaces/ws_1` and deleted the workspace, and `contacts.lists.remove_contact(list_id, '..')` deleted the list. Every method, sync and async, uploads included, now raises `ValidationError` for such an id without making a request. Ids that merely contain dots, such as `tpl.v2` or `...`, are sent as before.
- **Values that were wrong on every call.** `messages.list_scheduled()` and `list_batches()` sent an enum member passed as `status` by its name, such as `status=ScheduledMessageStatus.SCHEDULED`, which matched nothing; they send its value. `account.get_api_key()` reported `is_revoked=False` and `permissions=[]` for every key; they are read from `isActive`, `revokedAt` and `scopes`. `webhooks.test()` left `status_code` and `response_time_ms` None; they are read from the test delivery. `enterprise.workspaces.get()` left `verification_status`, `toll_free_number`, `business_name` and `credit_balance` at None or 0. `campaigns.get()`, `list()`, `create()`, `update()`, `schedule()`, `cancel()` and `clone()` read the counts and dates from snake_case keys the API does not send, so every count was 0 and `scheduled_at`, `started_at` and `completed_at` were None; they are read from the camelCase keys the API sends.
- **Only a response that can change is retried.** An ordinary rate limit (`rate_limit_exceeded`) still waits out the body's `retryAfter` when that is 60 seconds or less. A longer one is raised at once with its `retry_after`. The workspace provisioning limit (`provision_rate_limit`, 120 a minute) is waited out the same way; its hourly limit (1,000) is raised at once, unless a minute or less is left in the hour. It is now a `RateLimitError`, where it was a plain `SendlyError` that was sent again at once. Before, `verify.send()` and `verify.resend()` against the per-phone limit (5 codes per 10 minutes) or the daily limit (20 per day) blocked for up to 10 minutes or a day on each attempt. `verify.resend()` then sent a code nobody was waiting for; `verify.send()` retried under the same idempotency key, so it got the recorded 429 back and raised it. The two key-check 429s are described below. 408, 425 and 5xx responses are retried after the same exponential backoff as timeouts and network errors (5xx used to be retried at once). Every other status is raised on the first attempt: a 307, a 409 conflict, a 422 or a 429 `max_attempts_exceeded` from `verify.check()` used to be sent again, up to three more times. While `drafts.approve()` still answered with a redirect, the retried 307 surfaced as a misleading 404 `Draft not found or not pending`, because the first request had already used up the draft.
- **A retried 5xx keeps its idempotency key.** After a 5xx the client sent the retry with a new auto-generated key, a leftover from when the API recorded server errors under the key. The API has not recorded a 5xx since August, so the retry runs again under the same key either way. A new key only lost protection in one case: when the API had finished the request and recorded its answer but a gateway returned the 5xx, a retry with a new key sent the message again. The retry now carries the same key, so that case returns the recorded answer instead.
- **The two 429s from API key checks.** A 429 `too_many_concurrent_verifications`, returned while too many first-time key checks run at once from one address, is retried after its `retryAfter` (1 second; never a wait over a minute) with the same idempotency key, because the request never ran. This includes uploads (`media.upload()`, `business_upgrade.start()` and `resubmit()`, and `enterprise.upload_verification_document()`). If the retries run out it is a `RateLimitError`, where it was a plain `SendlyError` sent again at once with no wait (uploads raised it at once). A 429 `too_many_failed_key_attempts` means repeated wrong API keys from one address locked the account out for a while: it is raised at once as a `RateLimitError` whose `code` is `too_many_failed_key_attempts` and whose `retry_after` says when the lockout ends, which can be up to 5 minutes. It is not retried; it was a plain `SendlyError` sent again at once, up to three more times (uploads raised it at once). Fix the key, then wait `retry_after` seconds, since until the lockout ends requests from that address can be refused even with the right key. `RateLimitError` takes an optional `code` keyword. An ordinary `rate_limit_exceeded` is still waited out and retried when its `retryAfter` is 60 seconds or less, as described above.
- **Errors keep their code and message.** Many endpoints answer `{"error": "<sentence>"}` or `{"error": "not_found"}` with no `message`, and a failed `webhooks.test()` answers `{success, message}`; all of them surfaced as `internal_error` with the body as the message. A code-shaped `error` is kept; a sentence, or no `error`, gets a code from the status (`invalid_request`, `unauthorized`, `insufficient_credits`, `forbidden`, `not_found`, `conflict`, `rate_limit_exceeded`, otherwise `internal_error`), and the message is `message`, then the sentence, then `HTTP <status>`. `validation_error` and `invalid_code` errors are `ValidationError`s. `e.response` keeps the rest of the body.
- **Client-side checks raise the documented error type.** The RCS check for exactly one of `text` or `card` and the check that a WhatsApp send has content raise `ValidationError` instead of the base `SendlyError`, with the same code, `invalid_request`. `webhooks.create()` still raises `ValueError` for a URL that is not HTTPS or empty events, and its docstring now says so instead of `ValidationError`.
- **Docs that described behaviour the API does not have.** `webhooks.rotate_secret()` no longer says the old secret keeps working for 24 hours: deliveries are signed with the new secret as soon as the rotation returns, so have your endpoint accept both secrets while you deploy the new one. `webhooks.backfill()` no longer says to dedupe on `data.object.id`: synthesized events reuse the original event id, so dedupe on `event.id`. The `Message` descriptions no longer say sends omit `direction`, `segments` and `credits_used`. `calls.create()` lists `from_number_required` and `from_number_not_supported`, `VerificationStatus` says `INVALID` is never returned, `CampaignStatus` says `SENT` and `PAUSED` are never returned, and the `messages.preview_batch()` example reads keys the preview returns instead of `canSend`. `media.upload()` names the errors an unsupported file raises: `invalid_file` when `content_type` is a JPEG, PNG or GIF type but the content is not, and `internal_error` (HTTP 500) for any other `content_type` or a file over 600 KB. `Account.name`, `CreditTransaction.message_id`, `Campaign.template_id` and `CampaignPreview.breakdown` say the API never sends them, so they are always None, and `TemplatePreview.variables` says it is always empty. `campaigns.create()` and `update()` say `contact_list_ids` takes one contact list ID in a one-element list: a campaign targets one list, and the API answers 400 `invalid_request` to more than one.
- **WhatsApp docs match the API.** The field descriptions and docstrings now say that the API never sends the `expired` signup status, that a closed window returns its past `expires_at` rather than None, that a media send returns its caption as `text`, how in-window replies are priced (1 credit for the first 1,000 per sending number each month, then the destination's utility price), which roles and scopes connecting and editing need, the `waba_mismatch` and `registration_timeout` failure reasons, `template_header_variable_unsupported`, `whatsapp_unavailable` (503), `whatsapp_signup_limit_reached` (429), and `whatsapp_send_failed` as a final 422 or a retried 502. Nothing changes at runtime.
- **WhatsApp send failures.** A 502 `whatsapp_send_failed` means the message provably never reached the carrier, so it was not sent and is safe to send again; the SDK still retries it under the same idempotency key. The new 409 `whatsapp_send_unconfirmed` means the outcome is unknown: the message was marked failed and refunded but may still be delivered, so check before sending it again (it could arrive twice). It is not retried automatically. The `messages.send()` docstring and the README say so.

**Worth knowing before you upgrade.**

- Four methods are annotated with a new return type, because the old one described a response the endpoint never sends and every call raised: `conversations.add_labels()` returns `LabelListResponse`, `conversations.remove_label()` returns `None`, `campaigns.send()` returns `CampaignSendResult` (read the campaign itself with `campaigns.get()`), and `contacts.update()` returns `UpdatedContact`, which has no `opted_out`, `lists` or `created_at` because the update response does not carry them (read those with `contacts.get()`). A type checker will flag code written against the old types.
- Fields that the API leaves out or sends as null are now `Optional`: `CreditTransaction.description`, `TemplatePreview.name`, `CampaignPreview.estimated_segments`, and `WebhookSecretRotation.webhook` and `old_secret_expires_at`, which the API never sends and are always None.
- Errors from bodies without a code were `internal_error`; they now carry the status-derived code above and the matching subclass (`ValidationError`, `NotFoundError`, `AuthenticationError`, `InsufficientCreditsError`, `RateLimitError`). A failed `webhooks.test()` still raises, now as a `ValidationError` with the API's message. Code that compared `e.code == 'internal_error'` for these responses needs the new code. Every error is still a `SendlyError`.

## 4.2.0

### Minor Changes

- **Voice configuration: `client.voice`.** Everything a phone call depends on is now configurable from code. `voice.numbers.list()`, `get(number)`, `update(number, voice_enabled=..., voice_mode=..., agent_id=...)` and `register_emergency_address(number, street=..., unit=..., city=..., state=..., zip=..., country=...)` switch voice on for a number, choose how it answers and register the emergency address it needs before it can place calls; `number` is the number's id or its E.164 phone number. `voice.agents.list()`, `create(name, ...)`, `get(id)`, `update(id, ...)` and `delete(id)` manage the AI agents that talk, and `voice.voices.list()` lists the voices they can use. Sync and async clients. Reads need the `calls:read` scope, writes `calls:write` and a live API key. Deleting an agent that still answers a number raises `SendlyError` with code `agent_in_use` (HTTP 409) and the numbers in `e.response.model_extra['numbers']`.
- New types: `VoiceNumber`, `VoiceNumberListResponse`, `VoiceNumberEmergencyAddress`, `EmergencyAddress`, `VoiceNumberRates`, `VoiceMode`, `VoiceAgent`, `VoiceAgentListResponse`, `VoiceAgentTools`, `Voice`, `VoiceListResponse`, `CreateVoiceAgentRequest`, `UpdateVoiceAgentRequest`, `UpdateVoiceNumberRequest` and `DeletedVoiceAgent`.

### Patch Changes

- The `calls.recording()` docstring had the channels the wrong way round. Agent calls are recorded with the agent on the left channel and the other party on the right.

## 4.1.0

### Minor Changes

- **Voice calls: `client.calls`.** `create(to, agent_id, from_=..., context=..., metadata=...)` places a phone call that one of your workspace's AI agents handles; `list(...)`, `get(id)`, `hangup(id)` and `recording(id)` follow it, end it early and fetch the recording. Sync and async clients. Reads need the `calls:read` scope, writes `calls:write` and a live API key; until voice is enabled for your workspace the routes answer 404 `voice_not_enabled`.
- `voice_enabled` and `voice_mode` on owned numbers.

### Patch Changes

- `MessageStatus` gains `RECEIVED` and `UNDELIVERED`. `messages.list()` returns inbound rows by default and their status is `received`, which the strict enum rejected, so listing failed for any workspace with inbound traffic. Any status this version does not know now maps to `MessageStatus.UNKNOWN` instead of raising.

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
