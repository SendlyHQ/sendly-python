"""
Tests for webhook verification and parsing
"""

import json
from dataclasses import dataclass

import pytest

from sendly.types import WebhookEventType as TypesWebhookEventType
from sendly.webhooks import (
    WEBHOOK_EVENT_TYPES,
    WebhookEvent,
    WebhookEventType,
    WebhookMessageData,
    Webhooks,
    WebhookSignatureError,
    WebhookVerificationData,
    is_message_event,
)


class TestWebhookVerifySignature:
    """Test Webhooks.verify_signature() method"""

    def test_verify_valid_signature(self):
        """Test verifying a valid signature"""
        payload = '{"test": "data"}'
        secret = "test_secret"

        # Generate signature
        signature = Webhooks.generate_signature(payload, secret)

        # Verify it
        assert Webhooks.verify_signature(payload, signature, secret) is True

    def test_verify_invalid_signature(self):
        """Test verifying an invalid signature"""
        payload = '{"test": "data"}'
        secret = "test_secret"
        wrong_signature = "sha256=invalid"

        assert Webhooks.verify_signature(payload, wrong_signature, secret) is False

    def test_verify_signature_wrong_secret(self):
        """Test verifying with wrong secret"""
        payload = '{"test": "data"}'
        secret = "test_secret"
        wrong_secret = "wrong_secret"

        signature = Webhooks.generate_signature(payload, secret)

        assert Webhooks.verify_signature(payload, signature, wrong_secret) is False

    def test_verify_signature_empty_payload(self):
        """Test verifying with empty payload"""
        assert Webhooks.verify_signature("", "sha256=test", "secret") is False

    def test_verify_signature_empty_signature(self):
        """Test verifying with empty signature"""
        assert Webhooks.verify_signature('{"test": "data"}', "", "secret") is False

    def test_verify_signature_empty_secret(self):
        """Test verifying with empty secret"""
        assert Webhooks.verify_signature('{"test": "data"}', "sha256=test", "") is False

    def test_verify_signature_none_values(self):
        """Test verifying with None values"""
        assert Webhooks.verify_signature(None, "sha256=test", "secret") is False
        assert Webhooks.verify_signature('{"test": "data"}', None, "secret") is False
        assert Webhooks.verify_signature('{"test": "data"}', "sha256=test", None) is False

    def test_verify_signature_modified_payload(self):
        """Test that modified payload fails verification"""
        payload = '{"test": "data"}'
        secret = "test_secret"
        signature = Webhooks.generate_signature(payload, secret)

        modified_payload = '{"test": "modified"}'

        assert Webhooks.verify_signature(modified_payload, signature, secret) is False

    def test_verify_signature_case_sensitive(self):
        """Test that signature verification is case-sensitive"""
        payload = '{"test": "data"}'
        secret = "test_secret"
        signature = Webhooks.generate_signature(payload, secret)

        # Convert to uppercase (should fail)
        uppercase_signature = signature.upper()

        assert Webhooks.verify_signature(payload, uppercase_signature, secret) is False


