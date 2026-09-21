# Meridian Cloudworks: Cloud Migration Service

Document version: 4.2
Last reviewed: March 2026
Owner: Solutions Engineering

## 1. Overview

Meridian Cloudworks Cloud Migration moves an organisation's servers,
databases, and applications from on-premises data centres or colocation
facilities into public cloud. We migrate to Amazon Web Services and Microsoft
Azure. We do not currently migrate to Google Cloud Platform.

Every migration is delivered as a fixed-scope project with a named
Engagement Lead, a migration architect, and a cutover manager.

## 2. Migration approaches

We use the standard "R" strategies and select one per workload:

- Rehost ("lift and shift"): move the server as-is. Fastest and lowest
  risk. Typical for stable legacy workloads. Around 6 to 8 servers per week
  per migration squad.
- Replatform: small changes to gain cloud benefits, for example moving a
  self-managed database to a managed database service. Around 3 to 4
  workloads per week per squad.
- Refactor: redesign the application to be cloud-native. Priced as a custom
  engagement and not covered by the standard rate card.
- Retire: decommission workloads found to be unused during assessment.

We do not offer mainframe migration. We do not migrate SAP HANA workloads.

## 3. Phases and timeline

Phase 1: Discovery and Assessment (2 to 3 weeks)
An automated scan of the estate followed by workshops with application
owners. Output: a workload inventory, dependency map, cloud landing zone
design, and a migration wave plan with a cost forecast.

Phase 2: Landing Zone Build (2 weeks)
Network, identity, logging, and security baseline in the target cloud.
Follows the CIS Foundations benchmark for the chosen provider.

Phase 3: Migration Waves (variable)
Workloads move in waves of 10 to 25 servers. Each wave has a rehearsal
cutover in a staging window before the production cutover.

Phase 4: Hypercare (4 weeks)
Meridian engineers monitor the migrated estate daily, resolve defects, and
tune performance and cost. Hypercare is included in the migration fee.

As a planning guide, an estate of 40 servers takes about 12 to 14 weeks from
kickoff to the end of hypercare. An estate of 150 servers takes about 24 to
30 weeks.

## 4. Standard rate card (India, INR)

All prices exclude GST at the prevailing rate.

| Component | Unit | Rate (INR) |
|---|---|---|
| Discovery and Assessment | fixed fee up to 50 servers | 4,20,000 |
| Discovery and Assessment | per server above 50 | 6,500 |
| Landing Zone Build | fixed fee, single cloud | 6,50,000 |
| Landing Zone Build | additional cloud (multi-cloud) | 4,00,000 |
| Rehost migration | per server | 38,000 |
| Replatform migration | per workload | 1,15,000 |
| Hypercare | included in migration fee | 0 |
| Project management | 12 percent of migration fees | variable |

Cloud consumption charges (the provider's own bill) are separate and are
paid by the customer directly to the provider.

## 5. Guarantees and service levels

- Migration wave success target: 99 percent of servers in a wave cut over
  without data loss.
- If a wave fails its rehearsal cutover, Meridian re-runs it at no
  additional charge.
- Rollback to the source environment is supported for 14 days after each
  production cutover.
- We do not guarantee a specific cloud cost reduction. We provide a cost
  forecast in Discovery and report actuals during Hypercare.

## 6. Security and compliance

- Meridian is certified to ISO 27001:2022.
- Meridian holds a SOC 2 Type II report for its managed services
  operation. The Cloud Migration service itself is delivered under the ISO
  27001 certification.
- Customer data in transit is encrypted with TLS 1.2 or higher.
- Meridian engineers access customer environments through just-in-time
  privileged access with session recording.
- We support data residency requirements by restricting the landing zone
  to the customer's chosen regions, including Mumbai (ap-south-1 or Central
  India) and Hyderabad (ap-south-2 or South India).

## 7. Customer responsibilities

- Provide read access to the source estate and named application owners
  within one week of kickoff.
- Approve migration waves at least five working days before each cutover.
- Own the final business acceptance of each migrated application.

## 8. Exclusions

Not included in the standard rate card: application code changes,
performance testing of the customer's own applications, end-user training,
third-party software licences, and network circuit provisioning.