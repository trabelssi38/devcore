"""The former implicit coding/reasoning mapping is intentionally prohibited."""
import pytest
from Scripts.router.policy import MODEL_MAP, validate_auxiliary

def test_auxiliary_profiles_are_explicit():
    assert set(MODEL_MAP) == {"devcore-writing", "devcore-documentation", "devcore-summary", "devcore-bulk"}

@pytest.mark.parametrize("mode", ["reasoning", "coding", "bulk", "plan"])
def test_mode_alone_cannot_authorize_gemini(mode):
    with pytest.raises(ValueError):
        validate_auxiliary({"mode": mode, "messages": []})

def test_old_model_aliases_cannot_authorize_gemini():
    for model in ("devcore-reasoning", "devcore-coding", "devcore-always-on"):
        with pytest.raises(ValueError):
            validate_auxiliary({"model": model})
