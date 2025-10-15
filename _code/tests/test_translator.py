# -*- coding: utf-8 -*-
"""
Translator Refactoring Test
----------------------------
Tests the new Translator entrypoint following FirefoxWebDriver pattern.
"""

import sys
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

def test_translator_basic():
    """Test basic Translator initialization and usage."""
    from translate_utils import Translator, TranslatePolicy
    from translate_utils.core.policy import SourcePolicy, ProviderPolicy, StorePolicy
    
    print("=" * 70)
    print("Test 1: Translator with Policy object")
    print("=" * 70)
    
    # Create policy with mock provider
    policy = TranslatePolicy(
        source=SourcePolicy(text=["Hello", "Thank you", "Good morning"]),
        provider=ProviderPolicy(
            provider="mock",  # Use mock provider for testing
            target_lang="KO",
            source_lang="EN"
        ),
        store=StorePolicy(save_db=False, save_tr=False)  # Disable storage for test
    )
    
    # Create translator
    translator = Translator(policy)
    
    # Run translation
    result = translator.run()
    
    print("\nResults:")
    for src, tgt in result.items():
        print(f"  {src} → {tgt}")
    
    translator.close()
    print("\n✅ Test 1 passed!\n")


def test_translator_yaml():
    """Test Translator with YAML config."""
    from translate_utils import Translator
    
    print("=" * 70)
    print("Test 2: Translator with YAML config")
    print("=" * 70)
    
    config_path = Path(__file__).parent.parent / "modules" / "translate_utils" / "config" / "translate.yaml"
    
    print(f"\nConfig path: {config_path}")
    print(f"Exists: {config_path.exists()}")
    
    if not config_path.exists():
        print("❌ Config file not found, skipping test")
        return
    
    # Test with runtime override to use mock provider and disable storage
    translator = Translator(
        str(config_path),
        provider__provider="mock",  # Override to use mock
        source__text=["안녕하세요", "감사합니다"],
        store__save_db=False,  # Disable DB cache
        store__save_tr=False   # Disable file save
    )
    
    result = translator.run()
    
    print("\nResults:")
    for src, tgt in result.items():
        print(f"  {src} → {tgt}")
    
    translator.close()
    print("\n✅ Test 2 passed!\n")


def test_translator_context_manager():
    """Test Translator with context manager."""
    from translate_utils import Translator, TranslatePolicy
    from translate_utils.core.policy import SourcePolicy, ProviderPolicy, StorePolicy
    
    print("=" * 70)
    print("Test 3: Translator with context manager")
    print("=" * 70)
    
    policy = TranslatePolicy(
        source=SourcePolicy(text=["Python", "Programming", "AI"]),
        provider=ProviderPolicy(provider="mock", target_lang="KO"),
        store=StorePolicy(save_db=False, save_tr=False)  # Disable storage
    )
    
    with Translator(policy) as translator:
        result = translator.run()
        
        print("\nResults:")
        for src, tgt in result.items():
            print(f"  {src} → {tgt}")
    
    print("\n✅ Test 3 passed!\n")


if __name__ == "__main__":
    try:
        test_translator_basic()
        test_translator_yaml()
        test_translator_context_manager()
        
        print("=" * 70)
        print("ALL TESTS PASSED! ✅")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
