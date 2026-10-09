import io

import pytest
from pytest_httpx import HTTPXMock

from sendly import AsyncSendly, Sendly
from sendly.errors import SendlyError
from sendly.resources.media import MediaResource

BASE = "https://sendly.live/api/v1"

UPLOADED = {
    "id": "m1",
    "url": "https://cdn.example.com/m1.jpg",
    "contentType": "image/jpeg",
    "sizeBytes": 3,
}


def _boundary(request):
    content_type = request.headers["content-type"]
    assert content_type.startswith("multipart/form-data; boundary=")
    return content_type.split("boundary=", 1)[1]


class TestMediaUpload:
    def test_sends_a_multipart_body_labelled_as_multipart(
        self, api_key, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)
        httpx_mock.add_response(url=f"{BASE}/media", method="POST", status_code=201, json=UPLOADED)

        media = client.media.upload(io.BytesIO(b"abc"))

        request = httpx_mock.get_request()
        boundary = _boundary(request)
        body = request.content
        assert f"--{boundary}".encode() in body
        assert b'name="file"' in body
        assert b"Content-Type: image/jpeg" in body
        assert b"abc" in body
        assert request.headers["authorization"] == f"Bearer {api_key}"
        assert request.headers.get("idempotency-key")
        assert media.id == "m1"
        client.close()

    @pytest.mark.asyncio
    async def test_sends_a_multipart_body_labelled_as_multipart_async(
        self, api_key, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(url=f"{BASE}/media", method="POST", status_code=201, json=UPLOADED)

        media = await client.media.upload(io.BytesIO(b"abc"), content_type="image/png")

        request = httpx_mock.get_request()
        boundary = _boundary(request)
        assert f"--{boundary}".encode() in request.content
        assert b"Content-Type: image/png" in request.content
        assert media.size_bytes == 3
        await client.close()


class TestUploadRejections:
    def test_a_type_the_route_filters_out_raises_unsupported_media_type(
        self, api_key, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/media",
            method="POST",
            status_code=415,
            json={
                "error": "unsupported_media_type",
                "message": "Only JPEG, PNG, and GIF images are allowed for MMS",
            },
        )

        with pytest.raises(SendlyError) as exc_info:
            client.media.upload(io.BytesIO(b"RIFF0000WEBP"), content_type="image/webp")

        assert exc_info.value.code == "unsupported_media_type"
        assert exc_info.value.status_code == 415
        assert exc_info.value.message == "Only JPEG, PNG, and GIF images are allowed for MMS"
        assert len(httpx_mock.get_requests()) == 1
        client.close()

    def test_a_file_over_the_limit_raises_file_too_large(
        self, api_key, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/media",
            method="POST",
            status_code=413,
            json={"error": "file_too_large", "message": 'The file in field "file" is too large.'},
        )

        with pytest.raises(SendlyError) as exc_info:
            client.media.upload(io.BytesIO(b"\xff" * 16), content_type="image/jpeg")

        assert exc_info.value.code == "file_too_large"
        assert exc_info.value.status_code == 413
        assert len(httpx_mock.get_requests()) == 1
        client.close()

    def test_content_that_is_not_the_declared_image_raises_invalid_file(
        self, api_key, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/media",
            method="POST",
            status_code=400,
            json={
                "error": "invalid_file",
                "message": "File content does not match a supported image type (JPEG, PNG, GIF)",
            },
        )

        with pytest.raises(SendlyError) as exc_info:
            client.media.upload(io.BytesIO(b"not an image"), content_type="image/png")

        assert exc_info.value.code == "invalid_file"
        client.close()

    def test_docs_name_every_rejection(self):
        doc = MediaResource.upload.__doc__ or ""

        assert "``unsupported_media_type`` (HTTP 415)" in doc
        assert "``file_too_large`` (HTTP 413)" in doc
        assert "600 KB" in doc
        assert "``invalid_file``" in doc
