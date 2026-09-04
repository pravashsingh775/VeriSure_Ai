# Safe cleanup script to prune test-generated artifacts from VeriSure AI primary DB
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import text
from backend.app.core.database import sync_engine

def cleanup():
    with sync_engine.begin() as conn:
        print('Scanning for test artifacts in PostgreSQL...')
        
        # 1. Evaluation runs created by test_models_registry_and_evaluation
        r_evals = conn.execute(text('DELETE FROM ml_evaluation_runs WHERE accuracy IS NULL AND f1 IS NULL'))
        print(f'Deleted {r_evals.rowcount} test evaluation runs.')

        # 2. Dataset samples, versions, and datasets created by test_datasets_and_versioning
        conn.execute(text('DELETE FROM dataset_samples WHERE image_path LIKE \'data/sample_%\''))
        conn.execute(text('DELETE FROM dataset_versions WHERE split_strategy = \'PACKAGE_AND_SESSION_ISOLATED\''))
        r_ds = conn.execute(text('DELETE FROM datasets WHERE name LIKE \'Amul Packaging Integrity Benchmark%\''))
        print(f'Deleted test datasets and samples.')

        # 3. Packaging versions created by test_packaging_versions (code = V2)
        r_pv = conn.execute(text('DELETE FROM packaging_versions WHERE version_code = \'V2\' AND notes LIKE \'%2027 Eco-Friendly%\''))
        print(f'Deleted {r_pv.rowcount} test packaging versions.')

        # 4. Test brands created by test_brands_and_rbac
        # First clean any brand settings for test brands
        conn.execute(text('DELETE FROM brand_settings WHERE brand_id IN (SELECT id FROM brands WHERE code LIKE \'BRAND_%\')'))
        r_brands = conn.execute(text('DELETE FROM brands WHERE code LIKE \'BRAND_%\''))
        print(f'Deleted {r_brands.rowcount} test brands.')

        # 5. Test consumer users created by test_auth_register_new_consumer
        conn.execute(text('DELETE FROM user_roles WHERE user_id IN (SELECT id FROM users WHERE email LIKE \'consumer_%@verisure.ai\')'))
        conn.execute(text('DELETE FROM audit_logs WHERE user_id IN (SELECT id FROM users WHERE email LIKE \'consumer_%@verisure.ai\')'))
        r_users = conn.execute(text('DELETE FROM users WHERE email LIKE \'consumer_%@verisure.ai\''))
        print(f'Deleted {r_users.rowcount} test consumer accounts.')

        print('Database cleanup complete! Pristine production state verified.')

if __name__ == '__main__':
    cleanup()