class TestWebhookParseEvent:
    """Test Webhooks.parse_event() method"""

    def test_parse_delivered_event(self):
        """Test parsing a message.delivered event"""
        event_data = {
            "id": "evt_123",
            "type": "message.delivered",
            "data": {
                "message_id": "msg_123",
                "status": "delivered",
                "to": "+15551234567",
                "from": "Sendly",
                "segments": 1,
                "credits_used": 1,
                "delivered_at": "2025-01-20T10:00:00Z",
            },
            "created_at": "2025-01-20T10:00:00Z",
            "api_version": "2024-01-01",
        }

        payload = json.dumps(event_data)
        secret = "test_secret"
        signature = Webhooks.generate_signature(payload, secret)

        event = Webhooks.parse_event(payload, signature, secret)

        assert isinstance(event, WebhookEvent)
        assert event.id == "evt_123"
        assert event.type == "message.delivered"
        assert event.data.message_id == "msg_123"
        assert event.data.status == "delivered"
        assert event.data.to == "+15551234567"
        assert event.data.delivered_at == "2025-01-20T10:00:00Z"

    def test_parse_failed_event(self):
        """Test parsing a message.failed event"""
        event_data = {
            "id": "evt_456",
            "type": "message.failed",
            "data": {
                "message_id": "msg_456",
                "status": "failed",
                "to": "+15551234567",
                "from": "Sendly",
                "segments": 1,
                "credits_used": 0,
                "error": "Invalid number",
                "error_code": "invalid_number",
                "failed_at": "2025-01-20T10:00:00Z",
            },
            "created_at": "2025-01-20T10:00:00Z",
        }

        payload = json.dumps(event_data)
        secret = "test_secret"
        signature = Webhooks.generate_signature(payload, secret)

        event = Webhooks.parse_event(payload, signature, secret)

        assert event.type == "message.failed"
        assert event.data.error == "Invalid number"
        assert event.data.error_code == "invalid_number"
        assert event.data.failed_at == "2025-01-20T10:00:00Z"

    def test_parse_queued_event(self):
        """Test parsing a message.queued event"""
        event_data = {
            "id": "evt_789",
            "type": "message.queued",
            "data": {
                "message_id": "msg_789",
                "status": "queued",
                "to": "+15551234567",
                "from": "Sendly",
                "segments": 1,
                "credits_used": 1,
            },
            "created_at": "2025-01-20T10:00:00Z",
        }

        payload = json.dumps(event_data)
        secret = "test_secret"
        signature = Webhooks.generate_signature(payload, secret)

        event = Webhooks.parse_event(payload, signature, secret)

        assert event.type == "message.queued"
        assert event.data.status == "queued"

    def test_parse_sent_event(self):
        """Test parsing a message.sent event"""
        event_data = {
            "id": "evt_sent",
            "type": "message.sent",
            "data": {
                "message_id": "msg_sent",
                "status": "sent",
                "to": "+15551234567",
                "from": "Sendly",
                "segments": 1,
                "credits_used": 1,
            },
            "created_at": "2025-01-20T10:00:00Z",
        }

        payload = json.dumps(event_data)
        secret = "test_secret"
        signature = Webhooks.generate_signature(payload, secret)

        event = Webhooks.parse_event(payload, signature, secret)

        assert event.type == "message.sent"

    def test_parse_undelivered_event(self):
        """Test parsing a message.undelivered event"""
        event_data = {
            "id": "evt_undelivered",
            "type": "message.undelivered",
            "data": {
                "message_id": "msg_undelivered",
                "status": "undelivered",
                "to": "+15551234567",
                "from": "Sendly",
                "segments": 1,
                "credits_used": 1,
                "error": "Carrier timeout",
            },
            "created_at": "2025-01-20T10:00:00Z",
        }

        payload = json.dumps(event_data)
        secret = "test_secret"
        signature = Webhooks.generate_signature(payload, secret)

        event = Webhooks.parse_event(payload, signature, secret)

        assert event.type == "message.undelivered"
        assert event.data.error == "Carrier timeout"

    def test_parse_event_invalid_signature(self):
        """Test parsing event with invalid signature"""
        event_data = {
            "id": "evt_123",
            "type": "message.delivered",
            "data": {
                "message_id": "msg_123",
                "status": "delivered",
                "to": "+15551234567",
                "from": "Sendly",
                "segments": 1,
                "credits_used": 1,
            },
            "created_at": "2025-01-20T10:00:00Z",
        }

        payload = json.dumps(event_data)
        invalid_signature = "sha256=invalid"

        with pytest.raises(WebhookSignatureError):
            Webhooks.parse_event(payload, invalid_signature, "secret")

    def test_parse_event_malformed_json(self):
        """Test parsing event with malformed JSON"""
        payload = "not valid json"
        secret = "test_secret"
        signature = Webhooks.generate_signature(payload, secret)

        with pytest.raises(WebhookSignatureError, match="Failed to parse webhook payload"):
            Webhooks.parse_event(payload, signature, secret)

    def test_parse_event_missing_required_fields(self):
        """Test parsing event with missing required fields"""
        event_data = {
            "id": "evt_123",
            # Missing 'type', 'data', 'created_at'
        }

        payload = json.dumps(event_data)
        secret = "test_secret"
        signature = Webhooks.generate_signature(payload, secret)

        with pytest.raises(WebhookSignatureError, match="Failed to parse webhook payload"):
            Webhooks.parse_event(payload, signature, secret)

    def test_parse_event_sparse_data_structure(self):
        """Sparse data leaves absent fields None instead of inventing values"""
        event_data = {
            "id": "evt_123",
            "type": "message.delivered",
            "data": {
                "message_id": "msg_123",
            },
            "created_at": "2025-01-20T10:00:00Z",
        }

        payload = json.dumps(event_data)
        secret = "test_secret"
        signature = Webhooks.generate_signature(payload, secret)

        event = Webhooks.parse_event(payload, signature, secret)
        assert event.data.id == "msg_123"
        assert event.data.status is None
        assert event.data.segments is None
        assert event.data.credits_used is None
        assert event.data.to is None
        assert event.data.from_ is None
        assert event.data.direction is None
        assert event.object == {"message_id": "msg_123"}

    def test_parse_event_empty_payload(self):
        """Test parsing empty payload"""
        payload = ""
        signature = "sha256=test"

        with pytest.raises(WebhookSignatureError):
            Webhooks.parse_event(payload, signature, "secret")

    def test_parse_event_with_default_api_version(self):
        """Test parsing event without api_version field"""
        event_data = {
            "id": "evt_123",
            "type": "message.delivered",
            "data": {
                "message_id": "msg_123",
                "status": "delivered",
                "to": "+15551234567",
                "from": "Sendly",
                "segments": 1,
                "credits_used": 1,
            },
            "created_at": "2025-01-20T10:00:00Z",
            # No api_version
        }

        payload = json.dumps(event_data)
        secret = "test_secret"
        signature = Webhooks.generate_signature(payload, secret)

        event = Webhooks.parse_event(payload, signature, secret)

        assert event.api_version == "2024-01"  # Default value


