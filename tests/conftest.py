"""Shared fixtures for tests."""

import pytest

from aws_calculator.core.types import Estimate

SAMPLE_ESTIMATE_ID = "e459751ce5e5aa93f254ea8ad3e825af92906379"

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


ENTERPRISE_DATA_PIPELINE_ESTIMATE_JSON = {
    "name": "Enterprise Data Pipeline",
    "services": {
        "amazonKinesis-1a2b3c4d-e5f6-7890-abcd-aabbccddeeff": {
            "serviceCode": "amazonKinesis",
            "serviceName": "Amazon Kinesis Data Streams",
            "region": "us-west-2",
            "regionName": "US West (Oregon)",
            "estimateFor": "KinesisDataStreams",
            "version": "0.0.33",
            "description": None,
            "calculationComponents": {
                "numberOfShards": {"value": "4", "unit": "shards"},
                "putPayloadUnitsPerSecond": {"value": "4000", "unit": "perSecond"},
                "dataRetentionHours": {"value": "168", "unit": "hours"},
                "enhancedFanOutConsumers": {"value": "2", "unit": "consumers"},
            },
            "serviceCost": {"monthly": 1248.00},
            "configSummary": (
                "Number of shards (4), PUT payload units (4,000 per second), "
                "Extended data retention (168 hours), "
                "Enhanced fan-out consumers (2)"
            ),
            "group": "Ingestion",
        },
        "AmazonS3-2b3c4d5e-f6a7-8901-bcde-bbccddeeff00": {
            "serviceCode": "AmazonS3",
            "serviceName": "Amazon Simple Storage Service (S3)",
            "region": "us-west-2",
            "regionName": "US West (Oregon)",
            "estimateFor": "S3",
            "version": "0.0.92",
            "description": "Raw data lake - landing zone and processed partitions",
            "calculationComponents": {
                "storageAmountTB": {"value": "5", "unit": "TB"},
                "putCopyPostListRequests": {"value": "10000000", "unit": "perMonth"},
                "getSelectRequests": {"value": "50000000", "unit": "perMonth"},
                "s3SelectDataScannedGB": {"value": "1024", "unit": "GB"},
                "intelligentTieringEnabled": {"value": "true"},
            },
            "serviceCost": {"monthly": 147.00},
            "configSummary": (
                "S3 Standard storage (5 TB), "
                "PUT, COPY, POST, LIST requests (10,000,000), "
                "GET, SELECT and all other requests (50,000,000), "
                "Data returned by S3 Select (1,024 GB), "
                "S3 Intelligent-Tiering (enabled)"
            ),
            "group": "Ingestion",
        },
        "AWSGlue-3c4d5e6f-a7b8-9012-cdef-ccddeeff0011": {
            "serviceCode": "AWSGlue",
            "serviceName": "AWS Glue",
            "region": "us-west-2",
            "regionName": "US West (Oregon)",
            "estimateFor": "Glue",
            "version": "0.0.61",
            "description": None,
            "calculationComponents": {
                "numberOfDPUs": {"value": "200", "unit": "DPUs"},
                "jobRunsPerDay": {"value": "6", "unit": "perDay"},
                "avgJobDurationMinutes": {"value": "45", "unit": "minutes"},
                "glueVersion": {"value": "3.0"},
            },
            "serviceCost": {"monthly": 2880.00},
            "configSummary": (
                "Number of DPUs (200), Job runs per day (6), "
                "Average job duration (45 minutes), Glue version (3.0)"
            ),
            "group": "Processing",
        },
        "awsstepfunctions-4d5e6f7a-b8c9-0123-defa-ddeeff001122": {
            "serviceCode": "awsstepfunctions",
            "serviceName": "AWS Step Functions",
            "region": "us-west-2",
            "regionName": "US West (Oregon)",
            "estimateFor": "StepFunctions",
            "version": "0.0.27",
            "description": "Pipeline orchestration - daily ETL and ML retraining workflows",
            "calculationComponents": {
                "workflowType": {"value": "Standard"},
                "stateTransitionsPerMonth": {"value": "15000000", "unit": "perMonth"},
            },
            "serviceCost": {"monthly": 45.00},
            "configSummary": (
                "Workflow type (Standard Workflows), State transitions (15,000,000 per month)"
            ),
            "group": "Processing",
        },
        "amazonAthena-5e6f7a8b-c9d0-1234-efab-eeff00112233": {
            "serviceCode": "amazonAthena",
            "serviceName": "Amazon Athena",
            "region": "us-west-2",
            "regionName": "US West (Oregon)",
            "estimateFor": "Athena",
            "version": "0.0.118",
            "description": None,
            "calculationComponents": {
                "dataScannedTBPerMonth": {"value": "192", "unit": "TB"},
            },
            "serviceCost": {"monthly": 960.00},
            "configSummary": "Queries (data scanned per query: 192 TB per month)",
            "group": "Analytics",
        },
        "AmazonSageMaker-6f7a8b9c-d0e1-2345-fabc-ff0011223344": {
            "serviceCode": "AmazonSageMaker",
            "serviceName": "Amazon SageMaker",
            "region": "us-west-2",
            "regionName": "US West (Oregon)",
            "estimateFor": "SageMaker",
            "version": "0.0.88",
            "description": "Model training (ml.p3.2xlarge) + real-time inference endpoint",
            "calculationComponents": {
                "trainingInstanceType": {"value": "ml.p3.2xlarge"},
                "trainingHoursPerMonth": {"value": "200", "unit": "hours"},
                "inferenceInstanceType": {"value": "ml.g4dn.xlarge"},
                "inferenceInstanceCount": {"value": "2", "unit": "instances"},
                "inferenceHoursPerDay": {"value": "24", "unit": "hours"},
            },
            "serviceCost": {"monthly": 4320.00},
            "configSummary": (
                "Training: instance type (ml.p3.2xlarge), hours per month (200), "
                "Inference: instance type (ml.g4dn.xlarge), "
                "number of instances (2), hours per day (24)"
            ),
            "group": "Analytics",
        },
        "AmazonRedshift-7a8b9c0d-e1f2-3456-abcd-001122334455": {
            "serviceCode": "AmazonRedshift",
            "serviceName": "Amazon Redshift",
            "region": "us-west-2",
            "regionName": "US West (Oregon)",
            "estimateFor": "Redshift",
            "version": "0.0.54",
            "description": None,
            "calculationComponents": {
                "nodeType": {"value": "dc2.8xlarge"},
                "numberOfNodes": {"value": "2", "unit": "nodes"},
                "paymentOption": {"value": "On-Demand"},
            },
            "serviceCost": {"monthly": 1920.00},
            "configSummary": (
                "Node type (dc2.8xlarge), Number of nodes (2), Pricing model (On-Demand)"
            ),
            "group": "Analytics",
        },
    },
    "groups": {
        "grp-ing": {"name": "Ingestion"},
        "grp-proc": {"name": "Processing"},
        "grp-anal": {"name": "Analytics"},
    },
    "groupSubtotal": {"monthly": 11520.00},
    "totalCost": {"monthly": 11520.00, "upfront": 0},
    "support": {},
    "metaData": {
        "locale": "en_US",
        "currency": "USD",
        "createdOn": "2026-02-01T08:30:00.000Z",
        "source": "calculator-platform",
        "estimateId": "enterprise0datapipeline000000000000000001",
    },
}


