# Meridian Cloudworks: Cloud Security Posture Service

Document version: 2.1
Last reviewed: January 2026
Owner: Security Practice

## 1. Overview

The Cloud Security Posture Service (CSPS) continuously assesses a customer's
AWS or Azure environment against security benchmarks and reports drift.
It can be purchased alone or added to Managed Cloud Support.

## 2. What is included

- Continuous configuration scanning against the CIS Foundations benchmark
  for AWS or Azure.
- Identity review: unused accounts, over-privileged roles, missing
  multi-factor authentication.
- A monthly posture report with a risk-ranked findings list.
- Remediation guidance for every finding. Meridian will carry out
  remediation only if the customer has Managed Cloud Support Standard or
  Premium; on a standalone CSPS subscription remediation is the customer's
  responsibility.
- A quarterly review call with a Meridian security engineer.

## 3. Pricing (INR, excluding GST)

| Component | Unit | Price |
|---|---|---|
| CSPS subscription | per cloud account per month | 28,000 |
| Minimum term | 12 months | n/a |
| Additional cloud account beyond 5 | per account per month | 22,000 |
| Penetration test (external, one application) | per test | 3,20,000 |

The subscription is priced per cloud account (an AWS account or an Azure
subscription), not per server.

## 4. Discount when bundled

A customer who subscribes to CSPS together with Managed Cloud Support at the
Standard or Premium tier receives a 10 percent reduction on the CSPS
subscription for the term of the support contract.

## 5. Frameworks supported for reporting

CIS Foundations, ISO 27001 Annex A mapping, and RBI cyber security
framework mapping for regulated financial entities. We do not currently
produce HIPAA control mappings.

## 6. Limits

- CSPS is an assessment and reporting service. It is not a managed
  detection and response (MDR) service and does not provide 24x7 security
  operations.
- Penetration testing is performed against agreed targets during agreed
  windows and never against production systems without written approval.