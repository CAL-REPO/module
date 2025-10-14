"""Integration tests for structured_data unified mixin architecture.

Tests that verify:
1. Common base classes work correctly
2. Policy inheritance and composition
3. DF and DB operations using unified patterns
4. Backward compatibility
"""

import tempfile
from pathlib import Path
import pandas as pd

# Test imports from structured_data
from modules.structured_data import (
    BaseOperationsPolicy,
    DFPolicy,
    DBPolicy,
    DataFrameOps,
    SQLiteKVStore,
    TranslationCache,
)

# Test imports from data_utils (backward compatibility)
from modules.data_utils import (
    DataFrameOps as DataFrameOpsCompat,
    SQLiteKVStore as SQLiteKVStoreCompat,
)


def test_common_policy_attributes():
    """Test that DF and DB policies share common attributes."""
    print("=" * 60)
    print("TEST: Common policy attributes")
    print("=" * 60)
    
    # Create policies with common attributes
    df_policy = DFPolicy(verbose=True, strict_mode=False, auto_validate=True)
    db_policy = DBPolicy(verbose=True, strict_mode=False, auto_validate=True)
    
    # Verify common attributes match
    assert df_policy.verbose == db_policy.verbose == True
    assert df_policy.strict_mode == db_policy.strict_mode == False
    assert df_policy.auto_validate == db_policy.auto_validate == True
    
    # Verify specific attributes exist
    assert hasattr(df_policy, 'allow_empty')
    assert hasattr(db_policy, 'auto_commit')
    
    print("✅ Common policy attributes work correctly")
    print()


def test_database_operations():
    """Test database operations with new mixin architecture."""
    print("=" * 60)
    print("TEST: Database operations")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        
        # Create store with custom policy
        policy = DBPolicy(
            auto_commit=True,
            enable_wal=False,  # Disable for testing
            verbose=False
        )
        
        store = SQLiteKVStore(db_path, policy=policy)
        
        with store:
            # Test basic operations
            store.put("key1", "value1")
            assert store.get("key1") == "value1"
            
            # Test exists
            assert store.exists("key1") == True
            assert store.exists("key2") == False
            
            # Test delete
            store.delete("key1")
            assert store.exists("key1") == False
            
            # Test key generation
            key = store.make_key("part1", "part2", "part3")
            assert isinstance(key, str)
            assert len(key) == 64  # SHA256 hash
        
        print("✅ Database operations work correctly")
        print()


def test_translation_cache():
    """Test specialized translation cache."""
    print("=" * 60)
    print("TEST: Translation cache")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "translations.db"
        
        cache = TranslationCache(db_path)
        
        with cache:
            # Store translation
            cache.put_translation(
                src="Hello",
                tgt="Bonjour",
                target_lang="fr",
                model="gpt-4"
            )
            
            # Retrieve translation
            result = cache.get_translation("Hello", "fr", "gpt-4")
            assert result == "Bonjour"
            
            # Test cache miss
            result = cache.get_translation("Goodbye", "fr", "gpt-4")
            assert result is None
        
        print("✅ Translation cache works correctly")
        print()


def test_dataframe_operations():
    """Test DataFrame operations (verify no breaking changes)."""
    print("=" * 60)
    print("TEST: DataFrame operations")
    print("=" * 60)
    
    # Create policy
    policy = DFPolicy(
        allow_empty=False,
        normalize_columns=True,
        drop_empty_rows=True
    )
    
    # Create operations
    df_ops = DataFrameOps(policy=policy)
    
    # Test basic DataFrame creation
    data = {"A": [1, 2, 3], "B": [4, 5, 6]}
    df = pd.DataFrame(data)
    
    # Verify operations work
    assert df is not None
    assert len(df) == 3
    
    print("✅ DataFrame operations work correctly")
    print()


def test_backward_compatibility():
    """Test that imports from data_utils still work."""
    print("=" * 60)
    print("TEST: Backward compatibility")
    print("=" * 60)
    
    # Verify imports work
    assert DataFrameOpsCompat is DataFrameOps
    assert SQLiteKVStoreCompat is SQLiteKVStore
    
    # Test basic usage through old import path
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "compat.db"
        
        # Use old import path
        store = SQLiteKVStoreCompat(db_path)
        
        with store:
            store.put("test", "works")
            assert store.get("test") == "works"
    
    print("✅ Backward compatibility maintained")
    print()


def test_policy_inheritance():
    """Test that policies properly inherit from BaseOperationsPolicy."""
    print("=" * 60)
    print("TEST: Policy inheritance")
    print("=" * 60)
    
    # Create policies
    df_policy = DFPolicy()
    db_policy = DBPolicy()
    
    # Verify they are instances of BaseOperationsPolicy
    assert isinstance(df_policy, BaseOperationsPolicy)
    assert isinstance(db_policy, BaseOperationsPolicy)
    
    # Verify default values
    assert df_policy.verbose == False
    assert df_policy.strict_mode == True
    assert df_policy.auto_validate == True
    
    assert db_policy.verbose == False
    assert db_policy.strict_mode == True
    assert db_policy.auto_validate == True
    
    print("✅ Policy inheritance works correctly")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("STRUCTURED DATA INTEGRATION TESTS")
    print("=" * 60 + "\n")
    
    try:
        test_common_policy_attributes()
        test_database_operations()
        test_translation_cache()
        test_dataframe_operations()
        test_backward_compatibility()
        test_policy_inheritance()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        
    except Exception as e:
        print("=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        raise
