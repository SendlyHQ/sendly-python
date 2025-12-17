"""
Tests for validation functions
"""

import pytest

from sendly.errors import ValidationError
from sendly.utils.validation import (
    calculate_segments,
    get_country_from_phone,
    is_country_supported,
    validate_limit,
    validate_message_id,
    validate_message_text,
    validate_phone_number,
    validate_sender_id,
)


class TestValidatePhoneNumber:
    """Test validate_phone_number() function"""

    def test_valid_us_phone_number(self):
        """Test valid US phone number"""
        # Should not raise
        validate_phone_number("+15551234567")

    def test_valid_international_phone_numbers(self):
        """Test valid international phone numbers"""
        valid_numbers = [
            "+442071234567",  # UK
            "+33123456789",  # France
            "+491234567890",  # Germany
            "+81901234567",  # Japan
            "+861234567890",  # China
            "+911234567890",  # India
        ]

        for number in valid_numbers:
            validate_phone_number(number)  # Should not raise

    def test_invalid_phone_number_no_plus(self):
        """Test phone number without + prefix"""
        with pytest.raises(ValidationError, match="Invalid phone number format"):
            validate_phone_number("15551234567")

    def test_invalid_phone_number_too_short(self):
        """Test phone number too short"""
        with pytest.raises(ValidationError, match="Invalid phone number format"):
            validate_phone_number("+1")

    def test_invalid_phone_number_too_long(self):
        """Test phone number too long"""
        with pytest.raises(ValidationError, match="Invalid phone number format"):
            validate_phone_number("+1234567890123456")  # 16 digits

    def test_invalid_phone_number_with_letters(self):
        """Test phone number with letters"""
        with pytest.raises(ValidationError, match="Invalid phone number format"):
            validate_phone_number("+1555ABC4567")

    def test_invalid_phone_number_with_spaces(self):
        """Test phone number with spaces"""
        with pytest.raises(ValidationError, match="Invalid phone number format"):
            validate_phone_number("+1 555 123 4567")

    def test_invalid_phone_number_with_dashes(self):
        """Test phone number with dashes"""
        with pytest.raises(ValidationError, match="Invalid phone number format"):
            validate_phone_number("+1-555-123-4567")

    def test_invalid_phone_number_with_parentheses(self):
        """Test phone number with parentheses"""
        with pytest.raises(ValidationError, match="Invalid phone number format"):
            validate_phone_number("+1(555)1234567")

    def test_invalid_phone_number_starts_with_zero(self):
        """Test phone number starting with 0 after +"""
        with pytest.raises(ValidationError, match="Invalid phone number format"):
            validate_phone_number("+0551234567")

    def test_empty_phone_number(self):
        """Test empty phone number"""
        with pytest.raises(ValidationError, match="Phone number is required"):
            validate_phone_number("")

    def test_none_phone_number(self):
        """Test None phone number"""
        with pytest.raises(ValidationError, match="Phone number is required"):
            validate_phone_number(None)


class TestValidateMessageText:
    """Test validate_message_text() function"""

    def test_valid_short_text(self):
        """Test valid short message text"""
        validate_message_text("Hello, World!")

    def test_valid_long_text(self):
        """Test valid long message text"""
        long_text = "A" * 500
        validate_message_text(long_text)

    def test_very_long_text_warning(self):
        """Test that very long text triggers warning"""
        long_text = "A" * 1700

        with pytest.warns(UserWarning):
            validate_message_text(long_text)

    def test_empty_text(self):
        """Test empty message text"""
        with pytest.raises(ValidationError, match="Message text is required"):
            validate_message_text("")

    def test_none_text(self):
        """Test None message text"""
        with pytest.raises(ValidationError, match="Message text is required"):
            validate_message_text(None)

    def test_non_string_text(self):
        """Test non-string message text"""
        with pytest.raises(ValidationError, match="Message text must be a string"):
            validate_message_text(123)

    def test_text_with_unicode(self):
        """Test message text with unicode characters"""
        validate_message_text("Hello 世界! 🌍")

    def test_text_with_newlines(self):
        """Test message text with newlines"""
        validate_message_text("Line 1\nLine 2\nLine 3")

    def test_text_with_special_characters(self):
        """Test message text with special characters"""
        validate_message_text("Test: !@#$%^&*()_+-=[]{}|;':\",./<>?")


