"""
Tests for 10DLC resource (brands, qualify, campaigns, assignments)
"""

import json

import pytest
from pytest_httpx import HTTPXMock

from sendly import AsyncSendly, Sendly
from sendly.errors import NotFoundError, SendlyError
from sendly.types import (
    TenDlcAssignmentListResponse,
    TenDlcAssignmentResponse,
    TenDlcBrandListResponse,
    TenDlcBrandResponse,
    TenDlcCampaignListResponse,
    TenDlcCampaignResponse,
    TenDlcQualifyResponse,
)


@pytest.fixture
def mock_brand():
    return {
        "id": "brd_123",
        "legalName": "Acme Holdings LLC",
        "dba": "Acme",
        "entityType": "PRIVATE_PROFIT",
        "ein": "12-3456789",
        "vertical": "TECHNOLOGY",
        "website": "https://acme.example",
        "status": "pending",
        "identityStatus": None,
        "failureReasons": None,
        "createdAt": "2026-06-30T10:00:00Z",
        "updatedAt": "2026-06-30T10:00:00Z",
    }


@pytest.fixture
def mock_verified_brand(mock_brand):
    return {**mock_brand, "status": "verified", "identityStatus": "VERIFIED"}


@pytest.fixture
def mock_qualify():
    return {
        "useCase": "MIXED",
        "qualified": True,
        "reason": None,
        "throughput": {"tier": "Standard", "carriersReady": 4},
    }


@pytest.fixture
def mock_campaign():
    return {
        "id": "cmp_123",
        "brandId": "brd_123",
        "useCase": "MIXED",
        "subUseCases": [],
        "description": "Order updates and support replies",
        "status": "pending",
        "sampleMessages": ["Your order #123 has shipped!"],
        "throughput": None,
        "failureReasons": None,
        "createdAt": "2026-06-30T11:00:00Z",
        "updatedAt": "2026-06-30T11:00:00Z",
    }


@pytest.fixture
def mock_active_campaign(mock_campaign):
    return {
        **mock_campaign,
        "status": "active",
        "throughput": {"tier": "Standard", "carriersReady": 5},
    }


@pytest.fixture
def mock_assignment():
    return {
        "id": "asg_123",
        "campaignId": "cmp_123",
        "phoneNumber": "+15551234567",
        "status": "Under review",
        "assignedAt": None,
    }


class TestListBrands:
    def test_list_brands(self, api_key, mock_brand, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/tendlc/brands",
            method="GET",
            json={"data": [mock_brand]},
        )

        result = client.ten_dlc.list_brands()

        assert isinstance(result, TenDlcBrandListResponse)
        assert len(result.data) == 1
        brand = result.data[0]
        assert brand.id == "brd_123"
        assert brand.legal_name == "Acme Holdings LLC"
        assert brand.dba == "Acme"
        assert brand.entity_type == "PRIVATE_PROFIT"
        assert brand.ein == "12-3456789"
        assert brand.status == "pending"
        assert brand.identity_status is None
        assert brand.failure_reasons is None

        client.close()


