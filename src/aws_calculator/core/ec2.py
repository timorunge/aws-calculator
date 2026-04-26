"""EC2-specific config transform for the ec2Enhancement calculator format.

Converts agent-friendly fields (instanceType, quantity, pricingStrategy, etc.)
into the nested calculationComponents structure the calculator frontend expects.
"""

from __future__ import annotations

import re
from typing import Any

_SHORTHAND_RE = re.compile(
    r"^(?:ri|reserved|convertible|instanceSavings|computeSavings|ondemand)"
    r"(?:(\d)yr)?(?:(No|Partial|All)Upfront)?$",
    re.IGNORECASE,
)

_MODEL_ALIASES: dict[str, str] = {
    "ri": "reserved",
    "reserved": "reserved",
    "convertible": "convertible",
    "instancesavings": "instanceSavings",
    "computesavings": "computeSavings",
    "ondemand": "ondemand",
}

_SELECTED_OPTION: dict[str, str] = {
    "ondemand": "on-demand",
    "reserved": "standard",
    "convertible": "convertible",
    "instanceSavings": "instance-savings",
    "computeSavings": "compute-savings",
    "spot": "spot",
}

_PAYMENT_ALIASES: dict[str, str] = {"No": "None", "Partial": "Partial", "All": "All"}

_EMPTY_DATA_TRANSFER: dict[str, Any] = {
    "value": [
        {"entryType": "INBOUND", "value": "", "unit": "tb_month", "fromRegion": ""},
        {"entryType": "OUTBOUND", "value": "", "unit": "tb_month", "toRegion": ""},
        {"entryType": "INTRA_REGION", "value": "", "unit": "tb_month"},
    ]
}


def _parse_pricing(input_val: Any) -> dict[str, str]:
    if isinstance(input_val, str):
        return _parse_string(input_val)
    if isinstance(input_val, dict):
        inner = input_val.get("value", input_val)
        if isinstance(inner, dict) and "model" in inner:
            return _normalize(
                str(inner.get("model", "ondemand")),
                str(inner.get("term", "1yr")),
                str(inner.get("upfrontPayment", inner.get("options", "None"))),
            )
        return _normalize(
            str(input_val.get("model", "ondemand")),
            str(input_val.get("term", "1yr")),
            str(input_val.get("upfrontPayment", input_val.get("options", "None"))),
        )
    return _normalize("ondemand", "1yr", "None")


def _parse_string(s: str) -> dict[str, str]:
    m = _SHORTHAND_RE.match(s)
    if m:
        model_match = re.match(r"^[a-zA-Z]+", s)
        model_key = model_match.group(0).lower() if model_match else "ondemand"
        return {
            "model": _MODEL_ALIASES.get(model_key, model_key),
            "term": f"{m.group(1)}yr" if m.group(1) else "1yr",
            "upfrontPayment": _PAYMENT_ALIASES.get(m.group(2), "None") if m.group(2) else "None",
        }

    lower = s.lower()
    model = "ondemand"
    if re.search(r"instance.savings", lower, re.IGNORECASE):
        model = "instanceSavings"
    elif re.search(r"compute.savings", lower, re.IGNORECASE):
        model = "computeSavings"
    elif "convertible" in lower:
        model = "convertible"
    elif "reserved" in lower or re.search(r"\bri\b", lower):
        model = "reserved"
    elif "spot" in lower:
        model = "spot"

    term_match = re.search(r"(\d)\s*(?:yr|year)", lower)
    upfront_payment = "None"
    if "all upfront" in lower:
        upfront_payment = "All"
    elif "partial" in lower:
        upfront_payment = "Partial"

    return {
        "model": model,
        "term": f"{term_match.group(1)}yr" if term_match else "1yr",
        "upfrontPayment": upfront_payment,
    }


def _normalize(model: str, term: str, payment: str) -> dict[str, str]:
    payment = re.sub(r"Upfront$", "", payment, flags=re.IGNORECASE)
    if payment == "No":
        payment = "None"
    return {"model": model, "term": term, "upfrontPayment": payment}


def _build_pricing_strategy(
    parsed: dict[str, str], utilization: str, tenancy: str
) -> dict[str, Any]:
    model = parsed["model"]
    term = parsed["term"]
    upfront_payment = parsed["upfrontPayment"]
    term_str = "3 Year" if term == "3yr" else "1 Year"

    # Standard/Convertible RIs are only for dedicated/host tenancy
    if not tenancy or tenancy == "shared":
        if model == "reserved":
            model = "instanceSavings"
        if model == "convertible":
            model = "computeSavings"

    selected_option = _SELECTED_OPTION.get(model, "on-demand")
    if model == "ondemand":
        return {
            "value": {
                "selectedOption": "on-demand",
                "term": term_str,
                "utilizationValue": utilization,
                "utilizationUnit": "%Utilized/Month",
            }
        }
    if model == "spot":
        return {
            "value": {
                "selectedOption": "spot",
            }
        }
    return {
        "value": {
            "selectedOption": selected_option,
            "term": term_str,
            "upfrontPayment": upfront_payment,
            "model": model,
        }
    }


def transform_config(config: dict[str, Any]) -> dict[str, Any]:
    """Convert agent-friendly EC2 fields to ec2Enhancement calculator format."""
    tenancy = config.get("tenancy", "shared")
    pricing = _parse_pricing(config.get("pricingStrategy", "ondemand"))
    utilization = str(config.get("utilization", "100"))

    result: dict[str, Any] = {
        "tenancy": {"value": tenancy},
        "selectedOS": {"value": config.get("selectedOS", "linux")},
        "workloadSelection": {"value": "consistent"},
        "instanceType": {"value": config.get("instanceType", "")},
        "workload": {
            "value": {
                "workloadType": "consistent",
                "data": str(config.get("quantity", "1")),
            }
        },
        "pricingStrategy": _build_pricing_strategy(pricing, utilization, tenancy),
        "ec2AdvancedPricingMetrics": {"value": 1},
        "detailedMonitoringCheckbox": {"value": False},
    }

    if "storageType" in config:
        result["storageType"] = {"value": config["storageType"]}
    if "storageAmount" in config:
        val = config["storageAmount"]
        result["storageAmount"] = (
            val if isinstance(val, dict) else {"value": str(val), "unit": "gb|NA"}
        )
    if config.get("snapshotFrequency") is not None:
        result["snapshotFrequency"] = {"value": str(config["snapshotFrequency"])}

    result["dataTransferForEC2"] = config.get("dataTransferForEC2", _EMPTY_DATA_TRANSFER)

    return result
