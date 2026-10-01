import pytest
from pytest_httpx import HTTPXMock

from sendly import AsyncSendly, Sendly
from sendly.types import TemplatePreview

BASE = "https://sendly.live/api/v1"

PREVIEW = {
    "template_id": "tpl_1",
    "original_text": "Hi {{name}}",
    "rendered_text": "Hi Bob",
    "character_count": 6,
    "segment_count": 1,
}


class TestTemplatePreview:
    def test_reads_the_preview(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(url=f"{BASE}/templates/tpl_1/preview", method="POST", json=PREVIEW)

        preview = client.templates.preview("tpl_1", variables={"name": "Bob"})

        assert preview.id == "tpl_1"
        assert preview.original_text == "Hi {{name}}"
        assert preview.preview_text == "Hi Bob"
        assert preview.character_count == 6
        assert preview.segment_count == 1
        assert preview.name is None
        client.close()

    @pytest.mark.asyncio
    async def test_reads_the_preview_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(url=f"{BASE}/templates/tpl_1/preview", method="POST", json=PREVIEW)

        preview = await client.templates.preview("tpl_1")

        assert preview.preview_text == "Hi Bob"
        await client.close()


class TestTemplatePreviewModel:
    def test_variables_description_says_it_is_always_empty(self):
        description = TemplatePreview.model_fields["variables"].description

        assert "Not returned by the preview; always empty" in description