class TestCreateBrand:
    def test_create_brand(self, api_key, mock_brand, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/tendlc/brands",
            method="POST",
            status_code=201,
            json={"data": mock_brand},
        )

        result = client.ten_dlc.create_brand(
            legal_name="Acme Holdings LLC",
            ein="12-3456789",
            website="https://acme.example",
            email="ops@acme.example",
        )

        assert isinstance(result, TenDlcBrandResponse)
        assert result.data.id == "brd_123"
        assert result.data.status == "pending"

        request = httpx_mock.get_request()
        body = request.read().decode()
        assert '"legalName"' in body
        assert '"ein"' in body
        assert '"website"' in body
        assert '"email"' in body
        assert "entityType" not in body
        assert "mobilePhone" not in body
        assert "verificationId" not in body

        client.close()

    def test_create_brand_with_all_fields(self, api_key, mock_brand, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/tendlc/brands",
            method="POST",
            status_code=201,
            json={"data": mock_brand},
        )

        client.ten_dlc.create_brand(
            legal_name="Acme Holdings LLC",
            dba="Acme",
            ein="12-3456789",
            entity_type="SOLE_PROPRIETOR",
            vertical="TECHNOLOGY",
            website="https://acme.example",
            email="ops@acme.example",
            phone="+15550001111",
            mobile_phone="+15550002222",
            street="1 Main St",
            city="Austin",
            state="TX",
            postal_code="78701",
            country="US",
            verification_id="ver_123",
        )

        request = httpx_mock.get_request()
        body = request.read().decode()
        assert '"entityType"' in body
        assert '"mobilePhone"' in body
        assert '"postalCode"' in body
        assert '"verificationId"' in body
        assert "SOLE_PROPRIETOR" in body

        client.close()

    def test_create_brand_permission_error(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/tendlc/brands",
            method="POST",
            status_code=403,
            json=mock_error_response("insufficient_permission", "Your role cannot register brands"),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.ten_dlc.create_brand(legal_name="Acme Holdings LLC")

        assert exc_info.value.code == "insufficient_permission"

        client.close()


class TestGetBrand:
    def test_get_brand(self, api_key, mock_verified_brand, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/tendlc/brands/brd_123",
            method="GET",
            json={"data": mock_verified_brand},
        )

        result = client.ten_dlc.get_brand("brd_123")

        assert isinstance(result, TenDlcBrandResponse)
        assert result.data.status == "verified"
        assert result.data.identity_status == "VERIFIED"

        client.close()

    def test_get_brand_not_found_404(self, api_key, mock_error_response, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/tendlc/brands/brd_missing",
            method="GET",
            status_code=404,
            json=mock_error_response("not_found", "Not found"),
        )

        with pytest.raises(NotFoundError):
            client.ten_dlc.get_brand("brd_missing")

        client.close()


class TestQualify:
    def test_qualify(self, api_key, mock_qualify, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/tendlc/brands/brd_123/qualify/MIXED",
            method="GET",
            json={"data": mock_qualify},
        )

        result = client.ten_dlc.qualify("brd_123", "MIXED")

        assert isinstance(result, TenDlcQualifyResponse)
        assert result.data.use_case == "MIXED"
        assert result.data.qualified is True
        assert result.data.reason is None
        assert result.data.throughput is not None
        assert result.data.throughput.tier == "Standard"
        assert result.data.throughput.carriers_ready == 4

        client.close()

    def test_qualify_not_qualified(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/tendlc/brands/brd_123/qualify/MARKETING",
            method="GET",
            json={
                "data": {
                    "useCase": "MARKETING",
                    "qualified": False,
                    "reason": "Use case not accepted for this brand",
                    "throughput": None,
                }
            },
        )

        result = client.ten_dlc.qualify("brd_123", "MARKETING")

        assert result.data.qualified is False
        assert result.data.reason == "Use case not accepted for this brand"
        assert result.data.throughput is None

        client.close()


class TestListCampaigns:
    def test_list_campaigns(self, api_key, mock_campaign, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/tendlc/campaigns",
            method="GET",
            json={"data": [mock_campaign]},
        )

        result = client.ten_dlc.list_campaigns()

        assert isinstance(result, TenDlcCampaignListResponse)
        assert len(result.data) == 1
        campaign = result.data[0]
        assert campaign.id == "cmp_123"
        assert campaign.brand_id == "brd_123"
        assert campaign.use_case == "MIXED"
        assert campaign.status == "pending"
        assert campaign.sample_messages == ["Your order #123 has shipped!"]
        assert campaign.throughput is None

        client.close()


class TestCreateCampaign:
    def test_create_campaign(self, api_key, mock_campaign, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/tendlc/campaigns",
            method="POST",
            status_code=201,
            json={"data": mock_campaign},
        )

        result = client.ten_dlc.create_campaign(
            brand_id="brd_123",
            use_case="MIXED",
            description="Order updates and support replies",
            message_flow="Customers opt in at checkout on acme.example",
            sample_messages=["Your order #123 has shipped!"],
        )

        assert isinstance(result, TenDlcCampaignResponse)
        assert result.data.id == "cmp_123"
        assert result.data.status == "pending"

        request = httpx_mock.get_request()
        body = request.read().decode()
        assert '"brandId"' in body
        assert '"useCase"' in body
        assert '"description"' in body
        assert '"messageFlow"' in body
        assert '"sampleMessages"' in body
        assert "optOutKeywords" not in body
        assert "embeddedLink" not in body

        client.close()

    def test_create_campaign_with_optional_fields(
        self, api_key, mock_campaign, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/tendlc/campaigns",
            method="POST",
            status_code=201,
            json={"data": mock_campaign},
        )

        client.ten_dlc.create_campaign(
            brand_id="brd_123",
            use_case="MIXED",
            description="Order updates and support replies",
            message_flow="Customers opt in at checkout on acme.example",
            sample_messages=["Your order #123 has shipped!"],
            sub_use_cases=["ACCOUNT_NOTIFICATION"],
            opt_out_keywords="STOP",
            help_message="Reply STOP to opt out",
            embedded_link=True,
            embedded_phone=False,
        )

        request = httpx_mock.get_request()
        body = request.read().decode()
        assert '"subUseCases"' in body
        assert '"optOutKeywords"' in body
        assert '"helpMessage"' in body
        payload = json.loads(body)
        assert payload["embeddedLink"] is True
        assert payload["embeddedPhone"] is False

        client.close()

    def test_create_campaign_brand_not_verified_400(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/tendlc/campaigns",
            method="POST",
            status_code=400,
            json=mock_error_response("brand_not_verified", "Brand must be verified first"),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.ten_dlc.create_campaign(
                brand_id="brd_123",
                use_case="MIXED",
                description="Order updates",
                message_flow="Customers opt in at checkout",
                sample_messages=["Your order has shipped!"],
            )

        assert exc_info.value.code == "brand_not_verified"

        client.close()


class TestGetCampaign:
    def test_get_campaign(self, api_key, mock_active_campaign, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/tendlc/campaigns/cmp_123",
            method="GET",
            json={"data": mock_active_campaign},
        )

        result = client.ten_dlc.get_campaign("cmp_123")

        assert isinstance(result, TenDlcCampaignResponse)
        assert result.data.status == "active"
        assert result.data.throughput is not None
        assert result.data.throughput.carriers_ready == 5

        client.close()

    def test_get_campaign_not_found_404(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/tendlc/campaigns/cmp_missing",
            method="GET",
            status_code=404,
            json=mock_error_response("not_found", "Not found"),
        )

        with pytest.raises(NotFoundError):
            client.ten_dlc.get_campaign("cmp_missing")

        client.close()


class TestAssignNumber:
    def test_assign_number(self, api_key, mock_assignment, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/tendlc/campaigns/cmp_123/assign",
            method="POST",
            status_code=201,
            json={"data": mock_assignment},
        )

        result = client.ten_dlc.assign_number("cmp_123", "+15551234567")

        assert isinstance(result, TenDlcAssignmentResponse)
        assert result.data.id == "asg_123"
        assert result.data.campaign_id == "cmp_123"
        assert result.data.phone_number == "+15551234567"
        assert result.data.status == "Under review"
        assert result.data.assigned_at is None

        request = httpx_mock.get_request()
        body = request.read().decode()
        assert '"phoneNumber"' in body
        assert "+15551234567" in body

        client.close()

    def test_assign_number_already_assigned_409(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key, max_retries=0)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/tendlc/campaigns/cmp_123/assign",
            method="POST",
            status_code=409,
            json=mock_error_response(
                "number_already_assigned", "Number is already assigned to a campaign"
            ),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.ten_dlc.assign_number("cmp_123", "+15551234567")

        assert exc_info.value.code == "number_already_assigned"

        client.close()

    def test_assign_number_not_ready_400(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/tendlc/campaigns/cmp_123/assign",
            method="POST",
            status_code=400,
            json=mock_error_response("number_not_ready", "Number is not ready for assignment"),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.ten_dlc.assign_number("cmp_123", "+15551234567")

        assert exc_info.value.code == "number_not_ready"

        client.close()


class TestListAssignments:
    def test_list_assignments(self, api_key, mock_assignment, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/tendlc/assignments",
            method="GET",
            json={"data": [mock_assignment]},
        )

        result = client.ten_dlc.list_assignments()

        assert isinstance(result, TenDlcAssignmentListResponse)
        assert len(result.data) == 1
        assert result.data[0].phone_number == "+15551234567"

        client.close()


class TestAsyncTenDlc:
    async def test_async_list_brands(self, api_key, mock_brand, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/tendlc/brands",
            method="GET",
            json={"data": [mock_brand]},
        )

        result = await client.ten_dlc.list_brands()

        assert isinstance(result, TenDlcBrandListResponse)
        assert result.data[0].legal_name == "Acme Holdings LLC"

        await client.close()

    async def test_async_create_brand(self, api_key, mock_brand, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/tendlc/brands",
            method="POST",
            status_code=201,
            json={"data": mock_brand},
        )

        result = await client.ten_dlc.create_brand(
            legal_name="Acme Holdings LLC",
            ein="12-3456789",
        )

        assert isinstance(result, TenDlcBrandResponse)
        assert result.data.status == "pending"

        request = httpx_mock.get_request()
        body = request.read().decode()
        assert '"legalName"' in body
        assert "entityType" not in body

        await client.close()

    async def test_async_assign_number(self, api_key, mock_assignment, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/tendlc/campaigns/cmp_123/assign",
            method="POST",
            status_code=201,
            json={"data": mock_assignment},
        )

        result = await client.ten_dlc.assign_number("cmp_123", "+15551234567")

        assert isinstance(result, TenDlcAssignmentResponse)
        assert result.data.status == "Under review"

        await client.close()
