import asyncio
import io
import json
import os
import sys
import time
import numpy as np
import psutil
from httpx import ASGITransport, AsyncClient
from backend.app.main import app
from backend.tests.helpers import create_test_amul_image, get_image_bytes

async def run_workload(name, request_fn, concurrency, total_requests):
    latencies = []
    errors = 0
    start_time = time.perf_counter()

    semaphore = asyncio.Semaphore(concurrency)

    async def worker():
        nonlocal errors
        async with semaphore:
            t0 = time.perf_counter()
            try:
                success = await request_fn()
                if not success:
                    errors += 1
            except Exception as e:
                errors += 1
            finally:
                t1 = time.perf_counter()
                latencies.append((t1 - t0) * 1000.0) # in ms

    tasks = [asyncio.create_task(worker()) for _ in range(total_requests)]
    await asyncio.gather(*tasks)

    duration = time.perf_counter() - start_time
    rps = round(total_requests / max(0.001, duration), 2)
    p50 = round(float(np.percentile(latencies, 50)), 2)
    p95 = round(float(np.percentile(latencies, 95)), 2)
    p99 = round(float(np.percentile(latencies, 99)), 2)
    err_rate = round((errors / total_requests) * 100.0, 2)

    return {
        "workload": name,
        "concurrency": concurrency,
        "total_requests": total_requests,
        "duration_sec": round(duration, 2),
        "rps": rps,
        "p50_ms": p50,
        "p95_ms": p95,
        "p99_ms": p99,
        "error_rate_pct": err_rate,
        "errors": errors
    }

async def main():
    print("=== STARTING VERISURE AI PRODUCTION PERFORMANCE BENCHMARK ===")
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / (1024 * 1024)

    transport = ASGITransport(app=app)
    results = []

    async with AsyncClient(transport=transport, base_url="http://test", timeout=60.0) as client:
        # Pre-seed credentials
        login_res = await client.post("/api/v1/auth/login", json={"email": "admin@verisure.ai", "password": "Admin@12345"})
        admin_token = login_res.json().get("access_token")
        auth_headers = {"Authorization": f"Bearer {admin_token}"}

        # Pre-generate scan image bytes
        front_bgr = create_test_amul_image()
        front_bytes = get_image_bytes(front_bgr)
        back_bgr = create_test_amul_image(corrupt_barcode=False)
        back_bytes = get_image_bytes(back_bgr)

        # Workload 1: Health Probe
        async def fn_health():
            r = await client.get("/health")
            return r.status_code == 200

        print("[1/6] Benchmarking Health Probe (Concurrency=25, N=50)...")
        results.append(await run_workload("Health", fn_health, concurrency=25, total_requests=50))

        # Workload 2: Login
        async def fn_login():
            r = await client.post("/api/v1/auth/login", json={"email": "admin@verisure.ai", "password": "Admin@12345"})
            return r.status_code == 200

        print("[2/6] Benchmarking Auth Login (Concurrency=10, N=20)...")
        results.append(await run_workload("Login", fn_login, concurrency=10, total_requests=20))

        # Workload 3: Product API
        async def fn_products():
            r = await client.get("/api/v1/products")
            return r.status_code == 200

        print("[3/6] Benchmarking Product Catalog API (Concurrency=25, N=50)...")
        results.append(await run_workload("Product API", fn_products, concurrency=25, total_requests=50))

        # Perform one initial scan to obtain a valid scan_id for PDF testing
        init_scan = await client.post(
            "/api/v1/scans/upload",
            data={"view_type": "FRONT"},
            files={"file": ("bench_front.png", io.BytesIO(front_bytes), "image/png")}
        )
        sample_scan_id = init_scan.json().get("id")

        # Workload 4: Single Scan Pipeline
        async def fn_single_scan():
            r = await client.post(
                "/api/v1/scans/upload",
                data={"view_type": "FRONT"},
                files={"file": ("bench_front.png", io.BytesIO(front_bytes), "image/png")}
            )
            return r.status_code in (200, 201)

        print("[4/6] Benchmarking Single-View AI Scan (Concurrency=5, N=10)...")
        results.append(await run_workload("Single Scan", fn_single_scan, concurrency=5, total_requests=10))

        # Workload 5: Dual Scan Pipeline
        async def fn_dual_scan():
            r = await client.post(
                "/api/v1/scans/upload-dual",
                files={
                    "file_front": ("front.png", io.BytesIO(front_bytes), "image/png"),
                    "file_back": ("back.png", io.BytesIO(back_bytes), "image/png")
                }
            )
            return r.status_code in (200, 201)

        print("[5/6] Benchmarking Dual-View 360° Scan (Concurrency=3, N=6)...")
        results.append(await run_workload("Dual Scan", fn_dual_scan, concurrency=3, total_requests=6))

        # Workload 6: PDF Report Generation
        async def fn_pdf():
            if not sample_scan_id:
                return False
            r = await client.get(f"/api/v1/scans/{sample_scan_id}/report", headers=auth_headers)
            return r.status_code == 200

        print("[6/6] Benchmarking PDF Report Generation (Concurrency=5, N=10)...")
        results.append(await run_workload("PDF Report", fn_pdf, concurrency=5, total_requests=10))

    mem_after = process.memory_info().rss / (1024 * 1024)
    cpu_percent = psutil.cpu_percent(interval=0.5)

    summary = {
        "system": {
            "python_version": sys.version,
            "os": os.name,
            "cpu_percent": cpu_percent,
            "ram_before_mb": round(mem_before, 2),
            "ram_after_mb": round(mem_after, 2),
            "ram_delta_mb": round(mem_after - mem_before, 2)
        },
        "benchmarks": results
    }

    os.makedirs("artifacts/performance", exist_ok=True)
    out_file = "artifacts/performance/baseline_metrics.json"
    with open(out_file, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n=== BENCHMARK COMPLETE. Saved to {out_file} ===")
    print(f"{'Workload':<15} | {'Concurrency':<11} | {'p50 (ms)':<9} | {'p95 (ms)':<9} | {'p99 (ms)':<9} | {'RPS':<6} | {'Err %':<6}")
    print("-" * 75)
    for b in results:
        print(f"{b['workload']:<15} | {b['concurrency']:<11} | {b['p50_ms']:<9} | {b['p95_ms']:<9} | {b['p99_ms']:<9} | {b['rps']:<6} | {b['error_rate_pct']:<6}")

if __name__ == "__main__":
    asyncio.run(main())
