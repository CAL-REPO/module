# -*- coding: utf-8 -*-
# Test performance of ReferenceResolver

import time
from unify_utils.normalizers.resolver_reference import ReferenceResolver
from unify_utils.core.policy import KeyPathNormalizePolicy

def test_reference_resolver_initialization():
    """Test initialization time of ReferenceResolver with small and large data."""
    small_data = {"key": "value"}
    large_data = {f"key_{i}": {f"nested_key_{j}": j for j in range(100)} for i in range(1000)}

    # Measure initialization time for small data
    start_time = time.time()
    resolver_small = ReferenceResolver(small_data)
    small_data_time = time.time() - start_time

    # Measure initialization time for large data
    start_time = time.time()
    resolver_large = ReferenceResolver(large_data)
    large_data_time = time.time() - start_time

    print(f"Initialization time (small data): {small_data_time:.6f} seconds")
    print(f"Initialization time (large data): {large_data_time:.6f} seconds")

def test_reference_resolver_resolution():
    """Test resolution performance of ReferenceResolver with large data."""
    large_data = {f"key_{i}": {f"nested_key_{j}": j for j in range(100)} for i in range(1000)}
    resolver = ReferenceResolver(large_data)

    # Test resolving a valid keypath
    start_time = time.time()
    result = resolver._resolve_keypath("key_999.nested_key_99")
    resolution_time = time.time() - start_time

    print(f"Resolution time (valid keypath): {resolution_time:.6f} seconds")
    assert result == 99

    # Test resolving an invalid keypath
    start_time = time.time()
    try:
        resolver._resolve_keypath("key_999.invalid_key")
    except KeyError:
        pass
    invalid_resolution_time = time.time() - start_time

    print(f"Resolution time (invalid keypath): {invalid_resolution_time:.6f} seconds")

if __name__ == "__main__":
    test_reference_resolver_initialization()
    test_reference_resolver_resolution()