from services.users_service.app import create_app


class FakeUserRepository:
    def __init__(self):
        self.users = [{"id": 1, "name": "Alice", "email": "alice@example.com", "created_at": "now"}]

    def list_users(self):
        return self.users

    def get_user(self, user_id):
        return next((user for user in self.users if user["id"] == user_id), None)

    def create_user(self, name, email):
        new_user = {"id": len(self.users) + 1, "name": name, "email": email, "created_at": "now"}
        self.users.append(new_user)
        return new_user


def test_users_flow():
    app = create_app(FakeUserRepository())
    client = app.test_client()

    list_response = client.get("/users")
    assert list_response.status_code == 200
    assert len(list_response.get_json()) == 1

    create_response = client.post("/users", json={"name": "Bob", "email": "bob@example.com"})
    assert create_response.status_code == 201

    get_response = client.get("/users/2")
    assert get_response.status_code == 200
    assert get_response.get_json()["name"] == "Bob"
