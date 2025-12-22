"""
Account Resource

Access account information, credit balance, and API keys.
"""

from typing import Any, Dict, List, Optional

from ..types import Account, ApiKey, Credits, CreditTransaction
from ..utils.http import AsyncHttpClient, HttpClient


def _transform_response(data: Dict[str, Any], key_map: Dict[str, str]) -> Dict[str, Any]:
    """Transform snake_case API response to camelCase for pydantic models."""
    result = {}
    for key, value in data.items():
        new_key = key_map.get(key, key)
        result[new_key] = value
    return result


CREDITS_KEY_MAP = {
    "reserved_balance": "reservedBalance",
    "available_balance": "availableBalance",
}

TRANSACTION_KEY_MAP = {
    "balance_after": "balanceAfter",
    "message_id": "messageId",
    "created_at": "createdAt",
}

API_KEY_MAP = {
    "last_four": "lastFour",
    "created_at": "createdAt",
    "last_used_at": "lastUsedAt",
    "expires_at": "expiresAt",
    "is_revoked": "isRevoked",
}

ACCOUNT_KEY_MAP = {
    "created_at": "createdAt",
}


class AccountResource:
    """
    Account API resource (synchronous)

    Access account information, credit balance, and API keys.

    Example:
        >>> # Get credit balance
        >>> credits = client.account.get_credits()
        >>> print(f'Available: {credits.available_balance} credits')
        >>>
        >>> # Get transaction history
        >>> transactions = client.account.get_credit_transactions()
        >>>
        >>> # List API keys
        >>> keys = client.account.list_api_keys()
    """

    def __init__(self, http: HttpClient):
        self._http = http

    def get(self) -> Account:
        """
        Get account information.

        Returns:
            Account details
        """
        response = self._http.request("GET", "/account")
        return Account(**_transform_response(response, ACCOUNT_KEY_MAP))

    def get_credits(self) -> Credits:
        """
        Get credit balance.

        Returns:
            Current credit balance and reserved credits
        """
        response = self._http.request("GET", "/credits")
        return Credits(**_transform_response(response, CREDITS_KEY_MAP))

    def get_credit_transactions(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[CreditTransaction]:
        """
        Get credit transaction history.

        Args:
            limit: Maximum number of transactions to return
            offset: Number of transactions to skip

        Returns:
            Array of credit transactions
        """
        params = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._http.request("GET", "/credits/transactions", params=params)
        return [CreditTransaction(**_transform_response(t, TRANSACTION_KEY_MAP)) for t in response]

    def list_api_keys(self) -> List[ApiKey]:
        """
        List API keys for the account.

        Note: This returns key metadata, not the actual secret keys.

        Returns:
            Array of API keys
        """
        response = self._http.request("GET", "/keys")
        return [ApiKey(**_transform_response(k, API_KEY_MAP)) for k in response]

    def get_api_key(self, key_id: str) -> ApiKey:
        """
        Get a specific API key by ID.

        Args:
            key_id: API key ID

        Returns:
            API key details
        """
        response = self._http.request("GET", f"/keys/{key_id}")
        return ApiKey(**_transform_response(response, API_KEY_MAP))

    def get_api_key_usage(self, key_id: str) -> Dict[str, Any]:
        """
        Get usage statistics for an API key.

        Args:
            key_id: API key ID

        Returns:
            Usage statistics
        """
        response = self._http.request("GET", f"/keys/{key_id}/usage")
        return response


class AsyncAccountResource:
    """
    Account API resource (asynchronous)

    Async version of the account resource for use with asyncio.
    """

    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def get(self) -> Account:
        """Get account information."""
        response = await self._http.request("GET", "/account")
        return Account(**_transform_response(response, ACCOUNT_KEY_MAP))

    async def get_credits(self) -> Credits:
        """Get credit balance."""
        response = await self._http.request("GET", "/credits")
        return Credits(**_transform_response(response, CREDITS_KEY_MAP))

    async def get_credit_transactions(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[CreditTransaction]:
        """Get credit transaction history."""
        params = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = await self._http.request("GET", "/credits/transactions", params=params)
        return [CreditTransaction(**_transform_response(t, TRANSACTION_KEY_MAP)) for t in response]

    async def list_api_keys(self) -> List[ApiKey]:
        """List API keys for the account."""
        response = await self._http.request("GET", "/keys")
        return [ApiKey(**_transform_response(k, API_KEY_MAP)) for k in response]

    async def get_api_key(self, key_id: str) -> ApiKey:
        """Get a specific API key by ID."""
        response = await self._http.request("GET", f"/keys/{key_id}")
        return ApiKey(**_transform_response(response, API_KEY_MAP))

    async def get_api_key_usage(self, key_id: str) -> Dict[str, Any]:
        """Get usage statistics for an API key."""
        response = await self._http.request("GET", f"/keys/{key_id}/usage")
        return response
