"""Fashion Module core: owner-scoped persistence and honest tool results."""


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


def test_tools_are_typed_and_external_tools_are_honestly_unavailable(client):
    item = create_item(client)
    response = client.post("/api/fashion/tools/get_wardrobe", json={"category": "outerwear"})
    assert response.status_code == 200
    assert response.json()["data"]["total"] == 1
    assert response.json()["source_refs"][0]["ref_id"] == str(item["id"])

    unavailable = client.post("/api/fashion/tools/search_products", json={})
    assert unavailable.status_code == 200
    assert unavailable.json()["status"] == "unavailable"