class TestWebhookGenerateSignature:
    """Test Webhooks.generate_signature() method"""

    def test_generate_signature_basic(self):
        """Test generating a signature"""
        payload = '{"test": "data"}'
        secret = "test_secret"

        signature = Webhooks.generate_signature(payload, secret)

        assert signature.startswith("sha256=")
        assert len(signature) > 7  # "sha256=" + hash

    def test_generate_signature_consistency(self):
        """Test that same inputs generate same signature"""
        payload = '{"test": "data"}'
        secret = "test_secret"

        sig1 = Webhooks.generate_signature(payload, secret)
        sig2 = Webhooks.generate_signature(payload, secret)

        assert sig1 == sig2

    def test_generate_signature_different_payloads(self):
        """Test that different payloads generate different signatures"""
        secret = "test_secret"

        sig1 = Webhooks.generate_signature('{"test": "data1"}', secret)
        sig2 = Webhooks.generate_signature('{"test": "data2"}', secret)

        assert sig1 != sig2

    def test_generate_signature_different_secrets(self):
        """Test that different secrets generate different signatures"""
        payload = '{"test": "data"}'

        sig1 = Webhooks.generate_signature(payload, "secret1")
        sig2 = Webhooks.generate_signature(payload, "secret2")

        assert sig1 != sig2

    def test_generate_signature_empty_payload(self):
        """Test generating signature for empty payload"""
        signature = Webhooks.generate_signature("", "secret")

        assert signature.startswith("sha256=")

    def test_generate_signature_unicode_payload(self):
        """Test generating signature for unicode payload"""
        payload = '{"test": "测试数据"}'
        secret = "test_secret"

        signature = Webhooks.generate_signature(payload, secret)

        assert signature.startswith("sha256=")

    def test_generate_signature_special_characters(self):
        """Test generating signature with special characters"""
        payload = '{"test": "data with !@#$%^&*()"}'
        secret = "secret!@#$"

        signature = Webhooks.generate_signature(payload, secret)

        assert signature.startswith("sha256=")


