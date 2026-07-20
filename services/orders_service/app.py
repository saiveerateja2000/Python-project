import json
import logging
import os
from datetime import datetime
from typing import Any

from flask import Flask, jsonify, request
from psycopg2 import DatabaseError
from psycopg2.extras import RealDictCursor
import psycopg2
import requests


class JsonFormatter(logging.Formatter):
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "message": record.getMessage(),
        }
        return json.dumps(payload)


def setup_logger(service_name: str) -> logging.Logger:
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter(service_name))
        logger.addHandler(handler)

    return logger


class UserClient:
    def __init__(self, users_service_url: str):
        self.users_service_url = users_service_url.rstrip("/")

    def get_user(self, user_id: int) -> dict[str, Any] | None:
        response = requests.get(f"{self.users_service_url}/users/{user_id}", timeout=3)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()


class OrderRepository:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def _connect(self):
        return psycopg2.connect(self.database_url)

    def list_orders(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT id, user_id, item, quantity, status, created_at FROM orders ORDER BY id")
                return list(cursor.fetchall())

    def create_order(self, user_id: int, item: str, quantity: int) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    INSERT INTO orders (user_id, item, quantity)
                    VALUES (%s, %s, %s)
                    RETURNING id, user_id, item, quantity, status, created_at
                    """,
                    (user_id, item, quantity),
                )
                created = cursor.fetchone()
                connection.commit()
                return created


def create_app(
    repository: OrderRepository | None = None,
    user_client: UserClient | None = None,
) -> Flask:
    app = Flask(__name__)
    logger = setup_logger("orders-service")

    database_url = os.getenv("DATABASE_URL")
    users_service_url = os.getenv("USERS_SERVICE_URL", "http://localhost:5001")

    if not database_url and repository is None:
        raise RuntimeError("DATABASE_URL is required")

    order_repository = repository or OrderRepository(database_url)
    users_client = user_client or UserClient(users_service_url)

    @app.get("/health")
    def health() -> tuple[dict[str, str], int]:
        logger.info("Health check requested")
        return {"status": "ok", "service": "orders-service"}, 200

    @app.get("/orders")
    def get_orders():
        orders = order_repository.list_orders()
        logger.info("Orders listed count=%s", len(orders))
        return jsonify(orders), 200

    @app.post("/orders")
    def post_order():
        payload = request.get_json(silent=True) or {}
        user_id = payload.get("user_id")
        item = str(payload.get("item", "")).strip()
        quantity = payload.get("quantity")

        if not isinstance(user_id, int) or not item or not isinstance(quantity, int) or quantity <= 0:
            logger.info("Invalid order payload")
            return {"error": "user_id (int), item, quantity (positive int) are required"}, 400

        user = users_client.get_user(user_id)
        if user is None:
            logger.info("Order rejected, user does not exist user_id=%s", user_id)
            return {"error": "User not found"}, 404

        created = order_repository.create_order(user_id, item, quantity)
        logger.info("Order created id=%s user_id=%s", created["id"], user_id)
        return jsonify(created), 201

    @app.errorhandler(DatabaseError)
    def handle_database_error(error: DatabaseError):
        logger.exception("Database error")
        return {"error": "Database operation failed", "details": str(error)}, 500

    @app.errorhandler(requests.RequestException)
    def handle_http_error(error: requests.RequestException):
        logger.exception("Users service communication failed")
        return {"error": "Users service unavailable", "details": str(error)}, 503

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        logger.exception("Unexpected error")
        return {"error": "Unexpected service error", "details": str(error)}, 500

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=int(os.getenv("ORDERS_SERVICE_PORT", "5002")))
