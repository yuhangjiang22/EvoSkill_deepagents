from src.agent_profiles.sdk_config import set_sdk, get_sdk, is_azure_sdk, is_claude_sdk

def test_azure_sdk_type():
    set_sdk("azure")
    assert get_sdk() == "azure"
    assert is_azure_sdk() is True
    assert is_claude_sdk() is False
    set_sdk("claude")  # reset

def test_invalid_sdk_raises():
    import pytest
    with pytest.raises(ValueError):
        set_sdk("invalid")
