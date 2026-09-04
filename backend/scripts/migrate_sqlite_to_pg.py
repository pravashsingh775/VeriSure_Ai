import sqlite3
import json
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine
from psycopg2.extras import Json
import psycopg2
from backend.app.core.config import settings
from backend.app.core.database import BaseModel
import backend.app.models

sqlite_path = r"c:\Users\PRAVASH\Desktop\VeriSure_Ai\verisure.db"

TABLES_ORDER = [
    "roles",
    "permissions",
    "users",
    "user_roles",
    "role_permissions",
    "brands",
    "brand_settings",
    "brand_users",
    "products",
    "product_variants",
    "product_pack_sizes",
    "packaging_versions",
    "reference_images",
    "reference_features",
    "reference_fingerprints",
    "scans",
    "scan_images",
    "evidences",
    "packaging_fingerprints",
    "decisions",
    "reports",
    "suspicious_cases",
    "case_reviews",
    "feedback_samples",
    "datasets",
    "dataset_versions",
    "dataset_samples",
    "ml_models",
    "ml_model_versions",
    "ml_training_runs",
    "ml_evaluation_runs",
    "ml_model_deployments",
    "audit_logs",
]

def migrate():
    print("Connecting to SQLite and PostgreSQL...")
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    pg_engine = create_engine(settings.DATABASE_SYNC_URL)
    pg_conn = pg_engine.raw_connection()
    pg_cur = pg_conn.cursor()

    metadata_tables = BaseModel.metadata.tables
    report = {}

    # Pre-fetch valid user IDs for SET NULL checks
    sqlite_cur.execute("SELECT id FROM users;")
    valid_user_ids = {r[0] for r in sqlite_cur.fetchall()}

    try:
        for table_name in TABLES_ORDER:
            if table_name not in metadata_tables:
                continue

            sa_table = metadata_tables[table_name]
            json_cols = {c.name for c in sa_table.columns if 'JSON' in str(c.type).upper()}
            bool_cols = {c.name for c in sa_table.columns if 'BOOL' in str(c.type).upper()}
            dt_cols = {c.name for c in sa_table.columns if 'DATE' in str(c.type).upper()}

            # 1. Fetch from SQLite
            if table_name == "packaging_fingerprints":
                sqlite_cur.execute('SELECT count(*) FROM packaging_fingerprints WHERE scan_id NOT IN (SELECT id FROM scans);')
                orphans = sqlite_cur.fetchone()[0]
                sqlite_cur.execute('SELECT * FROM packaging_fingerprints WHERE scan_id IN (SELECT id FROM scans);')
                src_rows = sqlite_cur.fetchall()
                src_count = len(src_rows)
            else:
                orphans = 0
                sqlite_cur.execute(f'SELECT * FROM "{table_name}";')
                src_rows = sqlite_cur.fetchall()
                src_count = len(src_rows)

            if src_count == 0:
                report[table_name] = {
                    "source_rows": 0,
                    "target_rows": 0,
                    "status": "EMPTY",
                    "orphans_filtered": orphans,
                    "mismatches": 0
                }
                continue

            cols = [d[0] for d in sqlite_cur.description]
            cols_str = ', '.join(f'"{c}"' for c in cols)
            placeholders = ', '.join(['%s'] * len(cols))
            insert_sql = f'INSERT INTO "{table_name}" ({cols_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING;'

            rows_to_insert = []
            for row in src_rows:
                row_vals = []
                for col in cols:
                    val = row[col]
                    if val is None:
                        row_vals.append(None)
                    elif table_name == "audit_logs" and col == "user_id" and val not in valid_user_ids:
                        # SET NULL semantic for deleted user
                        row_vals.append(None)
                    elif col in json_cols:
                        if isinstance(val, str):
                            try:
                                loaded = json.loads(val)
                                row_vals.append(Json(loaded))
                            except Exception:
                                row_vals.append(Json(val))
                        else:
                            row_vals.append(Json(val))
                    elif col in bool_cols:
                        row_vals.append(bool(val))
                    elif col in dt_cols:
                        if isinstance(val, str):
                            try:
                                dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
                                row_vals.append(dt)
                            except Exception:
                                row_vals.append(val)
                        else:
                            row_vals.append(val)
                    else:
                        row_vals.append(val)
                rows_to_insert.append(tuple(row_vals))

            # Insert batch
            pg_cur.executemany(insert_sql, rows_to_insert)
            pg_conn.commit()

            # Verify in PostgreSQL
            pg_cur.execute(f'SELECT count(*) FROM "{table_name}";')
            target_count = pg_cur.fetchone()[0]

            status = "MATCH" if src_count == target_count else "MISMATCH"
            report[table_name] = {
                "source_rows": src_count,
                "target_rows": target_count,
                "status": status,
                "orphans_filtered": orphans,
                "mismatches": abs(src_count - target_count)
            }
            extra_msg = f" (filtered {orphans} orphaned records from deleted scans)" if orphans else ""
            print(f"  Migrated {table_name:25s}: {src_count:4d} rows -> {target_count:4d} rows ({status}){extra_msg}")

        with open(r'c:\Users\PRAVASH\Desktop\VeriSure_Ai\data_migration_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)

        print("\nDATA MIGRATION SUMMARY:")
        all_match = all(r['status'] in ('MATCH', 'EMPTY') for r in report.values())
        print(f"All tables synchronized successfully: {all_match}")

    finally:
        sqlite_conn.close()
        pg_cur.close()
        pg_conn.close()

if __name__ == '__main__':
    migrate()
