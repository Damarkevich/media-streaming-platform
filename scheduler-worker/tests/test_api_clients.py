"""Tests for src.services.api_clients."""

import httpx
import pytest

import src.services.api_clients as api_clients_module
from src.services.api_clients import get_all_user_ids, get_top_films

PAGE_SIZE = 500  # mirrors the constant inside get_all_user_ids


# ---------------------------------------------------------------------------
# get_top_films
# ---------------------------------------------------------------------------


class TestGetTopFilms:
    async def test_returns_films_on_success(self, monkeypatch):
        films = [{"id": "abc", "title": "Test Film", "imdb_rating": 9.5}]
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(lambda req: httpx.Response(200, json=films))
        )
        monkeypatch.setattr(api_clients_module, "_client", client)

        result = await get_top_films(10)

        assert result == films

    async def test_passes_correct_query_params(self, monkeypatch):
        captured: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=[])

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        monkeypatch.setattr(api_clients_module, "_client", client)

        await get_top_films(5)

        assert captured["params"]["sort"] == "-imdb_rating"
        assert captured["params"]["page_size"] == "5"
        assert captured["params"]["page_number"] == "1"

    async def test_returns_empty_list_on_http_error(self, monkeypatch):
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda req: httpx.Response(500, text="Internal Server Error")
            )
        )
        monkeypatch.setattr(api_clients_module, "_client", client)

        result = await get_top_films(10)

        assert result == []

    async def test_returns_empty_list_on_network_error(self, monkeypatch):
        def handler(req: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        monkeypatch.setattr(api_clients_module, "_client", client)

        result = await get_top_films(10)

        assert result == []

    async def test_sends_request_id_header(self, monkeypatch):
        captured: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["headers"] = dict(req.headers)
            return httpx.Response(200, json=[])

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        monkeypatch.setattr(api_clients_module, "_client", client)

        await get_top_films(3)

        assert captured["headers"].get("x-request-id") == "scheduler-weekly-digest"


# ---------------------------------------------------------------------------
# get_all_user_ids
# ---------------------------------------------------------------------------


class TestGetAllUserIds:
    async def test_single_page_returns_all_ids(self, monkeypatch):
        users = [{"user_id": "user-1"}, {"user_id": "user-2"}]
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda req: httpx.Response(200, json={"items": users})
            )
        )
        monkeypatch.setattr(api_clients_module, "_client", client)

        result = await get_all_user_ids()

        assert result == ["user-1", "user-2"]

    async def test_empty_items_returns_empty_list(self, monkeypatch):
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda req: httpx.Response(200, json={"items": []})
            )
        )
        monkeypatch.setattr(api_clients_module, "_client", client)

        result = await get_all_user_ids()

        assert result == []

    async def test_paginates_when_full_page_returned(self, monkeypatch):
        """When the first page has exactly PAGE_SIZE items the function requests page 2."""
        page0_items = [{"user_id": f"u{i}"} for i in range(PAGE_SIZE)]
        page1_items = [{"user_id": "u-last"}]
        responses = iter([
            httpx.Response(200, json={"items": page0_items}),
            httpx.Response(200, json={"items": page1_items}),
        ])
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(lambda req: next(responses))
        )
        monkeypatch.setattr(api_clients_module, "_client", client)

        result = await get_all_user_ids()

        assert len(result) == PAGE_SIZE + 1
        assert result[0] == "u0"
        assert result[-1] == "u-last"

    async def test_stops_on_http_error_returns_collected_ids(self, monkeypatch):
        """If a page request fails the function stops and returns what was collected."""
        page0_items = [{"user_id": f"u{i}"} for i in range(PAGE_SIZE)]
        responses = iter([
            httpx.Response(200, json={"items": page0_items}),
            httpx.Response(503, text="service unavailable"),
        ])
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(lambda req: next(responses))
        )
        monkeypatch.setattr(api_clients_module, "_client", client)

        result = await get_all_user_ids()

        assert len(result) == PAGE_SIZE
        assert result[0] == "u0"

    async def test_sends_internal_key_header(self, monkeypatch):
        captured: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["headers"] = dict(req.headers)
            return httpx.Response(200, json={"items": []})

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        monkeypatch.setattr(api_clients_module, "_client", client)

        await get_all_user_ids()

        from src.core.config import settings
        assert captured["headers"].get("x-internal-key") == settings.internal_api_key

    async def test_increments_page_param(self, monkeypatch):
        """Verify the page query parameter increments between requests."""
        captured_pages: list[str] = []
        page0_items = [{"user_id": f"u{i}"} for i in range(PAGE_SIZE)]
        page1_items = [{"user_id": "u-last"}]
        responses = iter([
            httpx.Response(200, json={"items": page0_items}),
            httpx.Response(200, json={"items": page1_items}),
        ])

        def handler(req: httpx.Request) -> httpx.Response:
            captured_pages.append(req.url.params.get("page", ""))
            return next(responses)

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        monkeypatch.setattr(api_clients_module, "_client", client)

        await get_all_user_ids()

        assert captured_pages == ["0", "1"]
