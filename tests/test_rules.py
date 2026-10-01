import json

import pytest
from pytest_httpx import HTTPXMock

from sendly import AsyncSendly, Sendly

BASE = "https://sendly.live/api/v1"

RULE = {
    "id": "rule_1",
    "userId": "user_1",
    "organizationId": "org_1",
    "name": "Support",
    "conditions": {"intent": ["support"]},
    "actions": {"addLabels": ["lbl_1"]},
    "enabled": False,
    "priority": 0,
    "createdAt": "2026-01-01T00:00:00.000Z",
    "updatedAt": "2026-01-02T00:00:00.000Z",
}


class TestRuleEnabled:
    def test_update_can_disable_a_rule(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(url=f"{BASE}/rules/rule_1", method="PATCH", json=RULE)

        rule = client.rules.update("rule_1", enabled=False)

        assert json.loads(httpx_mock.get_request().content) == {"enabled": False}
        assert rule.enabled is False
        client.close()

    def test_list_reads_enabled(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/rules",
            method="GET",
            json={"data": [RULE, {**RULE, "id": "rule_2", "enabled": True}]},
        )

        result = client.rules.list()

        assert [r.enabled for r in result.data] == [False, True]
        client.close()

    @pytest.mark.asyncio
    async def test_update_can_enable_a_rule_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/rules/rule_1", method="PATCH", json={**RULE, "enabled": True}
        )

        rule = await client.rules.update("rule_1", enabled=True)

        assert json.loads(httpx_mock.get_request().content) == {"enabled": True}
        assert rule.enabled is True
        await client.close()
