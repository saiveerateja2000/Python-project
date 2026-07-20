from services.orders_service.app import create_app


class FakeOrderRepository:
    def __init__(self):
        self.orders = []

    def list_orders(self):
        return self.orders

    def create_order(self, user_id, item, quantity):
        order = {
            "id": len(self.orders) + 1,
            "user_id": user_id,
            "item": item,
            "quantity": quantity,
            "status": "created",
            "created_at": "now",
        }
        self.orders.append(order)
        return order


class FakeUserClient:
    def get_user(self, user_id):
        if user_id == 1:
            return {"id": 1, "name": "Alice"}
        return None


def test_order_creation_flow():
    app = create_app(FakeOrderRepository(), FakeUserClient())
    client = app.test_client()

    create_response = client.post("/orders", json={"user_id": 1, "item": "Keyboard", "quantity": 2})
    assert create_response.status_code == 201

    list_response = client.get("/orders")
    assert list_response.status_code == 200
    assert len(list_response.get_json()) == 1


def test_order_creation_rejects_unknown_user():
    app = create_app(FakeOrderRepository(), FakeUserClient())
    client = app.test_client()

    create_response = client.post("/orders", json={"user_id": 2, "item": "Mouse", "quantity": 1})
    assert create_response.status_code == 404
