"""
Numbers Resource - Search, list, and buy phone numbers

Exposes the public numbers API: discover the countries Sendly sells numbers
in, search for available numbers, list the numbers you already own, and buy a
number. Pricing on available numbers is already customer-priced.

When a purchase needs documents or payment, ``buy()`` returns a response whose
``status`` is ``documents_required`` or ``payment_required`` and whose
``action`` carries a hosted Sendly page (``url``) plus a short ``code``. Hand
the user the URL + code; once they complete the page, call ``buy()`` again with
the SAME arguments PLUS ``action_code`` set to that code. Polling the action to
completion is the CLI's job, not the SDK's.
"""

from typing import Any, Dict, Optional

from pydantic import ValidationError as PydanticValidationError

from ..errors import SendlyError
from ..types import (
    AvailableNumbersResponse,
    BuyNumberResponse,
    NumberCountriesResponse,
    OwnedNumbersResponse,
)
from ..utils.http import AsyncHttpClient, HttpClient


class NumbersResource:
    """Numbers API resource (sync)

    Example:
        >>> countries = client.numbers.list_countries()
        >>> available = client.numbers.list_available(country='GB', type='mobile')
        >>> result = client.numbers.buy(
        ...     phone_number=available.numbers[0].phone_number,
        ...     country_code='GB',
        ...     phone_number_type='mobile',
        ...     monthly_cost=available.numbers[0].monthly_cost,
        ... )
    """

    def __init__(self, http: HttpClient):
        self._http = http

    def list_countries(self) -> NumberCountriesResponse:
        """List the countries where numbers can be searched and purchased."""
        data = self._http.request(method="GET", path="/numbers/countries")
        try:
            return NumberCountriesResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def list_available(
        self,
        country: str,
        type: str,
        contains: Optional[str] = None,
    ) -> AvailableNumbersResponse:
        """Search for available numbers, already priced for the customer.

        Args:
            country: ISO 3166-1 alpha-2 country code (e.g. ``GB``).
            type: Number type to search for (e.g. ``mobile``).
            contains: Optional digit pattern the number should contain.
        """
        params: Dict[str, Any] = {"country": country, "type": type}
        if contains is not None:
            params["contains"] = contains

        data = self._http.request(method="GET", path="/numbers/available", params=params)
        try:
            return AvailableNumbersResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def list(self) -> OwnedNumbersResponse:
        """List the numbers the account already owns."""
        data = self._http.request(method="GET", path="/numbers")
        try:
            return OwnedNumbersResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def buy(
        self,
        phone_number: str,
        country_code: str,
        phone_number_type: str,
        monthly_cost: str,
        action_code: Optional[str] = None,
    ) -> BuyNumberResponse:
        """Buy a number.

        Returns a response whose ``status`` is ``provisioning``,
        ``documents_required``, or ``payment_required``. When documents or
        payment are required, the ``action`` field carries a hosted Sendly page
        URL + a short code; hand them to the user, then call ``buy()`` again
        with the same arguments plus ``action_code`` set to the code of the
        completed action.

        Args:
            phone_number: Number to buy, in E.164 format.
            country_code: ISO 3166-1 alpha-2 country code.
            phone_number_type: Number type (e.g. ``mobile``).
            monthly_cost: Monthly cost as returned by :meth:`list_available`.
            action_code: Code from a completed documents/payment action.
        """
        body: Dict[str, Any] = {
            "phoneNumber": phone_number,
            "countryCode": country_code,
            "phoneNumberType": phone_number_type,
            "monthlyCost": monthly_cost,
        }
        if action_code is not None:
            body["actionCode"] = action_code

        data = self._http.request(method="POST", path="/numbers/buy", body=body)
        try:
            return BuyNumberResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e


class AsyncNumbersResource:
    """Numbers API resource (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def list_countries(self) -> NumberCountriesResponse:
        """List the countries where numbers can be searched and purchased."""
        data = await self._http.request(method="GET", path="/numbers/countries")
        try:
            return NumberCountriesResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def list_available(
        self,
        country: str,
        type: str,
        contains: Optional[str] = None,
    ) -> AvailableNumbersResponse:
        """Search for available numbers, already priced for the customer."""
        params: Dict[str, Any] = {"country": country, "type": type}
        if contains is not None:
            params["contains"] = contains

        data = await self._http.request(method="GET", path="/numbers/available", params=params)
        try:
            return AvailableNumbersResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def list(self) -> OwnedNumbersResponse:
        """List the numbers the account already owns."""
        data = await self._http.request(method="GET", path="/numbers")
        try:
            return OwnedNumbersResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def buy(
        self,
        phone_number: str,
        country_code: str,
        phone_number_type: str,
        monthly_cost: str,
        action_code: Optional[str] = None,
    ) -> BuyNumberResponse:
        """Buy a number. See :meth:`NumbersResource.buy`."""
        body: Dict[str, Any] = {
            "phoneNumber": phone_number,
            "countryCode": country_code,
            "phoneNumberType": phone_number_type,
            "monthlyCost": monthly_cost,
        }
        if action_code is not None:
            body["actionCode"] = action_code

        data = await self._http.request(method="POST", path="/numbers/buy", body=body)
        try:
            return BuyNumberResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e


def _invalid_response(e: PydanticValidationError) -> SendlyError:
    """Wrap a pydantic schema error as a SendlyError, matching the SDK's idiom."""
    return SendlyError(
        message=f"Invalid API response format: {e}",
        code="invalid_response",
        status_code=200,
    )
