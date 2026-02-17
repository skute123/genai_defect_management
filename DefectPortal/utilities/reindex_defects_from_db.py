"""
Re-index defects from database (defects_table_acc, defects_table_sit).
Run after updating the DB defect dump so AI search uses the latest data.
Usage: python utilities/reindex_defects_from_db.py
"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    print("=" * 60)
    print("Re-index Defects from DB")
    print("=" * 60)

    try:
        from modules.database_connection import get_db_engine
        from modules.utilities import fetch_defects
        from modules.genai.enhanced_search import EnhancedSearch

        print("\n1. Connecting to database...")
        engine = get_db_engine()

        print("2. Loading defects from defects_table_acc and defects_table_sit...")
        defects_acc = fetch_defects(engine, "defects_table_acc")
        defects_acc = defects_acc.fillna("").replace("nan", "").replace("NaN", "")
        defects_sit = fetch_defects(engine, "defects_table_sit")
        defects_sit = defects_sit.fillna("").replace("nan", "").replace("NaN", "")
        total = len(defects_acc) + len(defects_sit)
        print(f"   Loaded ACC: {len(defects_acc)}, SIT: {len(defects_sit)}, total: {total}")

        print("3. Initializing AI system and re-indexing defects (force_reindex=True)...")
        enhanced_search = EnhancedSearch()
        enhanced_search.index_data(
            defects_acc,
            defects_sit,
            index_documents=False,
            force_reindex=True,
        )

        stats = enhanced_search.get_status()
        print(f"\n4. Done. Defects indexed: {stats.get('defects_indexed', 0)}")
        print("=" * 60)
    except ImportError as e:
        print(f"\nError: {e}")
        print("Ensure dependencies are installed and DB is configured.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        raise


if __name__ == "__main__":
    main()
