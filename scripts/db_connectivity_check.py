"""VeriSure AI - DB connectivity probe.

Loads .env, tries asyncpg first then psycopg2, runs SELECT 1.
Exit code 0 = healthy, 1 = failed.
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv(override=True)


def main() -> int:
    host = os.environ.get("POSTGRES_HOST", "127.0.0.1")
    port = int(os.environ.get("POSTGRES_PORT", "5432"))
    user = os.environ.get("POSTGRES_USER", "verisure_app")
    password = os.environ.get("POSTGRES_PASSWORD", "")
    db = os.environ.get("POSTGRES_DB", "verisure_db")

    print(f"[db-check] target postgresql://{user}:***@{host}:{port}/{db}")

    try:
        import asyncio
        import asyncpg

        async def probe():
            conn = await asyncpg.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=db,
                timeout=10,
            )
            try:
                return await conn.fetchval("SELECT 1")
            finally:
                await conn.close()

        result = asyncio.run(probe())
        print(f"[db-check] asyncpg SELECT 1 -> {result} OK")
        return 0
    except Exception as e:
        print(f"[db-check] asyncpg failed: {e}")

    try:
        import psycopg2

        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=db,
            connect_timeout=10,
        )
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            result = cur.fetchone()
            print(f"[db-check] psycopg2 SELECT 1 -> {result} OK")
            return 0
        finally:
            conn.close()
    except Exception as e:
        print(f"[db-check] psycopg2 failed: {e}")

    print("[db-check] FAILED: no driver could connect")
    return 1


if __name__ == "__main__":
    sys.exit(main())
