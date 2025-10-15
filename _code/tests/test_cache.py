# -*- coding: utf-8 -*-
"""
Test DB Cache Functionality
----------------------------
Tests that translation cache (SQLite) works correctly.
"""

import sys
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))


def test_cache_basic():
    """Test basic cache functionality (in-memory mode)."""
    from translate_utils import Translator, TranslatePolicy
    from translate_utils.core.policy import SourcePolicy, ProviderPolicy, StorePolicy
    
    print("=" * 70)
    print("Test 1: In-Memory Cache (save_db=False)")
    print("=" * 70)
    
    policy = TranslatePolicy(
        source=SourcePolicy(text=["Hello", "World", "Hello"]),  # "Hello" repeated
        provider=ProviderPolicy(provider="mock", target_lang="KO"),
        store=StorePolicy(save_db=False, save_tr=False)
    )
    
    with Translator(policy) as t:
        result = t.run()
        
        print("\nResults:")
        for src, tgt in result.items():
            print(f"  {src} → {tgt}")
        
        # Check that duplicate "Hello" is handled
        assert "Hello" in result
        assert result["Hello"] == "[tr]:KO:Hello"
    
    print("\n✅ In-memory cache test passed!\n")


def test_cache_with_db():
    """Test SQLite DB cache functionality."""
    from translate_utils import Translator, TranslatePolicy
    from translate_utils.core.policy import SourcePolicy, ProviderPolicy, StorePolicy
    import tempfile
    
    print("=" * 70)
    print("Test 2: SQLite DB Cache (save_db=True)")
    print("=" * 70)
    
    # Use temporary directory for test
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"\nTemp DB dir: {tmpdir}")
        
        # First translation - should hit provider
        policy1 = TranslatePolicy(
            source=SourcePolicy(text=["Test1", "Test2"]),
            provider=ProviderPolicy(provider="mock", target_lang="KO"),
            store=StorePolicy(
                save_db=True,
                db_dir=tmpdir,
                db_name="test_cache.db",
                save_tr=False
            )
        )
        
        print("\n[First Run] Translating...")
        with Translator(policy1) as t:
            result1 = t.run()
            
            print("Results:")
            for src, tgt in result1.items():
                print(f"  {src} → {tgt}")
        
        # Second translation - should use cache
        policy2 = TranslatePolicy(
            source=SourcePolicy(text=["Test1", "Test2", "Test3"]),  # Test1, Test2 cached
            provider=ProviderPolicy(provider="mock", target_lang="KO"),
            store=StorePolicy(
                save_db=True,
                db_dir=tmpdir,
                db_name="test_cache.db",
                save_tr=False
            )
        )
        
        print("\n[Second Run] Using cache for Test1, Test2...")
        with Translator(policy2) as t:
            result2 = t.run()
            
            print("Results:")
            for src, tgt in result2.items():
                print(f"  {src} → {tgt}")
        
        # Verify cache worked
        assert result1["Test1"] == result2["Test1"], "Cache should return same result"
        assert result1["Test2"] == result2["Test2"], "Cache should return same result"
        assert "Test3" in result2, "New text should be translated"
    
    print("\n✅ SQLite DB cache test passed!\n")


def test_cache_persistence():
    """Test that cache persists across translator instances."""
    from translate_utils import Translator, TranslatePolicy
    from translate_utils.core.policy import SourcePolicy, ProviderPolicy, StorePolicy
    import tempfile
    
    print("=" * 70)
    print("Test 3: Cache Persistence")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "persistent_cache.db"
        print(f"\nDB path: {db_path}")
        
        # First translator instance
        policy1 = TranslatePolicy(
            source=SourcePolicy(text=["Persist1", "Persist2"]),
            provider=ProviderPolicy(provider="mock", target_lang="EN"),
            store=StorePolicy(save_db=True, db_dir=tmpdir, db_name="persistent_cache.db", save_tr=False)
        )
        
        print("\n[Instance 1] Writing to cache...")
        with Translator(policy1) as t1:
            result1 = t1.run()
            print(f"Translated: {len(result1)} items")
        
        print(f"\nDB exists: {db_path.exists()}")
        if db_path.exists():
            print(f"DB size: {db_path.stat().st_size} bytes")
        
        # Second translator instance (new object, should read from DB)
        policy2 = TranslatePolicy(
            source=SourcePolicy(text=["Persist1", "Persist2"]),  # Same texts
            provider=ProviderPolicy(provider="mock", target_lang="EN"),
            store=StorePolicy(save_db=True, db_dir=tmpdir, db_name="persistent_cache.db", save_tr=False)
        )
        
        print("\n[Instance 2] Reading from cache...")
        with Translator(policy2) as t2:
            result2 = t2.run()
            print(f"Translated: {len(result2)} items")
            
            # Should get same results from cache
            print("\nVerifying cache consistency:")
            for key in result1:
                if result1[key] == result2[key]:
                    print(f"  ✓ {key}: {result1[key]}")
                else:
                    print(f"  ✗ {key}: {result1[key]} != {result2[key]}")
                    raise AssertionError("Cache persistence failed!")
    
    print("\n✅ Cache persistence test passed!\n")


if __name__ == "__main__":
    try:
        test_cache_basic()
        
        # Check if structured_data is available for DB cache
        try:
            import structured_data.composites
            has_db = True
        except ImportError:
            has_db = False
            print("⚠️  structured_data.composites not available")
            print("⚠️  Skipping DB cache tests")
            print()
        
        if has_db:
            test_cache_with_db()
            test_cache_persistence()
        
        print("=" * 70)
        if has_db:
            print("ALL CACHE TESTS PASSED! ✅")
        else:
            print("IN-MEMORY CACHE TEST PASSED! ✅")
            print("(DB cache tests skipped - structured_data not available)")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