class TestWebhookIntegration:
    """Integration tests for webhook workflow"""

    def test_complete_webhook_flow(self):
        """Test complete webhook flow: generate, verify, parse"""
        event_data = {
            "id": "evt_integration",
            "type": "message.delivered",
            "data": {
                "message_id": "msg_integration",
                "status": "delivered",
                "to": "+15551234567",
                "from": "Sendly",
                "segments": 1,
                "credits_used": 1,
                "delivered_at": "2025-01-20T10:00:00Z",
            },
            "created_at": "2025-01-20T10:00:00Z",
        }

        payload = json.dumps(event_data)
        secret = "webhook_secret"

        # 1. Generate signature (as Sendly would)
        signature = Webhooks.generate_signature(payload, secret)

        # 2. Verify signature (in your webhook handler)
        assert Webhooks.verify_signature(payload, signature, secret) is True

        # 3. Parse event (in your webhook handler)
        event = Webhooks.parse_event(payload, signature, secret)

        assert event.id == "evt_integration"
        assert event.type == "message.delivered"
        assert event.data.message_id == "msg_integration"

    def test_webhook_flow_with_tampered_payload(self):
        """Test that tampering fails verification"""
        event_data = {
            "id": "evt_tamper",
            "type": "message.delivered",
            "data": {
                "message_id": "msg_tamper",
                "status": "delivered",
                "to": "+15551234567",
                "from": "Sendly",
                "segments": 1,
                "credits_used": 1,
            },
            "created_at": "2025-01-20T10:00:00Z",
        }

        payload = json.dumps(event_data)
        secret = "webhook_secret"
        signature = Webhooks.generate_signature(payload, secret)

        # Tamper with payload
        tampered_data = event_data.copy()
        tampered_data["data"]["credits_used"] = 0  # Changed!
        tampered_payload = json.dumps(tampered_data)

        # Verification should fail
        assert Webhooks.verify_signature(tampered_payload, signature, secret) is False

        # Parse should raise error
        with pytest.raises(WebhookSignatureError):
            Webhooks.parse_event(tampered_payload, signature, secret)

    def test_multiple_events_different_signatures(self):
        """Test that multiple events have different signatures"""
        secret = "webhook_secret"
        events = []

        for i in range(3):
            event_data = {
                "id": f"evt_{i}",
                "type": "message.delivered",
                "data": {
                    "message_id": f"msg_{i}",
                    "status": "delivered",
                    "to": "+15551234567",
                    "from": "Sendly",
                    "segments": 1,
                    "credits_used": 1,
                },
                "created_at": "2025-01-20T10:00:00Z",
            }

            payload = json.dumps(event_data)
            signature = Webhooks.generate_signature(payload, secret)
            event = Webhooks.parse_event(payload, signature, secret)

            events.append((signature, event))

        # All signatures should be different
        signatures = [sig for sig, _ in events]
        assert len(set(signatures)) == 3

        # All events should be different
        message_ids = [event.data.message_id for _, event in events]
        assert message_ids == ["msg_0", "msg_1", "msg_2"]


class TestWebhookEdgeCases:
    """Test edge cases and error conditions"""

    def test_verify_signature_with_whitespace(self):
        """Test that whitespace in payload affects signature"""
        secret = "test_secret"

        payload1 = '{"test":"data"}'
        payload2 = '{"test": "data"}'  # Extra space

        sig1 = Webhooks.generate_signature(payload1, secret)
        sig2 = Webhooks.generate_signature(payload2, secret)

        # Different payloads should have different signatures
        assert sig1 != sig2

        # Each signature should only verify its own payload
        assert Webhooks.verify_signature(payload1, sig1, secret) is True
        assert Webhooks.verify_signature(payload2, sig1, secret) is False

    def test_parse_event_with_extra_fields(self):
        """Test parsing event with extra unknown fields"""
        event_data = {
            "id": "evt_extra",
            "type": "message.delivered",
            "data": {
                "message_id": "msg_extra",
                "status": "delivered",
                "to": "+15551234567",
                "from": "Sendly",
                "segments": 1,
                "credits_used": 1,
                "unknown_field": "should be ignored",
            },
            "created_at": "2025-01-20T10:00:00Z",
            "unknown_top_level": "also ignored",
        }

        payload = json.dumps(event_data)
        secret = "test_secret"
        signature = Webhooks.generate_signature(payload, secret)

        # Should parse successfully, ignoring extra fields
        event = Webhooks.parse_event(payload, signature, secret)

        assert event.id == "evt_extra"
        assert event.type == "message.delivered"

    def test_large_payload(self):
        """Test handling large payload"""
        large_text = "A" * 10000
        event_data = {
            "id": "evt_large",
            "type": "message.delivered",
            "data": {
                "message_id": "msg_large",
                "status": "delivered",
                "to": "+15551234567",
                "from": "Sendly",
                "segments": 100,
                "credits_used": 100,
                "delivered_at": "2025-01-20T10:00:00Z",
            },
            "created_at": "2025-01-20T10:00:00Z",
        }

        payload = json.dumps(event_data)
        secret = "test_secret"
        signature = Webhooks.generate_signature(payload, secret)

        event = Webhooks.parse_event(payload, signature, secret)

        assert event.data.message_id == "msg_large"


