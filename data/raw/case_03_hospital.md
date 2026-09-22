# Case Study 3: Lakeview Multi-Speciality Hospital

Industry: Healthcare (private hospital group)
Headquarters: Hyderabad
Size: 3,800 employees, 3 hospitals
Service: Cloud Migration and Managed Cloud Support (Standard)
Cloud: Amazon Web Services (ap-south-2, Hyderabad)
Engagement year: 2025

## Situation

Lakeview's hospital information system (appointments, billing, pharmacy)
and its radiology image archive ran in a hospital-owned server room that
had suffered two power-related incidents. The radiology archive was the
largest data set, at roughly 90 terabytes. Clinical availability was the
overriding concern: the group could tolerate no more than a few hours of
planned downtime, and only in the early morning.

## What we did

The estate was 35 servers. Discovery took two weeks and identified that the
radiology archive was best handled by a separate data transfer track rather
than a conventional server rehost. We used an offline data transfer device
shipped to the hospital, then a synchronisation phase to catch up changes
before a short final cutover.

We rehosted 29 servers and replatformed 6 workloads. Every cutover for
clinical systems was scheduled between 2 a.m. and 5 a.m., with clinical
leads on a bridge call. Meridian kept the source environment intact for
the full 14-day rollback window on the hospital information system.

## Timeline

- Week 1 to 2: Discovery and Assessment
- Week 3 to 4: Landing Zone Build
- Week 5 to 14: Migration waves and radiology data transfer
- Week 15 to 18: Hypercare
- Total: 18 weeks from kickoff to end of hypercare

## Commercials

Total project fee approximately INR 22.4 lakh, including an additional
scoped data transfer component for the radiology archive. Managed Cloud
Support Standard for 35 servers on a 12-month term.

## Outcomes

- The hospital information system experienced planned downtime of 2 hours
  and 40 minutes in total across its production cutover.
- The 90 TB radiology archive was migrated with verified checksums on every
  file; no images were lost or altered.
- No patient-facing outage occurred during or after migration during the
  hypercare period.
- The power-related risk of the on-site server room was eliminated for the
  migrated systems.

## Client quote

"For a hospital, planned downtime is measured in minutes, not days.
Meridian planned the radiology transfer separately instead of forcing it
into a standard wave, and that made the difference."
Director of IT, Lakeview Multi-Speciality Hospital