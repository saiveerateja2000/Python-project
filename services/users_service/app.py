import json
import logging
import os
from datetime import datetime
from typing import Any

from flask import Flask, jsonify, request
from psycopg2 import DatabaseError
from psycopg2.extras import RealDictCursor
import psycopg2
from werkzeug.exceptions import HTTPException


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


class UserRepository:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def _connect(self):
        return psycopg2.connect(self.database_url)

    def list_users(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT id, name, email, created_at FROM users ORDER BY id")
                return list(cursor.fetchall())

    def get_user(self, user_id: int) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT id, name, email, created_at FROM users WHERE id = %s",
                    (user_id,),
                )
                return cursor.fetchone()

    def create_user(self, name: str, email: str) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    INSERT INTO users (name, email)
                    VALUES (%s, %s)
                    RETURNING id, name, email, created_at
                    """,
                    (name, email),
                )
                created = cursor.fetchone()
                connection.commit()
                return created


def create_app(repository: UserRepository | None = None) -> Flask:
    app = Flask(__name__)
    logger = setup_logger("users-service")

    database_url = os.getenv("DATABASE_URL")
    if not database_url and repository is None:
        raise RuntimeError("DATABASE_URL is required")

    user_repository = repository or UserRepository(database_url)

    @app.get("/health")
    def health() -> tuple[dict[str, str], int]:
        logger.info("Health check requested")
        return {"status": "ok", "service": "users-service"}, 200

    @app.get("/users")
    def get_users():
        users = user_repository.list_users()
        logger.info("Users listed count=%s", len(users))
        return jsonify(users), 200

    @app.get("/users/<int:user_id>")
    def get_user(user_id: int):
        user = user_repository.get_user(user_id)
        if user is None:
            logger.info("User not found id=%s", user_id)
            return {"error": "User not found"}, 404

        logger.info("User retrieved id=%s", user_id)
        return jsonify(user), 200

    @app.post("/users")
    def post_user():
        payload = request.get_json(silent=True) or {}
        name = payload.get("name", "").strip()
        email = payload.get("email", "").strip()

        if not name or not email:
            logger.info("Invalid user payload")
            return {"error": "name and email are required"}, 400

        created = user_repository.create_user(name, email)
        logger.info("User created id=%s", created["id"])
        return jsonify(created), 201

    @app.errorhandler(DatabaseError)
    def handle_database_error(error: DatabaseError):
        logger.exception("Database error")
        return {"error": "Database operation failed", "details": str(error)}, 500

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        logger.info("HTTP error status=%s path=%s", error.code, request.path)
        return {"error": error.name, "details": error.description}, error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        logger.exception("Unexpected error")
        return {"error": "Unexpected service error", "details": str(error)}, 500

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=int(os.getenv("USERS_SERVICE_PORT", "5001")))
