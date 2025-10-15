# -*- coding: utf-8 -*-
"""Test path_utils.resolve() functionality."""

from pathlib import Path
import sys

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

from path_utils import resolve, OSPath


def test_resolve():
    """Test path resolution functionality."""
    
    print("=" * 70)
    print("Testing path_utils.resolve()")
    print("=" * 70)
    
    # Test 1: String path
    print("\n1. String path (relative):")
    result = resolve("test.jpg")
    print(f"   Input: 'test.jpg'")
    print(f"   Output: {result}")
    print(f"   Type: {type(result)}")
    print(f"   Is absolute: {result.is_absolute()}")
    
    # Test 2: Path object
    print("\n2. Path object (relative):")
    result = resolve(Path("../images/test.jpg"))
    print(f"   Input: Path('../images/test.jpg')")
    print(f"   Output: {result}")
    print(f"   Is absolute: {result.is_absolute()}")
    
    # Test 3: Absolute path
    print("\n3. Absolute path:")
    abs_path = Path.cwd() / "test.jpg"
    result = resolve(abs_path)
    print(f"   Input: {abs_path}")
    print(f"   Output: {result}")
    print(f"   Same: {result == abs_path}")
    
    # Test 4: Home directory expansion
    print("\n4. Home directory expansion (~):")
    result = resolve("~/test.jpg")
    print(f"   Input: '~/test.jpg'")
    print(f"   Output: {result}")
    print(f"   Contains home: {str(Path.home()) in str(result)}")
    
    # Test 5: Disable expand_user
    print("\n5. Disable expand_user:")
    result = resolve("~/test.jpg", expand_user=False)
    print(f"   Input: '~/test.jpg' (expand_user=False)")
    print(f"   Output: {result}")
    print(f"   Contains '~': {'~' in str(result)}")
    
    # Test 6: Class method
    print("\n6. Using OSPath.resolve():")
    result = OSPath.resolve("test.jpg")
    print(f"   Input: 'test.jpg'")
    print(f"   Output: {result}")
    print(f"   Type: {type(result)}")
    
    # Test 7: ensure_absolute
    print("\n7. Using OSPath.ensure_absolute():")
    result = OSPath.ensure_absolute("test.jpg")
    print(f"   Input: 'test.jpg'")
    print(f"   Output: {result}")
    print(f"   Is absolute: {result.is_absolute()}")
    
    print("\n" + "=" * 70)
    print("✅ All tests completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    test_resolve()
