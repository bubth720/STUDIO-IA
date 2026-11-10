import pytest

from studio_ia.core import StudioError
from studio_ia.plans_v2 import load_plan


@pytest.mark.parametrize(
    "value",
    [None, [], 1, True, "not a plan", {"request": []}, {"schema_version": 2.0, "kind": "cpu-v1"}],
)
def test_malformed_plan_is_an_actionable_error(value):
    with pytest.raises(StudioError):
        load_plan(value)
