from copy import deepcopy

from app.models.config import ResearchConfigSchema
from app.services.config_adapter import builtin_presets, schema_to_research, validate_schema


def smoke_schema() -> ResearchConfigSchema:
    data = deepcopy(builtin_presets()["experiments"][0]["config"])
    data["message_count"] = 2
    data["ebn0_db_values"] = [1.0]
    data["results_dir"] = ""
    return ResearchConfigSchema.model_validate(data)


def test_json_schema_to_research_config() -> None:
    config = schema_to_research(smoke_schema(), results_dir="research_results/test")
    assert config.message_count == 2
    assert len(config.codes) == 2
    assert config.results_dir == "research_results/test"
    assert config.to_json_dict()["codes"][0]["family"] == "wavelet"


def test_wavelet_and_bch_derived_validate() -> None:
    result = validate_schema(smoke_schema())
    assert result.valid is True
    assert result.errors == []
    assert result.report["total_series"] == 4


def test_invalid_binary_vector() -> None:
    data = smoke_schema().model_dump()
    data["codes"][0]["h"] = [1, 2, 0]
    try:
        ResearchConfigSchema.model_validate(data)
    except ValueError as exc:
        assert "0 и 1" in str(exc)
    else:
        raise AssertionError("Недопустимый h должен быть отклонён")
