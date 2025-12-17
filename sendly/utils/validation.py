"""
Input Validation Utilities

Functions for validating API inputs.
"""

import re
from typing import Optional

from ..errors import ValidationError
from ..types import ALL_SUPPORTED_COUNTRIES


def validate_phone_number(phone: str) -> None:
    """
    Validate phone number format (E.164)

    Args:
        phone: Phone number to validate

    Raises:
        ValidationError: If phone number is invalid
    """
    if not phone:
        raise ValidationError("Phone number is required")

    # E.164 format: + followed by 1-15 digits
    e164_pattern = r"^\+[1-9]\d{1,14}$"

    if not re.match(e164_pattern, phone):
        raise ValidationError(
            f"Invalid phone number format: {phone}. Expected E.164 format (e.g., +15551234567)"
        )


def validate_message_text(text: str) -> None:
    """
    Validate message text

    Args:
        text: Message text to validate

    Raises:
        ValidationError: If text is invalid
    """
    if not text:
        raise ValidationError("Message text is required")

    if not isinstance(text, str):
        raise ValidationError("Message text must be a string")

    # Warn about very long messages
    if len(text) > 1600:
        import warnings

        warnings.warn(
            f"Message is {len(text)} characters. "
            f"This will be split into {calculate_segments(text)} segments."
        )


def validate_sender_id(from_: Optional[str]) -> None:
    """
    Validate sender ID

    Args:
        from_: Sender ID to validate

    Raises:
        ValidationError: If sender ID is invalid
    """
    if not from_:
        return  # Optional field

    # Phone number format (toll-free)
    if from_.startswith("+"):
        validate_phone_number(from_)
        return

    # Alphanumeric sender ID (2-11 characters)
    alphanumeric_pattern = r"^[a-zA-Z0-9]{2,11}$"

    if not re.match(alphanumeric_pattern, from_):
        raise ValidationError(
            f"Invalid sender ID: {from_}. "
            "Must be 2-11 alphanumeric characters or a valid phone number."
        )


def validate_limit(limit: Optional[int]) -> None:
    """
    Validate list limit

    Args:
        limit: Limit value to validate

    Raises:
        ValidationError: If limit is invalid
    """
    if limit is None:
        return

    if not isinstance(limit, int):
        raise ValidationError("Limit must be an integer")

    if limit < 1 or limit > 100:
        raise ValidationError("Limit must be between 1 and 100")


def validate_message_id(id: str) -> None:
    """
    Validate message ID format

    Args:
        id: Message ID to validate

    Raises:
        ValidationError: If ID is invalid
    """
    if not id:
        raise ValidationError("Message ID is required")

    if not isinstance(id, str):
        raise ValidationError("Message ID must be a string")

    # UUID format or prefixed format
    uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    prefixed_pattern = r"^msg_[a-zA-Z0-9_]+$"

    if not (re.match(uuid_pattern, id, re.IGNORECASE) or re.match(prefixed_pattern, id)):
        raise ValidationError(f"Invalid message ID format: {id}")


def get_country_from_phone(phone: str) -> Optional[str]:
    """
    Get country code from phone number

    Args:
        phone: Phone number in E.164 format

    Returns:
        ISO country code or None if not found
    """
    # Remove + prefix
    digits = phone.lstrip("+")

    # Check US/Canada (country code 1)
    if digits.startswith("1") and len(digits) == 11:
        return "US"  # Could be CA, but we treat as domestic

    # Map of country codes to ISO codes
    country_prefixes = {
        "44": "GB",
        "48": "PL",
        "351": "PT",
        "40": "RO",
        "420": "CZ",
        "36": "HU",
        "86": "CN",
        "82": "KR",
        "91": "IN",
        "63": "PH",
        "66": "TH",
        "84": "VN",
        "33": "FR",
        "34": "ES",
        "46": "SE",
        "47": "NO",
        "45": "DK",
        "358": "FI",
        "353": "IE",
        "81": "JP",
        "61": "AU",
        "64": "NZ",
        "65": "SG",
        "852": "HK",
        "60": "MY",
        "62": "ID",
        "55": "BR",
        "54": "AR",
        "56": "CL",
        "57": "CO",
        "27": "ZA",
        "30": "GR",
        "49": "DE",
        "39": "IT",
        "31": "NL",
        "32": "BE",
        "43": "AT",
        "41": "CH",
        "52": "MX",
        "972": "IL",
        "971": "AE",
        "966": "SA",
        "20": "EG",
        "234": "NG",
        "254": "KE",
        "886": "TW",
        "92": "PK",
        "90": "TR",
    }

    # Try to match country prefixes (longest first)
    sorted_prefixes = sorted(country_prefixes.keys(), key=len, reverse=True)

    for prefix in sorted_prefixes:
        if digits.startswith(prefix):
            return country_prefixes[prefix]

    return None


def is_country_supported(country_code: str) -> bool:
    """
    Check if a country is supported

    Args:
        country_code: ISO country code

    Returns:
        True if country is supported
    """
    return country_code.upper() in ALL_SUPPORTED_COUNTRIES


def calculate_segments(text: str) -> int:
    """
    Calculate number of SMS segments for a message

    Args:
        text: Message text

    Returns:
        Number of SMS segments
    """
    # Check if message contains non-GSM characters (requires UCS-2 encoding)
    # Simple check: any character outside basic ASCII range
    is_unicode = any(ord(c) > 127 for c in text)

    # GSM: 160 chars single, 153 chars per segment for multi
    # UCS-2: 70 chars single, 67 chars per segment for multi
    single_limit = 70 if is_unicode else 160
    multi_limit = 67 if is_unicode else 153

    if len(text) <= single_limit:
        return 1

    return (len(text) + multi_limit - 1) // multi_limit
