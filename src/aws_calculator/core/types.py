"""Pydantic models for AWS Pricing Calculator estimate JSON and tool inputs."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Cost(BaseModel):
    model_config = ConfigDict(extra="allow")
    monthly: float = 0.0
    upfront: float = 0.0


class CalculationComponent(BaseModel):
    model_config = ConfigDict(extra="allow")
    value: Any = None
    unit: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_non_dict(cls, data: Any) -> Any:
        # Some API components are bare arrays rather than {value: ..., unit: ...}
        if not isinstance(data, dict):
            return {"value": data}
        return data


class EstimateService(BaseModel):
    model_config = ConfigDict(extra="allow")
    service_code: str | None = Field(alias="serviceCode", default=None)
    service_name: str | None = Field(alias="serviceName", default=None)
    region: str | None = None
    region_name: str | None = Field(alias="regionName", default=None)
    calculation_components: dict[str, CalculationComponent] = Field(
        alias="calculationComponents", default_factory=dict
    )
    service_cost: Cost = Field(alias="serviceCost", default_factory=Cost)
    config_summary: str | None = Field(alias="configSummary", default=None)
    description: str | None = None
    estimate_for: str | None = Field(alias="estimateFor", default=None)
    version: str | None = None
    group: str | None = None


class EstimateMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")
    locale: str = "en_US"
    currency: str = "USD"
    created_on: str | None = Field(alias="createdOn", default=None)
    source: str | None = None
    estimate_id: str | None = Field(alias="estimateId", default=None)


class Estimate(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    name: str = "My Estimate"
    services: dict[str, EstimateService] = Field(default_factory=dict)
    groups: dict[str, Any] = Field(default_factory=dict)
    group_subtotal: Cost = Field(alias="groupSubtotal", default_factory=Cost)
    total_cost: Cost = Field(alias="totalCost", default_factory=Cost)
    support: dict[str, Any] = Field(default_factory=dict)
    meta_data: EstimateMetadata = Field(alias="metaData", default_factory=EstimateMetadata)


class ResponseFormat(StrEnum):
    TEXT = "text"
    JSON = "json"


class _BaseEstimateInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    url_or_id: str = Field(
        ...,
        description=(
            "A calculator.aws or pricing.calculator.aws.eu URL,"
            " or a bare estimate ID (bare IDs default to the global endpoint)"
        ),
        min_length=1,
    )
    format: ResponseFormat = Field(
        default=ResponseFormat.TEXT,
        description="Output format: 'text' for human-readable or 'json' for structured data",
    )


class GetEstimateInput(_BaseEstimateInput):
    pass


class ListServicesInput(_BaseEstimateInput):
    group: str | None = Field(
        default=None,
        description="Filter services by group name (case-insensitive substring match)",
    )


class GetServiceDetailInput(_BaseEstimateInput):
    service_key: str = Field(
        ...,
        description=(
            "The service key from the estimate"
            " (e.g. 'amazonAthena-bd371143-...')."
            " Use aws_calculator_list_services to find valid keys."
        ),
        min_length=1,
    )


class SummarizeEstimateInput(_BaseEstimateInput):
    pass