class TestWebhookExtractionContract:
    """data.object is reachable for every event type, and nothing is invented"""

    SECRET = "test_secret"

    def _parse(self, event_data):
        payload = json.dumps(event_data)
        signature = Webhooks.generate_signature(payload, self.SECRET)
        return Webhooks.parse_event(payload, signature, self.SECRET)

    def test_lifecycle_event_has_no_message_view(self):
        """rcs_agent.live is not a message, so event.data is None"""
        event = self._parse(
            {
                "id": "evt_rcs",
                "type": "rcs_agent.live",
                "created": 1767225600,
                "livemode": True,
                "data": {
                    "object": {
                        "agent_id": "bb22cc33",
                        "name": "Acme Support",
                        "stage": "live",
                        "organization_id": "0a1b2c3d",
                    }
                },
            }
        )

        assert event.data is None
        assert event.object["agent_id"] == "bb22cc33"
        assert event.object["stage"] == "live"
        assert event.raw_object is event.object

    def test_lifecycle_object_keeps_camel_case_keys(self):
        """Keys arrive verbatim; camelCase is not rewritten"""
        event = self._parse(
            {
                "id": "evt_wa",
                "type": "whatsapp_template.approved",
                "created": 1767225600,
                "data": {
                    "object": {
                        "id": "dd44ee55",
                        "name": "appointment_reminder",
                        "qualityRating": None,
                        "rejectionReason": None,
                        "createdAt": "2026-01-01T00:00:00.000Z",
                    }
                },
            }
        )

        assert event.data is None
        assert event.object["createdAt"] == "2026-01-01T00:00:00.000Z"
        assert event.object["qualityRating"] is None
        assert "quality_rating" not in event.object

    def test_call_event_null_numbers_stay_null(self):
        """In-app calls have null from/to; null must not become ''"""
        event = self._parse(
            {
                "id": "evt_call",
                "type": "call.started",
                "created": 1767225600,
                "data": {
                    "object": {
                        "id": "ff660011",
                        "object": "call",
                        "kind": "internal",
                        "direction": "outbound",
                        "status": "active",
                        "from": None,
                        "to": None,
                        "duration_secs": 0,
                        "agent_id": None,
                    }
                },
            }
        )

        assert event.data is None
        assert event.object["from"] is None
        assert event.object["to"] is None
        assert event.object["agent_id"] is None
        assert event.object["duration_secs"] == 0

    def test_contact_auto_flagged_does_not_mis_attribute_message_id(self):
        """`id` is the contact; `message_id` is the message. Never swap them."""
        event = self._parse(
            {
                "id": "evt_contact",
                "type": "contact.auto_flagged",
                "created": 1767225600,
                "data": {
                    "object": {
                        "id": "contact-5e4d3c2b",
                        "message_id": "message-2d1f8a34",
                        "phone_number": "+15555550144",
                        "invalid_reason": "landline",
                        "error_code": "E003",
                    }
                },
            }
        )

        assert event.data is None, "a contact event must not present as a message"
        assert event.object["id"] == "contact-5e4d3c2b"
        assert event.object["message_id"] == "message-2d1f8a34"

    def test_unknown_event_type_parses(self):
        """An event type this SDK version predates still parses"""
        event = self._parse(
            {
                "id": "evt_new",
                "type": "something.invented_later",
                "created": 1767225600,
                "data": {"object": {"id": "f1e2d3c4", "some_new_field": "a value"}},
            }
        )

        assert event.type == "something.invented_later"
        assert event.data is None
        assert event.object["some_new_field"] == "a value"

    def test_message_event_keeps_message_view(self):
        """message.* events still get the message view, unchanged"""
        event = self._parse(
            {
                "id": "evt_msg",
                "type": "message.delivered",
                "created": 1767225600,
                "data": {
                    "object": {
                        "id": "7c9e6679",
                        "to": "+15555550123",
                        "from": "+15555550188",
                        "text": "Hello",
                        "status": "delivered",
                        "direction": "outbound",
                        "segments": 1,
                        "credits_used": 2,
                    }
                },
            }
        )

        assert event.data is not None
        assert event.data.id == "7c9e6679"
        assert event.data.message_id == "7c9e6679"
        assert event.data.to == "+15555550123"
        assert event.data.from_ == "+15555550188"
        assert event.data.credits_used == 2
        assert event.object["from"] == "+15555550188"

    def test_object_as_dict_by_default(self):
        event = self._parse(
            {
                "id": "evt_num",
                "type": "number.activated",
                "created": 1767225600,
                "data": {"object": {"id": "8c7b6a59", "phone": "+15555550188"}},
            }
        )

        obj = event.object_as()
        assert obj == {"id": "8c7b6a59", "phone": "+15555550188"}
        assert obj is not event.object

    def test_object_as_dataclass_maps_reserved_words(self):
        @dataclass
        class CallObject:
            id: str = None
            from_: str = None
            to: str = None
            unmentioned: str = None

        event = self._parse(
            {
                "id": "evt_call2",
                "type": "call.completed",
                "created": 1767225600,
                "data": {
                    "object": {"id": "ee55ff66", "from": "+15555550188", "to": "+15555550123"}
                },
            }
        )

        call = event.object_as(CallObject)
        assert call.id == "ee55ff66"
        assert call.from_ == "+15555550188"
        assert call.to == "+15555550123"
        assert call.unmentioned is None

    def test_object_as_verification_data(self):
        event = self._parse(
            {
                "id": "evt_ver",
                "type": "verification.verified",
                "created": 1767225600,
                "data": {
                    "object": {
                        "id": "b1f0c9d2",
                        "phone": "+15555550123",
                        "status": "verified",
                        "attempts": 1,
                    }
                },
            }
        )

        assert event.data is None, "a verification event is not message-shaped"
        verification = event.object_as(WebhookVerificationData)
        assert verification.phone == "+15555550123"
        assert verification.attempts == 1
        assert verification.max_attempts is None, "absent field must stay None"


class TestWebhookEventTypeSourceOfTruth:
    """webhooks.WebhookEventType is sendly.types.WebhookEventType, not a copy"""

    def test_reexports_the_types_enum(self):
        assert WebhookEventType is TypesWebhookEventType

    def test_live_event_types_are_present(self):
        for event_type in (
            "rcs_agent.live",
            "whatsapp_template.approved",
            "call.started",
            "call.completed",
            "call.recording.ready",
            "conversation.updated",
            "draft.created",
            "contact.auto_flagged",
            "contacts.lookup_completed",
        ):
            assert event_type in WEBHOOK_EVENT_TYPES

    def test_removed_event_types_are_gone(self):
        assert "message.queued" not in WEBHOOK_EVENT_TYPES
        assert "message.undelivered" not in WEBHOOK_EVENT_TYPES

    def test_is_message_event(self):
        assert is_message_event("message.delivered") is True
        assert is_message_event(WebhookEventType.MESSAGE_RECEIVED) is True
        assert is_message_event("rcs_agent.live") is False
        assert is_message_event("call.started") is False
        assert is_message_event("contact.auto_flagged") is False
        assert is_message_event("verification.verified") is False
        assert is_message_event("something.invented_later") is False