ECOMMERCE_PLATFORM_ESTIMATE_JSON = {
    "name": "E-Commerce Platform",
    "services": {
        "amazonEC2-fe1a2b3c-d4e5-6789-abcd-fe1234567890": {
            "serviceCode": "amazonEC2",
            "serviceName": "Amazon EC2",
            "region": "us-east-1",
            "regionName": "US East (N. Virginia)",
            "estimateFor": "EC2",
            "version": "0.0.134",
            "description": "Auto Scaling web tier - baseline 6 instances, scales to 20",
            "calculationComponents": {
                "instanceType": {"value": "m5.xlarge"},
                "numberOfInstances": {"value": "6", "unit": "instances"},
                "operatingSystem": {"value": "Linux"},
                "tenancy": {"value": "Shared Instances"},
                "paymentOption": {"value": "On-Demand"},
                "utilizationPercentage": {"value": "100", "unit": "percent"},
                "ebsStorageGB": {"value": "30", "unit": "GB"},
            },
            "serviceCost": {"monthly": 840.96},
            "configSummary": (
                "Tenancy (Shared Instances), Operating system (Linux), "
                "Workload (Consistent, Number of instances: 6), "
                "Instance type (m5.xlarge), Pricing model (On-Demand), "
                "EBS storage amount (30 GB)"
            ),
            "group": "Frontend",
        },
        "elasticloadbalancing-fe2b3c4d-e5f6-7890-bcde-fe2345678901": {
            "serviceCode": "elasticloadbalancing",
            "serviceName": "Elastic Load Balancing",
            "region": "us-east-1",
            "regionName": "US East (N. Virginia)",
            "estimateFor": "ELB",
            "version": "0.0.31",
            "description": None,
            "calculationComponents": {
                "elbType": {"value": "Application Load Balancer"},
                "numberOfALBs": {"value": "2", "unit": "units"},
                "lcuPerHour": {"value": "10", "unit": "LCU"},
            },
            "serviceCost": {"monthly": 137.92},
            "configSummary": (
                "Load balancer type (Application), Number of ALBs (2), "
                "Processed bytes per LCU (10 LCU per hour)"
            ),
            "group": "Frontend",
        },
        "amazonCloudFront-fe3c4d5e-f6a7-8901-cdef-fe3456789012": {
            "serviceCode": "amazonCloudFront",
            "serviceName": "Amazon CloudFront",
            "region": "us-east-1",
            "regionName": "US East (N. Virginia)",
            "estimateFor": "CloudFront",
            "version": "0.0.58",
            "description": "Static assets CDN + API cache - global distribution",
            "calculationComponents": {
                "dataTransferOutGB": {"value": "5000", "unit": "GB"},
                "httpRequestsMillions": {"value": "200", "unit": "million"},
                "httpsRequestsMillions": {"value": "200", "unit": "million"},
                "originShieldEnabled": {"value": "true"},
                "originShieldRegion": {"value": "us-east-1"},
            },
            "serviceCost": {"monthly": 330.00},
            "configSummary": (
                "Data transfer out to internet (5,000 GB), "
                "Number of HTTP requests (200,000,000), "
                "Number of HTTPS requests (200,000,000), "
                "Origin Shield (enabled, us-east-1)"
            ),
            "group": "Frontend",
        },
        "awswaf-fe4d5e6f-a7b8-9012-defa-fe4567890123": {
            "serviceCode": "awswaf",
            "serviceName": "AWS WAF",
            "region": "us-east-1",
            "regionName": "US East (N. Virginia)",
            "estimateFor": "WAF",
            "version": "0.0.14",
            "description": None,
            "calculationComponents": {
                "numberOfWebACLs": {"value": "2", "unit": "ACLs"},
                "numberOfRules": {"value": "20", "unit": "rules"},
                "webRequestsPerMonth": {"value": "400000000", "unit": "perMonth"},
            },
            "serviceCost": {"monthly": 75.00},
            "configSummary": (
                "Web ACLs (2), Rules per ACL (20), Web requests processed (400,000,000 per month)"
            ),
            "group": "Frontend",
        },
        "AmazonRoute53-fe5e6f7a-b8c9-0123-efab-fe5678901234": {
            "serviceCode": "AmazonRoute53",
            "serviceName": "Amazon Route 53",
            "region": "us-east-1",
            "regionName": "US East (N. Virginia)",
            "estimateFor": "Route53",
            "version": "0.0.18",
            "description": "Latency-based routing across us-east-1 and eu-west-1",
            "calculationComponents": {
                "hostedZones": {"value": "4", "unit": "zones"},
                "standardQueriesM": {"value": "200", "unit": "million"},
                "latencyRoutingQueriesM": {"value": "100", "unit": "million"},
                "healthChecks": {"value": "12", "unit": "checks"},
            },
            "serviceCost": {"monthly": 35.50},
            "configSummary": (
                "Hosted zones (4), Standard queries (200 million per month), "
                "Latency-based routing queries (100 million per month), "
                "Health checks (12)"
            ),
            "group": "Frontend",
        },
        "amazonEC2-be1f7a8b-c9d0-1234-fabc-be1234567890": {
            "serviceCode": "amazonEC2",
            "serviceName": "Amazon EC2",
            "region": "us-east-1",
            "regionName": "US East (N. Virginia)",
            "estimateFor": "EC2",
            "version": "0.0.134",
            "description": "API workers - 1-year Reserved Instances (partial upfront)",
            "calculationComponents": {
                "instanceType": {"value": "m5.2xlarge"},
                "numberOfInstances": {"value": "8", "unit": "instances"},
                "operatingSystem": {"value": "Linux"},
                "tenancy": {"value": "Shared Instances"},
                "paymentOption": {"value": "Partial Upfront"},
                "reservationTerm": {"value": "1 Year"},
                "utilizationPercentage": {"value": "100", "unit": "percent"},
                "ebsStorageGB": {"value": "100", "unit": "GB"},
            },
            "serviceCost": {"monthly": 1830.88, "upfront": 6480.00},
            "configSummary": (
                "Tenancy (Shared Instances), Operating system (Linux), "
                "Workload (Consistent, Number of instances: 8), "
                "Instance type (m5.2xlarge), "
                "Pricing model (1yr No Upfront Reserved), "
                "EBS storage amount (100 GB)"
            ),
            "group": "Backend",
        },
        "AmazonDynamoDB-be2a8b9c-d0e1-2345-abcd-be2345678901": {
            "serviceCode": "AmazonDynamoDB",
            "serviceName": "Amazon DynamoDB",
            "region": "us-east-1",
            "regionName": "US East (N. Virginia)",
            "estimateFor": "DynamoDB",
            "version": "0.0.96",
            "description": "Product catalog, sessions, and order state",
            "calculationComponents": {
                "capacityMode": {"value": "Provisioned"},
                "readCapacityUnits": {"value": "5000", "unit": "RCU"},
                "writeCapacityUnits": {"value": "1500", "unit": "WCU"},
                "storageGB": {"value": "500", "unit": "GB"},
                "replicaRegions": {"value": "1", "unit": "regions"},
                "daxEnabled": {"value": "false"},
            },
            "serviceCost": {"monthly": 1560.00},
            "configSummary": (
                "Capacity mode (Provisioned), "
                "Provisioned RCU (5,000), Provisioned WCU (1,500), "
                "Table storage (500 GB), "
                "Global tables replicas (1 additional region)"
            ),
            "group": "Backend",
        },
        "amazonElastiCache-be3b9c0d-e1f2-3456-bcde-be3456789012": {
            "serviceCode": "amazonElastiCache",
            "serviceName": "Amazon ElastiCache",
            "region": "us-east-1",
            "regionName": "US East (N. Virginia)",
            "estimateFor": "ElastiCache",
            "version": "0.0.49",
            "description": "Session store and product page cache (Redis Cluster Mode)",
            "calculationComponents": {
                "cacheEngine": {"value": "Redis"},
                "nodeType": {"value": "cache.r6g.large"},
                "numberOfNodes": {"value": "8", "unit": "nodes"},
                "paymentOption": {"value": "On-Demand"},
            },
            "serviceCost": {"monthly": 780.48},
            "configSummary": (
                "Cache engine (Redis), Node type (cache.r6g.large), "
                "Number of nodes (8), Pricing model (On-Demand)"
            ),
            "group": "Backend",
        },
        "AmazonSQS-be4c0d1e-f2a3-4567-cdef-be4567890123": {
            "serviceCode": "AmazonSQS",
            "serviceName": "Amazon Simple Queue Service (SQS)",
            "region": "us-east-1",
            "regionName": "US East (N. Virginia)",
            "estimateFor": "SQS",
            "version": "0.0.38",
            "description": "Order processing and inventory update queues",
            "calculationComponents": {
                "requestsPerMonth": {"value": "300000000", "unit": "perMonth"},
                "queueType": {"value": "Standard"},
                "messageSizeKB": {"value": "5", "unit": "KB"},
            },
            "serviceCost": {"monthly": 32.00},
            "configSummary": (
                "Queue type (Standard), Requests (300,000,000 per month), Message size (5 KB)"
            ),
            "group": "Backend",
        },
        "AmazonSNS-be5d1e2f-a3b4-5678-defa-be5678901234": {
            "serviceCode": "AmazonSNS",
            "serviceName": "Amazon Simple Notification Service (SNS)",
            "region": "us-east-1",
            "regionName": "US East (N. Virginia)",
            "estimateFor": "SNS",
            "version": "0.0.29",
            "description": "Order confirmation and shipping notification push/email fan-out",
            "calculationComponents": {
                "publishRequestsPerMonth": {"value": "10000000", "unit": "perMonth"},
                "httpDeliveriesPerMonth": {"value": "5000000", "unit": "perMonth"},
                "emailDeliveriesPerMonth": {"value": "2000000", "unit": "perMonth"},
            },
            "serviceCost": {"monthly": 12.00},
            "configSummary": (
                "Publish requests (10,000,000 per month), "
                "HTTP/S deliveries (5,000,000 per month), "
                "Email/Email-JSON deliveries (2,000,000 per month)"
            ),
            "group": "Backend",
        },
        "AmazonVPC-in1e2f3a-b4c5-6789-efab-in1234567890": {
            "serviceCode": "AmazonVPC",
            "serviceName": "Amazon Virtual Private Cloud (VPC)",
            "region": "us-east-1",
            "regionName": "US East (N. Virginia)",
            "estimateFor": "NATGateway",
            "version": "0.0.22",
            "description": "NAT Gateways - 2 AZs for high availability",
            "calculationComponents": {
                "numberOfNATGateways": {"value": "2", "unit": "gateways"},
                "dataProcessedGBPerMonth": {"value": "500", "unit": "GB"},
            },
            "serviceCost": {"monthly": 64.80},
            "configSummary": ("NAT gateway (2 gateways), Data processed (500 GB per month)"),
            "group": "Infrastructure",
        },
        "AmazonRoute53-in2f3a4b-c5d6-7890-fabc-in2345678901": {
            "serviceCode": "AmazonRoute53",
            "serviceName": "Amazon Route 53",
            "region": "us-east-1",
            "regionName": "US East (N. Virginia)",
            "estimateFor": "Route53HealthChecks",
            "version": "0.0.18",
            "description": "Endpoint health checks for failover routing",
            "calculationComponents": {
                "healthChecks": {"value": "20", "unit": "checks"},
                "healthCheckIntervalSeconds": {"value": "30", "unit": "seconds"},
            },
            "serviceCost": {"monthly": 21.00},
            "configSummary": ("Health checks (20), Health check interval (30 seconds)"),
            "group": "Infrastructure",
        },
    },
    "groups": {
        "grp-front": {"name": "Frontend"},
        "grp-back": {"name": "Backend"},
        "grp-infra": {"name": "Infrastructure"},
    },
    "groupSubtotal": {"monthly": 5720.54},
    "totalCost": {"monthly": 5720.54, "upfront": 6480.00},
    "support": {},
    "metaData": {
        "locale": "en_US",
        "currency": "USD",
        "createdOn": "2026-03-01T14:00:00.000Z",
        "source": "calculator-platform",
        "estimateId": "ecommerce0platform0000000000000000000001",
    },
}


@pytest.fixture
def startup_saas_estimate() -> Estimate:
    return Estimate.model_validate(STARTUP_SAAS_ESTIMATE_JSON)


@pytest.fixture
def enterprise_data_pipeline_estimate() -> Estimate:
    return Estimate.model_validate(ENTERPRISE_DATA_PIPELINE_ESTIMATE_JSON)


@pytest.fixture
def ecommerce_platform_estimate() -> Estimate:
    return Estimate.model_validate(ECOMMERCE_PLATFORM_ESTIMATE_JSON)