class TestValidateSenderID:
    """Test validate_sender_id() function"""

    def test_valid_alphanumeric_sender_id(self):
        """Test valid alphanumeric sender ID"""
        valid_ids = [
            "MyBrand",
            "Test123",
            "SENDLY",
            "Alert2FA",
            "ABC",
        ]

        for sender_id in valid_ids:
            validate_sender_id(sender_id)

    def test_valid_phone_number_sender_id(self):
        """Test valid phone number as sender ID"""
        validate_sender_id("+15551234567")

    def test_none_sender_id(self):
        """Test None sender ID (optional)"""
        validate_sender_id(None)  # Should not raise

    def test_empty_sender_id(self):
        """Test empty sender ID"""
        validate_sender_id("")  # Should not raise (optional field)

    def test_invalid_sender_id_too_short(self):
        """Test sender ID too short"""
        with pytest.raises(ValidationError, match="Invalid sender ID"):
            validate_sender_id("A")

    def test_invalid_sender_id_too_long(self):
        """Test sender ID too long"""
        with pytest.raises(ValidationError, match="Invalid sender ID"):
            validate_sender_id("ABCDEFGHIJKL")  # 12 chars

    def test_invalid_sender_id_special_characters(self):
        """Test sender ID with special characters"""
        with pytest.raises(ValidationError, match="Invalid sender ID"):
            validate_sender_id("Test@Brand")

    def test_invalid_sender_id_spaces(self):
        """Test sender ID with spaces"""
        with pytest.raises(ValidationError, match="Invalid sender ID"):
            validate_sender_id("My Brand")

    def test_invalid_sender_id_symbols(self):
        """Test sender ID with symbols"""
        invalid_ids = [
            "Test-Brand",
            "Test_Brand",
            "Test.Brand",
            "Test!",
        ]

        for sender_id in invalid_ids:
            with pytest.raises(ValidationError, match="Invalid sender ID"):
                validate_sender_id(sender_id)


class TestValidateLimit:
    """Test validate_limit() function"""

    def test_valid_limits(self):
        """Test valid limit values"""
        valid_limits = [1, 10, 50, 100]

        for limit in valid_limits:
            validate_limit(limit)

    def test_none_limit(self):
        """Test None limit (optional)"""
        validate_limit(None)  # Should not raise

    def test_invalid_limit_zero(self):
        """Test limit of 0"""
        with pytest.raises(ValidationError, match="Limit must be between 1 and 100"):
            validate_limit(0)

    def test_invalid_limit_negative(self):
        """Test negative limit"""
        with pytest.raises(ValidationError, match="Limit must be between 1 and 100"):
            validate_limit(-1)

    def test_invalid_limit_too_large(self):
        """Test limit > 100"""
        with pytest.raises(ValidationError, match="Limit must be between 1 and 100"):
            validate_limit(101)

    def test_invalid_limit_not_integer(self):
        """Test non-integer limit"""
        with pytest.raises(ValidationError, match="Limit must be an integer"):
            validate_limit("10")

    def test_invalid_limit_float(self):
        """Test float limit"""
        with pytest.raises(ValidationError, match="Limit must be an integer"):
            validate_limit(10.5)


