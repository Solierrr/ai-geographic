import json

import httpx

from src.infra.external.google_registry.address import AddressProvider
from src.infra.external.google_registry.client import GoogleRegistryClient
from src.infra.external.google_registry.models import ValidateRequest


def _provider(handler):
    http = httpx.AsyncClient(
        base_url="http://registry",
        transport=httpx.MockTransport(handler),
    )
    client = GoogleRegistryClient(base_url="http://registry", timeout=2, http_client=http)
    return AddressProvider(client), http


def _address(place_id="p1", formatted="Av. Paulista, 1000"):
    return {
        "place_id": place_id,
        "formatted_address": formatted,
        "latitude": -23.5,
        "longitude": -46.6,
        "partial_match": False,
    }


async def test_geocode_success_and_serialization():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"results": [_address()]})

    provider, http = _provider(handler)
    results = await provider.geocode("Av. Paulista, 1000")
    assert results[0].place_id == "p1"
    assert requests[0].url.path == "/v1/address/geocode"
    assert json.loads(requests[0].content)["address"] == "Av. Paulista, 1000"
    await http.aclose()


async def test_geocode_empty_result_is_success():
    provider, http = _provider(
        lambda _request: httpx.Response(200, json={"results": []})
    )
    assert await provider.geocode("endereço inexistente") == []
    await http.aclose()


async def test_search_keeps_multiple_candidates_for_clarification():
    def handler(request):
        if request.url.path.endswith("suggestions"):
            return httpx.Response(
                200,
                json={
                    "suggestions": [
                        {"place_id": "p1", "description": "Rua A, SP"},
                        {"place_id": "p2", "description": "Rua A, RJ"},
                    ]
                },
            )
        place_id = request.url.path.rsplit("/", 1)[-1]
        return httpx.Response(200, json=_address(place_id, f"Rua A, {place_id}"))

    provider, http = _provider(handler)
    candidates = await provider.search("Rua A")
    assert [item.place_id for item in candidates] == ["p1", "p2"]
    await http.aclose()


async def test_place_reverse_validate_and_resolve_contracts():
    paths = []

    def handler(request):
        paths.append(request.url.path)
        if request.url.path.endswith("reverse-geocode"):
            return httpx.Response(200, json={"results": [_address()]})
        if request.url.path.endswith("validate"):
            return httpx.Response(
                200,
                json={"verdict": "ok", "address": _address()},
            )
        if request.url.path.endswith("resolve"):
            return httpx.Response(
                200,
                json={"address": _address(), "validation": {"verdict": "ok"}},
            )
        return httpx.Response(200, json=_address())

    provider, http = _provider(handler)
    assert (await provider.get_place("p1")).place_id == "p1"
    assert len(await provider.reverse_geocode(-23.5, -46.6)) == 1
    validated = await provider.validate(ValidateRequest(address_lines=["Av Paulista 1000"]))
    assert validated.verdict == "ok"
    resolved = await provider.resolve(place_id="p1")
    assert resolved.address.formatted_address == "Av. Paulista, 1000"
    assert paths == [
        "/v1/address/places/p1",
        "/v1/address/reverse-geocode",
        "/v1/address/validate",
        "/v1/address/resolve",
    ]
    await http.aclose()
