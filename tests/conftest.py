"""Shared fixtures for tests."""

from typing import Any

import httpx
import pytest

from aws_calculator.core.types import Estimate
from aws_calculator.server import mcp

SAMPLE_ESTIMATE_ID = "e459751ce5e5aa93f254ea8ad3e825af92906379"


def get_tool_fn(name: str) -> Any:
    return mcp._tool_manager._tools[name].fn


def make_catalog_transport(
    manifest: dict[str, Any],
    definitions: dict[str, dict[str, Any]] | None = None,
) -> httpx.MockTransport:
    defs = definitions or {}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "manifest" in url:
            return httpx.Response(200, json=manifest)
        for key, definition in defs.items():
            if key in url:
                return httpx.Response(200, json=definition)
        return httpx.Response(404, json={})

    return httpx.MockTransport(handler)


SAMPLE_ESTIMATE_JSON = {
    "name": "Serverless API",
    "services": {
        "amazonApiGateway-124c6a96-cd94-4c85-a162-6a4a3254d184": {
            "calculationComponents": {
                "apiType": {"value": "REST"},
                "numberOfAPIRequests": {"value": "5000000", "unit": "perMonth"},
                "averageMessageSizeKB": {"value": "32", "unit": "KB"},
                "cacheSizeGB": {"value": "0.5", "unit": "GB"},
            },
            "serviceCode": "amazonApiGateway",
            "region": "us-east-1",
            "estimateFor": "template",
            "version": "0.0.59",
            "description": None,
            "serviceCost": {"monthly": 17.50},
            "serviceName": "Amazon API Gateway",
            "regionName": "US East (N. Virginia)",
            "configSummary": "REST API requests (5,000,000 per month), Cache memory (0.5 GB)",
        },
        "awsLambda-bd371143-fbcd-4b43-b5b7-cfe3ac9fd72e": {
            "calculationComponents": {
                "numberOfRequests": {"value": "5000000", "unit": "perMonth"},
                "durationMs": {"value": "200", "unit": "ms"},
                "memoryMB": {"value": "256", "unit": "MB"},
            },
            "serviceCode": "awsLambda",
            "region": "us-east-1",
            "estimateFor": "Lambda",
            "version": "0.0.41",
            "description": None,
            "serviceCost": {"monthly": 12.08},
            "serviceName": "AWS Lambda",
            "regionName": "US East (N. Virginia)",
            "configSummary": (
                "Number of requests (5,000,000 per month), "
                "Duration of each request (200 ms), "
                "Amount of memory allocated (256 MB)"
            ),
        },
    },
    "groups": {},
    "groupSubtotal": {"monthly": 29.58},
    "totalCost": {"monthly": 29.58, "upfront": 0},
    "support": {},
    "metaData": {
        "locale": "en_US",
        "currency": "USD",
        "createdOn": "2026-03-26T22:45:11.638Z",
        "source": "calculator-platform",
        "estimateId": SAMPLE_ESTIMATE_ID,
    },
}


@pytest.fixture
def sample_estimate() -> Estimate:
    return Estimate.model_validate(SAMPLE_ESTIMATE_JSON)


