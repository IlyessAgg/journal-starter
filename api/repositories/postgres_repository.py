import json
import uuid
from datetime import datetime
from typing import Any

import asyncpg

from api.repositories.interface_repository import DatabaseInterface
from api.telemetry import entry_counter, tracer


class PostgresDB(DatabaseInterface):
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    @staticmethod
    def datetime_serialize(obj):
        """Convert datetime objects to ISO format for JSON serialization."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    async def __aenter__(self):
        self.pool = await asyncpg.create_pool(self._database_url)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.pool.close()

    async def create_entry(self, entry_data: dict[str, Any]) -> dict[str, Any]:
        with tracer.start_as_current_span("db.create_entry") as span:
            span.set_attribute("db.operation", "INSERT")

            async with self.pool.acquire() as conn:
                query = """
                INSERT INTO entries (id, data, created_at, updated_at)
                VALUES ($1, $2, $3, $4)
                RETURNING *
                """
                entry_id = entry_data.get("id") or str(uuid.uuid4())
                data_json = json.dumps(entry_data, default=PostgresDB.datetime_serialize)

                row = await conn.fetchrow(
                    query, entry_id, data_json, entry_data["created_at"], entry_data["updated_at"]
                )

                # Return a clean entry format without duplication
                if row:
                    entry_counter.add(
                        1,
                        {
                            "operation": "create",
                        },
                    )

                    data = json.loads(row["data"])
                    return {
                        "id": row["id"],
                        "work": data["work"],
                        "struggle": data["struggle"],
                        "intention": data["intention"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                    }
                return {}

    async def get_all_entries(self) -> list[dict[str, Any]]:
        with tracer.start_as_current_span("db.get_all_entries") as span:
            span.set_attribute("db.operation", "SELECT")

            async with self.pool.acquire() as conn:
                query = "SELECT * FROM entries"
                rows = await conn.fetch(query)
                entries = []
                for row in rows:
                    data = json.loads(row["data"])
                    entries.append(
                        {
                            "id": row["id"],
                            "work": data["work"],
                            "struggle": data["struggle"],
                            "intention": data["intention"],
                            "created_at": row["created_at"],
                            "updated_at": row["updated_at"],
                        }
                    )
                return entries

    async def get_entry(self, entry_id: str) -> dict[str, Any] | None:
        with tracer.start_as_current_span("db.get_entry") as span:
            span.set_attribute("db.system", "postgresql")
            span.set_attribute("db.operation", "SELECT")
            span.set_attribute("entry.id", entry_id)

            async with self.pool.acquire() as conn:
                query = "SELECT * FROM entries WHERE id = $1"
                row = await conn.fetchrow(query, entry_id)

                if row:
                    data = json.loads(row["data"])
                    return {
                        "id": row["id"],
                        "work": data["work"],
                        "struggle": data["struggle"],
                        "intention": data["intention"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                    }
                return None

    async def update_entry(self, entry_id: str, updated_data: dict[str, Any]) -> None:
        with tracer.start_as_current_span("db.update_entry") as span:
            span.set_attribute("db.operation", "UPDATE")
            span.set_attribute("entry.id", entry_id)

            updated_data["id"] = entry_id
            data_json = json.dumps(updated_data, default=PostgresDB.datetime_serialize)

            async with self.pool.acquire() as conn:
                query = """
                UPDATE entries
                SET data = $2, updated_at = $3
                WHERE id = $1
                """
                await conn.execute(query, entry_id, data_json, updated_data["updated_at"])

    async def delete_entry(self, entry_id: str) -> None:
        with tracer.start_as_current_span("db.delete_entry") as span:
            span.set_attribute("db.operation", "DELETE")
            span.set_attribute("entry.id", entry_id)

            async with self.pool.acquire() as conn:
                query = "DELETE FROM entries WHERE id = $1"
                await conn.execute(query, entry_id)

    async def delete_all_entries(self) -> None:
        with tracer.start_as_current_span("db.delete_all_entries") as span:
            span.set_attribute("db.operation", "DELETE")

            async with self.pool.acquire() as conn:
                query = "DELETE FROM entries"
                await conn.execute(query)
