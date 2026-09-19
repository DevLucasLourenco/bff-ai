"""Fashion Module core: owner-scoped persistence and honest tool results."""

from pathlib import Path
import shutil
import io

from PIL import Image

from app.fashion.external_collection import ExternalImageError, RemoteImage, fetch_remote_image


def create_item(client, **extra):
    payload = {"name": "Jaqueta jeans", "category": "outerwear", "color": "azul", **extra}
    response = client.post("/api/fashion/wardrobe", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_wardrobe_crud_filters_and_revision_conflict(client):
    item = create_item(client, tags=["denim", "oversized"], seasons=["inverno"])
    page = client.get("/api/fashion/wardrobe", params={"query": "denim"}).json()
    assert page["total"] == 1
    assert page["items"][0]["id"] == item["id"]

    changed = client.patch(f"/api/fashion/wardrobe/{item['id']}", json={"expected_revision": 1, "style": "casual"})
    assert changed.status_code == 200
    assert changed.json()["revision"] == 2
    stale = client.patch(f"/api/fashion/wardrobe/{item['id']}", json={"expected_revision": 1, "style": "streetwear"})
    assert stale.status_code == 409


def test_create_is_idempotent_and_archive_keeps_history(client):
    payload = {"name": "Calça preta", "category": "bottom", "idempotency_key": "wardrobe-create-1"}
    first = client.post("/api/fashion/wardrobe", json=payload).json()
    second = client.post("/api/fashion/wardrobe", json=payload).json()
    assert first["id"] == second["id"]
    archived = client.delete(f"/api/fashion/wardrobe/{first['id']}", params={"expected_revision": first["revision"]})
    assert archived.status_code == 200
    assert client.get("/api/fashion/wardrobe").json()["total"] == 0


def test_outfit_only_accepts_owned_items_and_wear_is_idempotent(client):
    item = create_item(client)
    outfit = client.post("/api/fashion/outfits", json={
        "title": "Denim casual", "items": [{"slot": "top", "wardrobe_item_id": item["id"]}],
    })
    assert outfit.status_code == 201
    event = {"outfit_id": outfit.json()["id"], "idempotency_key": "wear-1"}
    first = client.post("/api/fashion/wear-events", json=event)
    second = client.post("/api/fashion/wear-events", json=event)
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert client.get(f"/api/fashion/wardrobe/{item['id']}").json()["wear_count"] == 1


def test_external_image_import_keeps_local_asset_source_and_is_idempotent(client, monkeypatch):
    from app.api.routes import fashion as fashion_routes
    from app.fashion import media

    # PNG válido; o fetch é substituído para que a suíte nunca acesse rede.
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), "beige").save(buffer, format="PNG")
    content = buffer.getvalue()
    media_dir = Path(__file__).with_name(".fashion-test-media")
    shutil.rmtree(media_dir, ignore_errors=True)
    monkeypatch.setattr(media, "FASHION_MEDIA_DIR", media_dir)
    monkeypatch.setattr(fashion_routes, "fetch_remote_image", lambda _url: RemoteImage(
        canonical_url="https://cdn.example.com/blazer.png", domain="cdn.example.com", content=content, content_type="image/png",
    ))
    payload = {
        "image_url": "https://cdn.example.com/blazer.png", "name": "Blazer bege", "category": "outerwear",
        "collection_status": "wanted", "idempotency_key": "external-blazer-1",
    }
    first = client.post("/api/fashion/external-images", json=payload)
    second = client.post("/api/fashion/external-images", json=payload)
    assert first.status_code == second.status_code == 201
    item = first.json()
    assert second.json()["id"] == item["id"]
    assert item["source"] == "external"
    assert item["collection_status"] == "wanted"
    assert item["external_url"] == "https://cdn.example.com/blazer.png"
    assert item["image"]["mime_type"] == "image/webp"
    assert client.get(item["image"]["url"]).status_code == 200
    assert client.get("/api/fashion/wardrobe", params={"collection_status": "wanted"}).json()["total"] == 1
    duplicate = client.post("/api/fashion/external-images", json={**payload, "idempotency_key": "external-blazer-2"})
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == item["id"]
    outfit = client.post("/api/fashion/outfits", json={"title": "Não pode", "items": [{"slot": "top", "wardrobe_item_id": item["id"]}]})
    assert outfit.status_code == 409
    shutil.rmtree(media_dir, ignore_errors=True)


def test_external_fetch_blocks_private_hosts_before_request(monkeypatch):
    monkeypatch.setattr("app.fashion.external_collection.socket.getaddrinfo", lambda *_args, **_kwargs: [(2, 1, 6, "", ("127.0.0.1", 0))])
    with __import__("pytest").raises(ExternalImageError, match="rede não permitida"):
        fetch_remote_image("https://localhost/look.jpg")


def test_external_fetch_follows_only_validated_redirect_and_limits_bytes(monkeypatch):
    import app.fashion.external_collection as external

    monkeypatch.setattr(external.socket, "getaddrinfo", lambda *_args, **_kwargs: [(2, 1, 6, "", ("8.8.8.8", 0))])

    class Response:
        def __init__(self, status, headers, chunks=()): self.status_code, self.headers, self._chunks = status, headers, chunks
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def iter_bytes(self): return iter(self._chunks)

    class Client:
        calls = []
        def __init__(self, **_kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def stream(self, _method, url, **_kwargs):
            self.calls.append(url)
            return Response(302, {"location": "/final.jpg"}) if len(self.calls) == 1 else Response(200, {"content-type": "image/jpeg"}, [b"image"])

    image = fetch_remote_image("https://images.example.com/start", client_factory=Client)
    assert image.canonical_url == "https://images.example.com/final.jpg"
    assert image.content == b"image"


def test_tools_are_typed_and_external_tools_are_honestly_unavailable(client):
    item = create_item(client)
    response = client.post("/api/fashion/tools/get_wardrobe", json={"category": "outerwear"})
    assert response.status_code == 200
    assert response.json()["data"]["total"] == 1
    assert response.json()["source_refs"][0]["ref_id"] == str(item["id"])

    unavailable = client.post("/api/fashion/tools/search_products", json={})
    assert unavailable.status_code == 200
    assert unavailable.json()["status"] == "unavailable"