STARTUP_SAAS_ESTIMATE_JSON = {
    "name": "Startup SaaS Platform",
    "services": {
        "amazonEC2-3f2a1b4c-d5e6-7890-abcd-ef1234567890": {
            "serviceCode": "amazonEC2",
            "serviceName": "Amazon EC2",
            "region": "us-east-1",
            "regionName": "US East (N. Virginia)",
            "estimateFor": "EC2",
            "version": "0.0.134",
            "description": None,
            "calculationComponents": {
                "instanceType": {"value": "m5.xlarge"},
                "numberOfInstances": {"value": "4", "unit": "instances"},
                "operatingSystem": {"value": "Linux"},
                "tenancy": {"value": "Shared Instances"},
                "paymentOption": {"value": "On-Demand"},
                "utilizationPercentage": {"value": "100", "unit": "percent"},
                "ebsStorageGB": {"value": "50", "unit": "GB"},
            },
            "serviceCost": {"monthly": 560.64},
            "configSummary": (
                "Tenancy (Shared Instances), Operating system (Linux), "
                "Workload (Consistent, Number of instances: 4), "
                "Instance type (m5.xlarge), Pricing model (On-Demand), "
                "EBS storage amount (50 GB)"
            ),
            "group": "Application",
        },
        "awsLambda-a1b2c3d4-e5f6-7890-abcd-111122223333": {
            "serviceCode": "awsLambda",
            "serviceName": "AWS Lambda",
            "region": "us-east-1",
            "regionName": "US East (N. Virginia)",
            "estimateFor": "Lambda",
            "version": "0.0.41",
            "description": None,
            "calculationComponents": {
                "numberOfRequests": {"value": "20000000", "unit": "perMonth"},
                "durationMs": {"value": "300", "unit": "ms"},
                "memoryMB": {"value": "512", "unit": "MB"},
                "ephemeralStorageMB": {"value": "512", "unit": "MB"},
            },
            "serviceCost": {"monthly": 15.60},
            "configSummary": (
                "Architecture (x86), Number of requests (20,000,000 per month), "
                "Duration of each request (300 ms), "
                "Amount of memory allocated (512 MB), "
                "Ephemeral storage (512 MB)"
            ),
            "group": "Application",
        },
        "amazonSES-b2c3d4e5-f6a7-8901-bcde-222233334444": {
            "serviceCode": "amazonSES",
            "serviceName": "Amazon Simple Email Service (SES)",
            "region": "us-east-1",
            "regionName": "US East (N. Virginia)",
            "estimateFor": "SES",
            "version": "0.0.22",
            "description": None,
            "calculationComponents": {
                "emailsSentPerMonth": {"value": "500000", "unit": "perMonth"},
                "emailSizeKB": {"value": "32", "unit": "KB"},
            },
            "serviceCost": {"monthly": 38.00},
            "configSummary": (
                "Outbound email (Sending emails from EC2, 500,000 emails per month), "
                "Attachment/Message size (32 KB)"
            ),
            "group": "Application",
        },
        "elasticloadbalancing-c3d4e5f6-a7b8-9012-cdef-333344445555": {
            "serviceCode": "elasticloadbalancing",
            "serviceName": "Elastic Load Balancing",
            "region": "us-east-1",
            "regionName": "US East (N. Virginia)",
            "estimateFor": "ELB",
            "version": "0.0.31",
            "description": None,
            "calculationComponents": {
                "elbType": {"value": "Application Load Balancer"},
                "numberOfALBs": {"value": "1", "unit": "units"},
                "lcuPerHour": {"value": "5", "unit": "LCU"},
            },
            "serviceCost": {"monthly": 68.96},
            "configSummary": (
                "Load balancer type (Application), Number of ALBs (1), "
                "Processed bytes per LCU (5 LCU per hour)"
            ),
            "group": "Application",
        },
        "AmazonRDS-d4e5f6a7-b8c9-0123-defa-444455556666": {
            "serviceCode": "AmazonRDS",
            "serviceName": "Amazon RDS for PostgreSQL",
            "region": "us-east-1",
            "regionName": "US East (N. Virginia)",
            "estimateFor": "RDS",
            "version": "0.0.77",
            "description": None,
            "calculationComponents": {
                "instanceType": {"value": "db.r5.2xlarge"},
                "deploymentOption": {"value": "Multi-AZ"},
                "storageType": {"value": "General Purpose SSD (gp2)"},
                "storageGB": {"value": "500", "unit": "GB"},
                "paymentOption": {"value": "On-Demand"},
                "backupStorageGB": {"value": "100", "unit": "GB"},
            },
            "serviceCost": {"monthly": 751.20},
            "configSummary": (
                "Database engine (PostgreSQL), DB instance class (db.r5.2xlarge), "
                "Deployment type (Multi-AZ), "
                "Storage type (General Purpose SSD (gp2)), "
                "Storage amount (500 GB), Pricing model (OnDemand)"
            ),
            "group": "Data",
        },
        "amazonElastiCache-e5f6a7b8-c9d0-1234-efab-555566667777": {
            "serviceCode": "amazonElastiCache",
            "serviceName": "Amazon ElastiCache",
            "region": "us-east-1",
            "regionName": "US East (N. Virginia)",
            "estimateFor": "ElastiCache",
            "version": "0.0.49",
            "description": None,
            "calculationComponents": {
                "cacheEngine": {"value": "Redis"},
                "nodeType": {"value": "cache.r6g.xlarge"},
                "numberOfNodes": {"value": "2", "unit": "nodes"},
                "paymentOption": {"value": "On-Demand"},
            },
            "serviceCost": {"monthly": 523.20},
            "configSummary": (
                "Cache engine (Redis), Node type (cache.r6g.xlarge), "
                "Number of nodes (2), Pricing model (On-Demand)"
            ),
            "group": "Data",
        },
        "AmazonS3-f6a7b8c9-d0e1-2345-fabc-666677778888": {
            "serviceCode": "AmazonS3",
            "serviceName": "Amazon Simple Storage Service (S3)",
            "region": "us-east-1",
            "regionName": "US East (N. Virginia)",
            "estimateFor": "S3",
            "version": "0.0.92",
            "description": None,
            "calculationComponents": {
                "storageAmountGB": {"value": "2000", "unit": "GB"},
                "putCopyPostListRequests": {"value": "1000000", "unit": "perMonth"},
                "getSelectRequests": {"value": "10000000", "unit": "perMonth"},
                "dataTransferOutGB": {"value": "100", "unit": "GB"},
            },
            "serviceCost": {"monthly": 72.45},
            "configSummary": (
                "S3 Standard storage (2,000 GB), "
                "PUT, COPY, POST, LIST requests (1,000,000), "
                "GET, SELECT and all other requests (10,000,000), "
                "Data transfer out to internet (100 GB)"
            ),
            "group": "Data",
        },
        "amazonCloudFront-a7b8c9d0-e1f2-3456-abcd-777788889999": {
            "serviceCode": "amazonCloudFront",
            "serviceName": "Amazon CloudFront",
            "region": "us-east-1",
            "regionName": "US East (N. Virginia)",
            "estimateFor": "CloudFront",
            "version": "0.0.58",
            "description": None,
            "calculationComponents": {
                "dataTransferOutGB": {"value": "2000", "unit": "GB"},
                "httpRequestsMillions": {"value": "50", "unit": "million"},
                "httpsRequestsMillions": {"value": "50", "unit": "million"},
                "originShieldEnabled": {"value": "false"},
            },
            "serviceCost": {"monthly": 165.00},
            "configSummary": (
                "Data transfer out to internet (2,000 GB), "
                "Number of HTTP requests (50,000,000), "
                "Number of HTTPS requests (50,000,000)"
            ),
            "group": "Delivery",
        },
        "AmazonRoute53-b8c9d0e1-f2a3-4567-bcde-888899990000": {
            "serviceCode": "AmazonRoute53",
            "serviceName": "Amazon Route 53",
            "region": "us-east-1",
            "regionName": "US East (N. Virginia)",
            "estimateFor": "Route53",
            "version": "0.0.18",
            "description": None,
            "calculationComponents": {
                "hostedZones": {"value": "5", "unit": "zones"},
                "standardQueriesM": {"value": "100", "unit": "million"},
            },
            "serviceCost": {"monthly": 21.00},
            "configSummary": ("Hosted zones (5), Standard queries (100 million per month)"),
            "group": "Delivery",
        },
        "awswaf-c9d0e1f2-a3b4-5678-cdef-999900001111": {
            "serviceCode": "awswaf",
            "serviceName": "AWS WAF",
            "region": "us-east-1",
            "regionName": "US East (N. Virginia)",
            "estimateFor": "WAF",
            "version": "0.0.14",
            "description": None,
            "calculationComponents": {
                "numberOfWebACLs": {"value": "1", "unit": "ACLs"},
                "numberOfRules": {"value": "10", "unit": "rules"},
                "webRequestsPerMonth": {"value": "50000000", "unit": "perMonth"},
            },
            "serviceCost": {"monthly": 50.00},
            "configSummary": (
                "Web ACLs (1), Rules per ACL (10), Web requests processed (50,000,000 per month)"
            ),
            "group": "Delivery",
        },
    },
    "groups": {
        "grp-app": {"name": "Application"},
        "grp-data": {"name": "Data"},
        "grp-del": {"name": "Delivery"},
    },
    "groupSubtotal": {"monthly": 2266.05},
    "totalCost": {"monthly": 2266.05, "upfront": 0},
    "support": {},
    "metaData": {
        "locale": "en_US",
        "currency": "USD",
        "createdOn": "2026-01-15T10:00:00.000Z",
        "source": "calculator-platform",
        "estimateId": "startup01saas000000000000000000000000001a",
    },
}


@pytest.fixture
def startup_saas_estimate() -> Estimate:
    return Estimate.model_validate(STARTUP_SAAS_ESTIMATE_JSON)