class TestValidateMessageID:
    """Test validate_message_id() function"""

    def test_valid_prefixed_message_id(self):
        """Test valid prefixed message ID"""
        valid_ids = [
            "msg_123abc",
            "msg_test",
            "msg_ABC123xyz",
        ]

        for msg_id in valid_ids:
            validate_message_id(msg_id)

    def test_valid_uuid_message_id(self):
        """Test valid UUID message ID"""
        valid_uuids = [
            "550e8400-e29b-41d4-a716-446655440000",
            "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "12345678-1234-1234-1234-123456789abc",
        ]

        for msg_id in valid_uuids:
            validate_message_id(msg_id)

    def test_invalid_message_id_empty(self):
        """Test empty message ID"""
        with pytest.raises(ValidationError, match="Message ID is required"):
            validate_message_id("")

    def test_invalid_message_id_none(self):
        """Test None message ID"""
        with pytest.raises(ValidationError, match="Message ID is required"):
            validate_message_id(None)

    def test_invalid_message_id_not_string(self):
        """Test non-string message ID"""
        with pytest.raises(ValidationError, match="Message ID must be a string"):
            validate_message_id(123)

    def test_invalid_message_id_format(self):
        """Test invalid message ID format"""
        invalid_ids = [
            "invalid",
            "msg_",
            "test_123",
            "message_id",
            "123456",
        ]

        for msg_id in invalid_ids:
            with pytest.raises(ValidationError, match="Invalid message ID format"):
                validate_message_id(msg_id)

    def test_invalid_uuid_format(self):
        """Test invalid UUID format"""
        invalid_uuids = [
            "550e8400-e29b-41d4-a716",  # Too short
            "550e8400-e29b-41d4-a716-446655440000-extra",  # Too long
            "550e8400-e29b-41d4-g716-446655440000",  # Invalid character
        ]

        for msg_id in invalid_uuids:
            with pytest.raises(ValidationError, match="Invalid message ID format"):
                validate_message_id(msg_id)


class TestGetCountryFromPhone:
    """Test get_country_from_phone() function"""

    def test_us_phone_number(self):
        """Test US phone number"""
        assert get_country_from_phone("+15551234567") == "US"

    def test_uk_phone_number(self):
        """Test UK phone number"""
        assert get_country_from_phone("+442071234567") == "GB"

    def test_france_phone_number(self):
        """Test France phone number"""
        assert get_country_from_phone("+33123456789") == "FR"

    def test_germany_phone_number(self):
        """Test Germany phone number"""
        assert get_country_from_phone("+491234567890") == "DE"

    def test_japan_phone_number(self):
        """Test Japan phone number"""
        assert get_country_from_phone("+81901234567") == "JP"

    def test_china_phone_number(self):
        """Test China phone number"""
        assert get_country_from_phone("+861234567890") == "CN"

    def test_india_phone_number(self):
        """Test India phone number"""
        assert get_country_from_phone("+911234567890") == "IN"

    def test_australia_phone_number(self):
        """Test Australia phone number"""
        assert get_country_from_phone("+61412345678") == "AU"

    def test_unknown_country_code(self):
        """Test unknown country code"""
        result = get_country_from_phone("+999123456789")
        assert result is None

    def test_ambiguous_country_code(self):
        """Test country code that could be multiple countries"""
        # Country code 1 is US/Canada, we default to US
        assert get_country_from_phone("+12125551234") == "US"


class TestIsCountrySupported:
    """Test is_country_supported() function"""

    def test_domestic_countries_supported(self):
        """Test domestic countries are supported"""
        assert is_country_supported("US") is True
        assert is_country_supported("CA") is True

    def test_tier1_countries_supported(self):
        """Test tier 1 countries are supported"""
        tier1_countries = ["GB", "PL", "PT", "RO", "CZ", "HU", "CN", "KR", "IN"]

        for country in tier1_countries:
            assert is_country_supported(country) is True

    def test_tier2_countries_supported(self):
        """Test tier 2 countries are supported"""
        tier2_countries = ["FR", "ES", "SE", "NO", "DK", "FI", "JP", "AU"]

        for country in tier2_countries:
            assert is_country_supported(country) is True

    def test_tier3_countries_supported(self):
        """Test tier 3 countries are supported"""
        tier3_countries = ["DE", "IT", "NL", "BE", "AT", "CH", "MX", "IL"]

        for country in tier3_countries:
            assert is_country_supported(country) is True

    def test_unsupported_country(self):
        """Test unsupported country"""
        assert is_country_supported("XX") is False
        assert is_country_supported("ZZ") is False

    def test_case_insensitive(self):
        """Test case insensitivity"""
        assert is_country_supported("us") is True
        assert is_country_supported("gb") is True
        assert is_country_supported("Us") is True


