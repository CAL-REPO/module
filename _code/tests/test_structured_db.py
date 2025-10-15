# -*- coding: utf-8 -*-
"""Test refactored structured_data SQLiteKVStore."""

import tempfile
from pathlib import Path

from modules.structured_data import SQLiteKVStore, DBPolicy


def test_basic_kv_operations():
    """Test basic key-value operations."""
    print("=" * 60)
    print("TEST: Basic KV operations")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        
        policy = DBPolicy(auto_commit=True, enable_wal=False)
        
        with SQLiteKVStore(db_path, table="cache", policy=policy) as store:
            # Put
            store.put("key1", "value1")
            store.put("key2", "value2")
            
            # Get
            assert store.get("key1") == "value1"
            assert store.get("key2") == "value2"
            assert store.get("key3") is None
            
            # Exists
            assert store.exists("key1") is True
            assert store.exists("key3") is False
            
            # Delete
            store.delete("key1")
            assert store.exists("key1") is False
            assert store.get("key1") is None
        
        print("✅ Basic KV operations work")
        print()


def test_key_generation():
    """Test composite key generation."""
    print("=" * 60)
    print("TEST: Key generation")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        
        with SQLiteKVStore(db_path) as store:
            # Generate composite key
            key = store.make_key("user", "123", "en")
            assert isinstance(key, str)
            assert len(key) == 64  # SHA256 hex
            
            # Use composite key
            store.put(key, "cached_value")
            assert store.get(key) == "cached_value"
            
            # Same parts should generate same key
            key2 = store.make_key("user", "123", "en")
            assert key == key2
            
            # Different parts should generate different key
            key3 = store.make_key("user", "456", "en")
            assert key != key3
        
        print("✅ Key generation works")
        print()


def test_policy_behavior():
    """Test DBPolicy-driven behavior."""
    print("=" * 60)
    print("TEST: Policy behavior")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        
        # Custom policy
        policy = DBPolicy(
            auto_commit=False,  # Manual commit
            enable_wal=True,
            verbose=False
        )
        
        store = SQLiteKVStore(db_path, policy=policy)
        store.open()
        
        try:
            store.put("key1", "value1")
            # Without commit, data not persisted yet
            store.con.commit()  # Manual commit
            
            assert store.get("key1") == "value1"
        finally:
            store.close()
        
        print("✅ Policy behavior works")
        print()


if __name__ == "__main__":
    test_basic_kv_operations()
    test_key_generation()
    test_policy_behavior()
    
    print("=" * 60)
    print("ALL TESTS PASSED ✅")
    print("=" * 60)
