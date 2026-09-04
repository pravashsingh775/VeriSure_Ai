import asyncio
import os
import sys
import uvicorn
from backend.app.core.database import init_db
from backend.scripts.seed_data import seed_database as seed_all
from backend.scripts.seed_models import seed_initial_models


async def bootstrap():
    print("==========================================================")
    print("       VeriSure AI Platform - Minor Project Launcher      ")
    print("==========================================================")
    print("[1/3] Initializing SQLite database schema...")
    await init_db()

    print("[2/3] Verifying initial seed data (Roles, Amul, V1 Catalog)...")
    try:
        await seed_all()
        await seed_initial_models()
    except Exception as e:
        print(f"Seed info: {e}")

    print("[3/3] Launching production server on http://localhost:8000 ...")
    print("   -> Frontend App:   http://localhost:8000/app")
    print("   -> REST API Docs:  http://localhost:8000/docs")
    print("   -> Health Probe:   http://localhost:8000/health")
    print("==========================================================")


if __name__ == "__main__":
    asyncio.run(bootstrap())
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=False)
