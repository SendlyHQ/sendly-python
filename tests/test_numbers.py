"""
Tests for Numbers resource (list_countries, list_available, list, buy)
"""

import pytest
from pytest_httpx import HTTPXMock

from sendly import AsyncSendly, Sendly
from sendly.errors import NotFoundError, ValidationError
from sendly.types import (
    AvailableNumbersResponse,
    BuyNumberResponse,
    NumberCountriesResponse,
    OwnedNumbersResponse,
)


@pytest.fixture
def mock_countries():
    return {
        "countries": [
            {"code": "GB", "name": "United Kingdom", "numberTypes": ["mobile", "local"]},
            {"code": "US", "name": "United States", "numberTypes": ["local", "toll_free"]},
        ]
    }


@pytest.fixture
def mock_available():
    return {
        "numbers": [
            {
                "phoneNumber": "+447400000001",
                "country": "GB",
                "numberType": "mobile",
                "monthlyCost": "3.50",
                "currency": "GBP",
            },
            {
                "phoneNumber": "+447400000002",
                "country": "GB",
                "numberType": "mobile",
                "monthlyCost": "3.50",
                "currency": "GBP",
            },
        ]
    }


@pytest.fixture
def mock_owned():
    return {
        "numbers": [
            {
                "id": "num_123",
                "phoneNumber": "+447400000001",
                "status": "active",
                "source": "purchased",
                "countryCode": "GB",
                "phoneNumberType": "mobile",
                "monthlyCostCents": 350,
            }
        ]
    }


@pytest.fixture
def mock_buy_provisioning():
    return {
        "status": "provisioning",
        "number": {
            "id": "num_123",
            "phoneNumber": "+447400000001",
            "status": "provisioning",
        },
    }


@pytest.fixture
def mock_buy_documents_required():
    return {
        "status": "documents_required",
        "requirements": [{"type": "document", "field": "proof_of_address"}],
        "action": {
            "url": "https://sendly.live/a/abc123",
            "actionCode": "0123456789abcdef0123456789abcdef",
            "code": "ABC23456",
            "expiresAt": 1749463200000,
        },
    }


class TestListCountries:
    def test_list_countries(self, api_key, mock_countries, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/numbers/countries",
            method="GET",
            json=mock_countries,
        )

        result = client.numbers.list_countries()

        assert isinstance(result, NumberCountriesResponse)
        assert len(result.countries) == 2
        assert result.countries[0].code == "GB"
        assert result.countries[0].name == "United Kingdom"
        assert result.countries[0].number_types == ["mobile", "local"]

        client.close()


class TestListAvailable:
    def test_list_available(self, api_key, mock_available, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/numbers/available?country=GB&type=mobile",
            method="GET",
            json=mock_available,
        )

        result = client.numbers.list_available(country="GB", type="mobile")

        assert isinstance(result, AvailableNumbersResponse)
        assert len(result.numbers) == 2
        assert result.numbers[0].phone_number == "+447400000001"
        assert result.numbers[0].number_type == "mobile"
        assert result.numbers[0].monthly_cost == "3.50"
        assert result.numbers[0].currency == "GBP"

        client.close()

    def test_list_available_with_contains(self, api_key, mock_available, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/numbers/available?country=GB&type=mobile&contains=777",
            method="GET",
            json=mock_available,
        )

        result = client.numbers.list_available(country="GB", type="mobile", contains="777")

        assert isinstance(result, AvailableNumbersResponse)

        request = httpx_mock.get_request()
        assert "contains=777" in str(request.url)

        client.close()


class TestList:
    def test_list_owned(self, api_key, mock_owned, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/numbers",
            method="GET",
            json=mock_owned,
        )

        result = client.numbers.list()

        assert isinstance(result, OwnedNumbersResponse)
        assert len(result.numbers) == 1
        num = result.numbers[0]
        assert num.id == "num_123"
        assert num.phone_number == "+447400000001"
        assert num.status == "active"
        assert num.source == "purchased"
        assert num.country_code == "GB"
        assert num.phone_number_type == "mobile"
        assert num.monthly_cost_cents == 350

        client.close()


class TestBuy:
    def test_buy_provisioning(self, api_key, mock_buy_provisioning, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/numbers/buy",
            method="POST",
            status_code=202,
            json=mock_buy_provisioning,
        )

        result = client.numbers.buy(
            phone_number="+447400000001",
            country_code="GB",
            phone_number_type="mobile",
            monthly_cost="3.50",
        )

        assert isinstance(result, BuyNumberResponse)
        assert result.status == "provisioning"
        assert result.number is not None
        assert result.number.id == "num_123"
        assert result.action is None

        request = httpx_mock.get_request()
        body = request.read().decode()
        assert '"phoneNumber"' in body
        assert '"countryCode"' in body
        assert '"phoneNumberType"' in body
        assert '"monthlyCost"' in body
        assert "actionCode" not in body

        client.close()

    def test_buy_documents_required(
        self, api_key, mock_buy_documents_required, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/numbers/buy",
            method="POST",
            status_code=202,
            json=mock_buy_documents_required,
        )

        result = client.numbers.buy(
            phone_number="+447400000001",
            country_code="GB",
            phone_number_type="mobile",
            monthly_cost="3.50",
        )

        assert result.status == "documents_required"
        assert result.number is None
        assert result.requirements == [{"type": "document", "field": "proof_of_address"}]
        assert result.action is not None
        assert result.action.url == "https://sendly.live/a/abc123"
        assert result.action.action_code == "0123456789abcdef0123456789abcdef"
        assert result.action.code == "ABC23456"
        assert result.action.expires_at == 1749463200000

        client.close()

    def test_buy_with_action_code(
        self, api_key, mock_buy_provisioning, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/numbers/buy",
            method="POST",
            status_code=202,
            json=mock_buy_provisioning,
        )

        client.numbers.buy(
            phone_number="+447400000001",
            country_code="GB",
            phone_number_type="mobile",
            monthly_cost="3.50",
            action_code="ABC123",
        )

        request = httpx_mock.get_request()
        body = request.read().decode()
        assert '"actionCode"' in body
        assert "ABC123" in body

        client.close()

    def test_buy_validation_error_400(self, api_key, mock_error_response, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/numbers/buy",
            method="POST",
            status_code=400,
            json=mock_error_response("invalid_request", "monthlyCost mismatch"),
        )

        with pytest.raises(ValidationError):
            client.numbers.buy(
                phone_number="+447400000001",
                country_code="GB",
                phone_number_type="mobile",
                monthly_cost="1.00",
            )

        client.close()

    def test_list_available_not_found_404(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/numbers/available?country=ZZ&type=mobile",
            method="GET",
            status_code=404,
            json=mock_error_response("not_found", "Country not supported"),
        )

        with pytest.raises(NotFoundError):
            client.numbers.list_available(country="ZZ", type="mobile")

        client.close()


class TestAsyncNumbers:
    async def test_async_list_countries(self, api_key, mock_countries, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/numbers/countries",
            method="GET",
            json=mock_countries,
        )

        result = await client.numbers.list_countries()

        assert isinstance(result, NumberCountriesResponse)
        assert result.countries[0].code == "GB"

        await client.close()

    async def test_async_buy(self, api_key, mock_buy_provisioning, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/numbers/buy",
            method="POST",
            status_code=202,
            json=mock_buy_provisioning,
        )

        result = await client.numbers.buy(
            phone_number="+447400000001",
            country_code="GB",
            phone_number_type="mobile",
            monthly_cost="3.50",
        )

        assert isinstance(result, BuyNumberResponse)
        assert result.status == "provisioning"

        await client.close()
