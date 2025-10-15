import os
from pathlib import Path
from modules.cfg_utils.services.config_loader import ConfigLoader
from modules.structured_io.formats.yaml_io import YamlParser
from modules.cfg_utils.core.policy import ConfigPolicy  # Use ConfigPolicy instead of BaseParserPolicy
from modules.structured_io.core.base_policy import BaseParserPolicy  # Import BaseParserPolicy

def test_default_section_behavior():
    # Test case 1: default_section via policy
    policy = ConfigPolicy(yaml_policy=BaseParserPolicy(
        default_section="test_section",
        enable_env=False,
        enable_include=False,
        enable_placeholder=False,
        enable_reference=False,
        safe_mode=True,
        encoding="utf-8",
        on_error="ignore",  # Updated to a valid string
        sort_keys=False,
        default_flow_style=False,
        indent=2
    ))
    yaml_content = """
    key1: value1
    key2: value2
    """
    parser = YamlParser(policy=policy)
    parsed_data = parser.parse(yaml_content)
    assert "test_section" in parsed_data, "Default section not applied via policy"
    assert parsed_data["test_section"]["key1"] == "value1"

    # Test case 2: default_section via ConfigLoader argument
    config_loader = ConfigLoader(
        cfg_like=yaml_content,
        policy=policy,
        default_section="loader_section"
    )
    loaded_data = config_loader.as_dict()
    assert "loader_section" in loaded_data, "Default section not applied via ConfigLoader argument"
    assert loaded_data["loader_section"]["key2"] == "value2"

    # Test case 3: No default_section, fallback to root
    policy_no_section = ConfigPolicy()
    parser_no_section = YamlParser(policy=policy_no_section)
    parsed_data_no_section = parser_no_section.parse(yaml_content)
    assert "key1" in parsed_data_no_section, "Root fallback failed when no default_section"

    print("All tests passed!")

if __name__ == "__main__":
    test_default_section_behavior()