class TestCalculateSegments:
    """Test calculate_segments() function"""

    def test_single_segment_gsm(self):
        """Test single segment GSM message"""
        assert calculate_segments("Hello, World!") == 1
        assert calculate_segments("A" * 160) == 1

    def test_multiple_segments_gsm(self):
        """Test multiple segment GSM message"""
        assert calculate_segments("A" * 161) == 2
        assert calculate_segments("A" * 306) == 2
        assert calculate_segments("A" * 307) == 3
        assert calculate_segments("A" * 459) == 3
        assert calculate_segments("A" * 460) == 4

    def test_single_segment_unicode(self):
        """Test single segment unicode message"""
        assert calculate_segments("Hello 世界") == 1
        assert calculate_segments("🌍" * 70) == 1

    def test_multiple_segments_unicode(self):
        """Test multiple segment unicode message"""
        assert calculate_segments("🌍" * 71) == 2
        assert calculate_segments("世界" * 68) == 3

    def test_empty_message(self):
        """Test empty message"""
        assert calculate_segments("") == 1

    def test_single_character(self):
        """Test single character"""
        assert calculate_segments("A") == 1
        assert calculate_segments("世") == 1

    def test_gsm_special_characters(self):
        """Test GSM special characters"""
        # These are all GSM-7 characters
        assert calculate_segments("!@#$%^&*()") == 1
        assert calculate_segments("ABC123xyz") == 1

    def test_mixed_gsm_and_unicode(self):
        """Test mixed GSM and unicode (forces unicode encoding)"""
        # Emoji forces unicode encoding
        text = "A" * 69 + "🌍"
        assert calculate_segments(text) == 1  # 70 chars in unicode

        text = "A" * 70 + "🌍"
        assert calculate_segments(text) == 2  # 71 chars in unicode

    def test_newlines_and_whitespace(self):
        """Test newlines and whitespace"""
        assert calculate_segments("Line 1\nLine 2\nLine 3") == 1
        assert calculate_segments("   spaces   ") == 1

    def test_very_long_message(self):
        """Test very long message"""
        long_text = "A" * 1000
        segments = calculate_segments(long_text)
        assert segments == 7  # 1000 / 153 = 6.5, rounds up to 7


class TestValidationEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_phone_number_exactly_15_digits(self):
        """Test phone number with exactly 15 digits (max E.164)"""
        validate_phone_number("+123456789012345")

    def test_message_text_exactly_160_chars(self):
        """Test message text with exactly 160 characters"""
        text = "A" * 160
        validate_message_text(text)
        assert calculate_segments(text) == 1

    def test_message_text_exactly_161_chars(self):
        """Test message text with exactly 161 characters"""
        text = "A" * 161
        validate_message_text(text)
        assert calculate_segments(text) == 2

    def test_sender_id_exactly_2_chars(self):
        """Test sender ID with exactly 2 characters (minimum)"""
        validate_sender_id("AB")

    def test_sender_id_exactly_11_chars(self):
        """Test sender ID with exactly 11 characters (maximum)"""
        validate_sender_id("ABCDEFGHIJK")

    def test_limit_exactly_1(self):
        """Test limit of exactly 1 (minimum)"""
        validate_limit(1)

    def test_limit_exactly_100(self):
        """Test limit of exactly 100 (maximum)"""
        validate_limit(100)

    def test_validate_none_optional_fields(self):
        """Test validating None for optional fields"""
        validate_sender_id(None)  # Optional
        validate_limit(None)  # Optional

    def test_unicode_phone_number_rejected(self):
        """Test that unicode in phone number is rejected"""
        with pytest.raises(ValidationError):
            validate_phone_number("+１５５５１２３４５６７")  # Full-width digits

    def test_zero_width_characters_in_text(self):
        """Test message text with zero-width characters"""
        text = "Hello\u200bWorld"  # Zero-width space
        validate_message_text(text)
