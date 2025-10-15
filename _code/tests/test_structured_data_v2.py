"""Integration tests for role-based mixin architecture (V2).

Tests that verify the new role-based structure works correctly.
"""

import tempfile
from pathlib import Path
import pandas as pd

# Test imports from structured_data (new structure)
from modules.structured_data import (
    # Policies
    DBPolicy,
    DFPolicy,
    
    # Composites
    SQLiteKVStore,
    TranslationCache,
    DataFrameOps,
    
    # Individual mixins (for custom composition)
    CleanMixin,
    ConnectionMixin,
    KVOperationsMixin,
)

# Test imports from data_utils (backward compatibility)
from modules.data_utils import (
    DataFrameOps as DataFrameOpsCompat,
    SQLiteKVStore as SQLiteKVStoreCompat,
)


def test_role_based_structure():
    """Test that role-based mixin organization works."""
    print("=" * 60)
    print("TEST: Role-based structure")
    print("=" * 60)
    
    # Verify mixins are importable
    assert CleanMixin is not None
    assert ConnectionMixin is not None
    assert KVOperationsMixin is not None
    
    print("✅ Role-based mixins are accessible")
    print()


def test_database_operations_v2():
    """Test database operations with new structure."""
    print("=" * 60)
    print("TEST: Database operations (V2)")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        
        policy = DBPolicy(auto_commit=True, enable_wal=False)
        store = SQLiteKVStore(db_path, policy=policy)
        
        with store:
            # Test basic operations
            store.put("key1", "value1")
            assert store.get("key1") == "value1"
            assert store.exists("key1") == True
            
            store.delete("key1")
            assert store.exists("key1") == False
            
            # Test key generation
            key = store.make_key("part1", "part2")
            assert isinstance(key, str)
            assert len(key) == 64
        
        print("✅ Database operations work with new structure")
        print()


def test_dataframe_operations_v2():
    """Test DataFrame operations with new structure."""
    print("=" * 60)
    print("TEST: DataFrame operations (V2)")
    print("=" * 60)
    
    policy = DFPolicy(allow_empty=False, normalize_columns=True)
    ops = DataFrameOps(policy=policy)
    
    # Test dict to DataFrame
    data = {'A': [1, 2, 3], 'B': [4, 5, 6]}
    df = ops.dict_to_df(data)
    assert len(df) == 3
    
    # Test cleaning
    df_with_nulls = pd.DataFrame({'A': [1, None], 'B': [None, None]})
    cleaned = ops.drop_empty_df(df_with_nulls, axis=1)
    assert 'B' not in cleaned.columns
    
    # Test normalization
    df_to_norm = pd.DataFrame({'old_name': [1, 2]})
    normalized = ops.normalize_df_columns(df_to_norm, {'old_name': 'new_name'})
    assert 'new_name' in normalized.columns
    
    print("✅ DataFrame operations work with new structure")
    print()


def test_cross_usage():
    """Test that mixins can be used across different data types."""
    print("=" * 60)
    print("TEST: Cross-usage of mixins")
    print("=" * 60)
    
    # CleanMixin can work with DF, dict, and list
    clean = CleanMixin()
    
    # Clean DataFrame
    df = pd.DataFrame({'A': [1, None], 'B': [None, None]})
    df_cleaned = clean.drop_empty_df(df, axis=1)
    assert 'B' not in df_cleaned.columns
    
    # Clean dict
    d = {'a': 1, 'b': None, 'c': ''}
    d_cleaned = clean.drop_empty_dict(d)
    assert 'b' not in d_cleaned
    assert 'c' not in d_cleaned
    
    # Clean list
    lst = [1, None, '', 2]
    lst_cleaned = clean.drop_empty_list(lst)
    assert None not in lst_cleaned
    assert '' not in lst_cleaned
    
    print("✅ Mixins work across different data types")
    print()


def test_hybrid_composition():
    """Test creating hybrid classes with multiple role mixins."""
    print("=" * 60)
    print("TEST: Hybrid composition")
    print("=" * 60)
    
    # Example: Custom class combining multiple role mixins
    from modules.structured_data.mixins.io import SQLiteConnectionMixin
    from modules.structured_data.mixins.ops import SQLiteKVOperationsMixin
    from modules.structured_data.mixins.transform import CleanMixin
    
    class HybridDataOps(
        SQLiteConnectionMixin,
        SQLiteKVOperationsMixin,
        CleanMixin
    ):
        """Example hybrid class combining DB and transform mixins."""
        
        def __init__(self, path):
            from modules.structured_data.composites.database import DBPolicy
            super().__init__(path, DBPolicy())
            self.table = "data"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "hybrid.db"
        
        ops = HybridDataOps(db_path)
        # This class can now use both DB operations AND data cleaning!
        
        assert hasattr(ops, 'open')  # From ConnectionMixin
        assert hasattr(ops, 'put')   # From KVOperationsMixin
        assert hasattr(ops, 'drop_empty_df')  # From CleanMixin
    
    print("✅ Hybrid composition works")
    print()


def test_backward_compatibility_v2():
    """Test that old imports still work."""
    print("=" * 60)
    print("TEST: Backward compatibility (V2)")
    print("=" * 60)
    
    # Verify old imports map to new classes
    assert DataFrameOpsCompat is DataFrameOps
    assert SQLiteKVStoreCompat is SQLiteKVStore
    
    print("✅ Backward compatibility maintained")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("STRUCTURED DATA V2 TESTS (Role-Based)")
    print("=" * 60 + "\n")
    
    try:
        test_role_based_structure()
        test_database_operations_v2()
        test_dataframe_operations_v2()
        test_cross_usage()
        test_hybrid_composition()
        test_backward_compatibility_v2()
        
        print("=" * 60)
        print("✅ ALL V2 TESTS PASSED!")
        print("=" * 60)
        
    except Exception as e:
        print("=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        raise
