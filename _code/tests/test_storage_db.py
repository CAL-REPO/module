# -*- coding: utf-8 -*-
"""Test TranslationStorage with DB cache enabled."""

import tempfile
from pathlib import Path
from dataclasses import dataclass

from modules.translate_utils.services.storage import TranslationStorage


@dataclass
class StorePolicy:
    """Mock StorePolicy for testing."""
    save_db: bool = True
    db_dir: str = ""
    db_name: str = "translations.db"
    save_file: bool = False


def test_storage_with_db_cache():
    """Test TranslationStorage with DB cache enabled."""
    print("=" * 60)
    print("TEST: TranslationStorage with DB cache")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        default_dir = Path(tmpdir)
        
        policy = StorePolicy(save_db=True, db_dir=str(default_dir))
        storage = TranslationStorage(policy, default_dir=default_dir)
        
        try:
            assert storage.enabled is True
            assert storage.db_path is not None
            
            # Test put
            storage.put("Hello", "你好", "zh-CN", "deepl")
            
            # Test get
            result = storage.get("Hello", "zh-CN", "deepl")
            assert result == "你好"
            
            # Test cache miss
            missing = storage.get("Goodbye", "zh-CN", "deepl")
            assert missing is None
            
            print("✅ DB cache enabled works")
            print(f"   DB path: {storage.db_path}")
            print()
        finally:
            storage.close()


def test_storage_without_db_cache():
    """Test TranslationStorage with DB cache disabled."""
    print("=" * 60)
    print("TEST: TranslationStorage without DB cache")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        default_dir = Path(tmpdir)
        
        policy = StorePolicy(save_db=False)  # DB cache disabled
        storage = TranslationStorage(policy, default_dir=default_dir)
        
        assert storage.enabled is False
        assert storage._cache is None
        
        # These should not crash (just no-op)
        storage.put("Hello", "你好", "zh-CN", "deepl")
        result = storage.get("Hello", "zh-CN", "deepl")
        assert result is None  # No cache, so nothing stored
        
        print("✅ DB cache disabled works (no-op)")
        print()


if __name__ == "__main__":
    test_storage_with_db_cache()
    test_storage_without_db_cache()
    
    print("=" * 60)
    print("ALL STORAGE TESTS PASSED ✅")
    print("=" * 60)
