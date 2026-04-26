"""Core library for fetching, formatting, and creating AWS Pricing Calculator estimates."""

from aws_calculator.core.builder import DEFAULT_REGION, EstimateBuilder, EstimateBuildError
from aws_calculator.core.catalog import CatalogError, ManifestClient
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
    format_add_service_results,
    format_estimate_created,
    format_estimate_overview,
    format_estimate_summary,
    format_export_result,
    format_search_results,
    format_service_detail,
    format_service_fields,
    format_services_list,
)
from aws_calculator.core.save import SaveClient, SaveError
from aws_calculator.core.types import (
    AddServiceInput,
    CreateEstimateInput,
    Estimate,
    ExportEstimateInput,
    GetEstimateInput,
    GetServiceDetailInput,
    GetServiceFieldsInput,
    ListServicesInput,
    Partition,
    ResponseFormat,
    SaveResult,
    SearchServicesInput,
    ServiceEntry,
    SummarizeEstimateInput,
)
from aws_calculator.core.validation import validate_config_keys

__all__ = [
    "CALCULATOR_ESC_URL",
    "CALCULATOR_GLOBAL_URL",
    "DEFAULT_REGION",
    "AddServiceInput",
    "CatalogError",
    "CreateEstimateInput",
    "Estimate",
    "EstimateBuildError",
    "EstimateBuilder",
    "EstimateClient",
    "EstimateFetchError",
    "EstimateNotFoundError",
    "ExportEstimateInput",
    "GetEstimateInput",
    "GetServiceDetailInput",
    "GetServiceFieldsInput",
    "ListServicesInput",
    "ManifestClient",
    "Partition",
    "ResponseFormat",
    "SaveClient",
    "SaveError",
    "SaveResult",
    "SearchServicesInput",
    "ServiceEntry",
    "SummarizeEstimateInput",
    "discover_estimate_api_url",
    "format_add_service_results",
    "format_estimate_created",
    "format_estimate_overview",
    "format_estimate_summary",
    "format_export_result",
    "format_search_results",
    "format_service_detail",
    "format_service_fields",
    "format_services_list",
    "validate_config_keys",
]
