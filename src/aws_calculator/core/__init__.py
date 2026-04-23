"""Core library for fetching and formatting AWS Pricing Calculator estimates."""

from aws_calculator.core.client import (
    EstimateClient,
    EstimateFetchError,
    EstimateNotFoundError,
)
from aws_calculator.core.discovery import (
    CALCULATOR_ESC_URL,
    CALCULATOR_GLOBAL_URL,
    discover_estimate_api_url,
)
from aws_calculator.core.formatters import (
    format_estimate_overview,
    format_estimate_summary,
    format_service_detail,
    format_services_list,
)
from aws_calculator.core.types import (
    Estimate,
    EstimateMetadata,
    EstimateService,
    GetEstimateInput,
    GetServiceDetailInput,
    ListServicesInput,
    ResponseFormat,
    SummarizeEstimateInput,
)

__all__ = [
    "CALCULATOR_ESC_URL",
    "CALCULATOR_GLOBAL_URL",
    "Estimate",
    "EstimateClient",
    "EstimateFetchError",
    "EstimateMetadata",
    "EstimateNotFoundError",
    "EstimateService",
    "GetEstimateInput",
    "GetServiceDetailInput",
    "ListServicesInput",
    "ResponseFormat",
    "SummarizeEstimateInput",
    "discover_estimate_api_url",
    "format_estimate_overview",
    "format_estimate_summary",
    "format_service_detail",
    "format_services_list",
]
