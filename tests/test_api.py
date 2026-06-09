from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


async def test_add_site(http_client: AsyncClient):
    response = await http_client.post(
        "/sites",
        json={"name": "Example", "url": "https://example.com"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Example"
    assert body["url"] == "https://example.com/"
    assert body["id"] is not None
    assert body["created_at"] is not None


async def test_add_site_duplicate_returns_conflict(http_client: AsyncClient):
    await http_client.post(
        "/sites",
        json={"name": "Example", "url": "https://example.com"},
    )
    response = await http_client.post(
        "/sites",
        json={"name": "Example copy", "url": "https://example.com"},
    )

    assert response.status_code == 409


async def test_list_sites_empty(http_client: AsyncClient):
    response = await http_client.get("/sites")

    assert response.status_code == 200
    assert response.json() == []


async def test_list_sites_returns_added_sites(http_client: AsyncClient):
    await http_client.post("/sites", json={"name": "Google", "url": "https://google.com"})
    await http_client.post("/sites", json={"name": "GitHub", "url": "https://github.com"})

    response = await http_client.get("/sites")

    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_list_sites_pagination(http_client: AsyncClient):
    for index in range(5):
        await http_client.post("/sites", json={"name": f"Site {index}", "url": f"https://site-{index}.com"})

    first_page = await http_client.get("/sites", params={"limit": 2, "offset": 0})
    second_page = await http_client.get("/sites", params={"limit": 2, "offset": 2})
    last_page = await http_client.get("/sites", params={"limit": 2, "offset": 4})

    assert len(first_page.json()) == 2
    assert len(second_page.json()) == 2
    assert len(last_page.json()) == 1
    first_page_ids = {site["id"] for site in first_page.json()}
    second_page_ids = {site["id"] for site in second_page.json()}
    assert first_page_ids.isdisjoint(second_page_ids)


async def test_run_checks_returns_results(http_client: AsyncClient):
    await http_client.post("/sites", json={"name": "Example", "url": "https://example.com"})

    mock_response = AsyncMock()
    mock_response.status_code = 200

    with patch("app.routers.checks.httpx.AsyncClient") as mock_http_client_class:
        mock_http_client_instance = AsyncMock()
        mock_http_client_instance.get = AsyncMock(return_value=mock_response)
        mock_http_client_instance.__aenter__ = AsyncMock(return_value=mock_http_client_instance)
        mock_http_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_http_client_class.return_value = mock_http_client_instance

        response = await http_client.post("/checks/run")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["available"] == 1
    assert body["unavailable"] == 0
    assert len(body["results"]) == 1
    assert body["results"][0]["is_available"] is True
    assert body["results"][0]["status_code"] == 200


async def test_run_checks_marks_unavailable_on_error(http_client: AsyncClient):
    await http_client.post("/sites", json={"name": "Bad Site", "url": "https://bad-site.invalid"})

    with patch("app.routers.checks.httpx.AsyncClient") as mock_http_client_class:
        mock_http_client_instance = AsyncMock()
        mock_http_client_instance.get = AsyncMock(side_effect=Exception("Connection refused"))
        mock_http_client_instance.__aenter__ = AsyncMock(return_value=mock_http_client_instance)
        mock_http_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_http_client_class.return_value = mock_http_client_instance

        response = await http_client.post("/checks/run")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["available"] == 0
    assert body["unavailable"] == 1
    assert body["results"][0]["is_available"] is False
    assert body["results"][0]["status_code"] is None


async def test_get_latest_checks_no_checks(http_client: AsyncClient):
    await http_client.post("/sites", json={"name": "Example", "url": "https://example.com"})

    response = await http_client.get("/checks/latest")

    assert response.status_code == 200
    assert response.json() == []


async def test_run_checks_empty_sites(http_client: AsyncClient):
    response = await http_client.post("/checks/run")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["available"] == 0
    assert body["unavailable"] == 0