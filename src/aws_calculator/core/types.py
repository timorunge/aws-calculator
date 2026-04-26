"""Pydantic models for AWS Pricing Calculator estimate JSON and tool inputs."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ResponseFormat(StrEnum):
    TEXT = "text"
    JSON = "json"


class Partition(StrEnum):
    AWS = "aws"
    AWS_ESC = "aws-esc"
    AWS_ISO = "aws-iso"
    AWS_ISO_B = "aws-iso-b"


FORMAT_FIELD = Field(default=ResponseFormat.TEXT, description="'text' or 'json'")
URL_OR_ID_FIELD = Field(
    ...,
    description="calculator.aws URL or bare estimate ID",
    min_length=1,
)
PARTITION_FIELD = Field(
    default=Partition.AWS,
    description="'aws', 'aws-esc', 'aws-iso', or 'aws-iso-b'",
)
ESTIMATE_ID_FIELD = Field(
    ..., description="Estimate ID from create_estimate", min_length=1, max_length=200
)


DEFAULT_LOCALE = "en_US"
DEFAULT_CURRENCY = "USD"
MAX_KEYS_IN_ERROR = 5


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
    locale: str = DEFAULT_LOCALE
    currency: str = DEFAULT_CURRENCY
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

    @model_validator(mode="before")
    @classmethod
    def _hoist_grouped_services(cls, data: Any) -> Any:
        """Flatten services nested under groups into the top-level services dict."""
        if not isinstance(data, dict):
            return data
        groups = data.get("groups")
        if not isinstance(groups, dict):
            return data
        services = dict(data.get("services") or {})
        _flatten_groups(groups, services)
        data = {**data, "services": services}
        return data


def _flatten_groups(groups: dict[str, Any], services: dict[str, Any]) -> None:
    for group_data in groups.values():
        if not isinstance(group_data, dict):
            continue
        group_name = group_data.get("name")
        nested = group_data.get("services")
        if isinstance(nested, dict):
            for svc_key, svc_data in nested.items():
                if isinstance(svc_data, dict) and svc_key not in services:
                    if group_name and not svc_data.get("group"):
                        svc_data = {**svc_data, "group": group_name}
                    services[svc_key] = svc_data
        sub_groups = group_data.get("groups")
        if isinstance(sub_groups, dict):
            _flatten_groups(sub_groups, services)


class ServiceEntry(BaseModel):
    model_config = ConfigDict(extra="allow")
    key: str
    name: str
    service_code: str | None = Field(alias="serviceCode", default=None)
    search_keywords: list[str] = Field(alias="searchKeywords", default_factory=list)
    sub_type: str | None = Field(alias="subType", default=None)
    is_active: str | None = Field(alias="isActive", default=None)
    service_definition_url_path: str | None = Field(alias="serviceDefinitionUrlPath", default=None)


class FieldOption(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str | None = None
    label: str | None = None


class ServiceField(BaseModel):
    id: str
    type: str
    label: str | None = None
    options: list[FieldOption] = Field(default_factory=list)
    unit: str | None = None
    valid_sizes: list[str] = Field(default_factory=list)
    default_unit: str | None = None
    unit_format: str | None = None


class SaveResult(BaseModel):
    estimate_id: str
    shareable_url: str


class _BaseEstimateInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    url_or_id: str = URL_OR_ID_FIELD
    format: ResponseFormat = FORMAT_FIELD


class GetEstimateInput(_BaseEstimateInput):
    pass


class ListServicesInput(_BaseEstimateInput):
    group: str | None = Field(
        default=None,
        description="Filter by group name (substring match)",
    )


class GetServiceDetailInput(_BaseEstimateInput):
    service_key: str = Field(
        ...,
        description="Service key from list_services (e.g. 'amazonAthena-bd371143-...')",
        min_length=1,
    )


class SummarizeEstimateInput(_BaseEstimateInput):
    pass


class SearchServicesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    query: str = Field(
        ...,
        min_length=1,
        description="Comma-separated search terms (e.g. 'lambda, s3')",
    )
    partition: Partition = PARTITION_FIELD
    max_results: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Max results per term",
    )
    format: ResponseFormat = FORMAT_FIELD


class GetServiceFieldsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    service: str = Field(
        ...,
        min_length=1,
        description="Comma-separated service keys (e.g. 'aWSLambda, amazonS3Standard')",
    )
    partition: Partition = PARTITION_FIELD
    format: ResponseFormat = FORMAT_FIELD


class CreateEstimateInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(default="My Estimate")
    partition: Partition | None = Field(default=None)


class AddServiceInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    estimate_id: str = ESTIMATE_ID_FIELD
    services: str = Field(
        ...,
        description=(
            "JSON array: [{serviceCode, region, calculationComponents, description?, group?}]"
        ),
    )


class ExportEstimateInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    estimate_id: str = ESTIMATE_ID_FIELD
    format: ResponseFormat = FORMAT_FIELD
