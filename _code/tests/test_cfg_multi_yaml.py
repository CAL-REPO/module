"""Test multi-YAML merge scenarios"""
import pytest
from pathlib import Path
from cfg_utils.services.config_loader import ConfigLoader


def test_list_merge_with_overrides(tmp_path):
    """Test list merge applies overrides correctly"""
    # Create test files
    base_yaml = tmp_path / "base.yaml"
    base_yaml.write_text("app:\n  name: myapp\n  port: 8000\n")
    
    prod_yaml = tmp_path / "prod.yaml"
    prod_yaml.write_text("app:\n  port: 9000\n  debug: false\n")
    
    # Load with overrides
    result = ConfigLoader.load(
        [str(base_yaml), str(prod_yaml)],
        app__host="0.0.0.0"  # dot notation override
    )
    
    print(f"Result: {result}")
    
    # Check merge order
    assert result["app"]["name"] == "myapp"  # from base
    assert result["app"]["port"] == 9000  # prod overrides base
    assert result["app"]["debug"] is False  # from prod
    assert result["app"]["host"] == "0.0.0.0"  # from overrides
    
    print("✅ List merge with overrides works correctly")


def test_triple_override_source_paths(tmp_path):
    """Test 3-level override: source_paths → cfg_like → overrides"""
    # Create base config
    base_yaml = tmp_path / "base.yaml"
    base_yaml.write_text("config:\n  x: 1\n  y: 2\n")
    
    # Create config_loader.yaml
    loader_yaml = tmp_path / "config_loader.yaml"
    loader_yaml.write_text(f"""config_loader:
  yaml:
    source_paths:
      - path: "{base_yaml}"
        section: "config"
""")
    
    # Override 3 levels
    result = ConfigLoader.load(
        None,  # cfg_like
        policy_overrides={
            "config_loader_path": str(loader_yaml)
        },
        x=10,  # Override x
        z=3    # Add new key
    )
    
    print(f"Result: {result}")
    
    assert result["x"] == 10  # overrides
    assert result["y"] == 2   # from base
    assert result["z"] == 3   # new from overrides
    
    print("✅ Triple override works correctly")


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        test_list_merge_with_overrides(Path(tmpdir))
        print()
        test_triple_override_source_paths(Path(tmpdir))
