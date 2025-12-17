"""
Tests for webhook verification and parsing
"""

import json

import pytest

from sendly.webhooks import (
    WebhookEvent,
    WebhookMessageData,
    Webhooks,
    WebhookSignatureError,
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

    def test_parse_event_invalid_data_structure(self):
        """Test parsing event with invalid data structure"""
        event_data = {
            "id": "evt_123",
            "type": "message.delivered",
            "data": {
                # Missing required fields
                "message_id": "msg_123",
            },
            "created_at": "2025-01-20T10:00:00Z",
        }

        payload = json.dumps(event_data)
        secret = "test_secret"
        signature = Webhooks.generate_signature(payload, secret)

        with pytest.raises(WebhookSignatureError, match="Failed to parse webhook payload"):
            Webhooks.parse_event(payload, signature, secret)

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

        assert event.api_version == "2024-01-01"  # Default value


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
