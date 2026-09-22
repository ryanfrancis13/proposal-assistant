# Case Study 2: Sahyadri Cooperative Bank

Industry: Banking (regional cooperative bank)
Headquarters: Pune
Size: 1,150 employees, 74 branches
Service: Cloud Migration, Cloud Security Posture Service, Managed Cloud
Support (Premium)
Cloud: Microsoft Azure (Central India)
Engagement year: 2023 to 2024

## Situation

Sahyadri needed to modernise its non-core banking systems: the internal
reporting platform, document management, and customer relationship tools.
The core banking system stayed on the bank's existing vendor platform and
was explicitly out of scope. As a regulated financial entity, the bank had
to demonstrate compliance with the Reserve Bank of India's cyber security
framework and keep all data within India.

## What we did

The estate in scope was 28 servers. Discovery took three weeks and
produced a workload inventory and a data classification map agreed with
the bank's information security officer. We restricted the Azure landing
zone to Central India and South India regions and enforced this with
Azure Policy so it could not be overridden by a configuration change.

We rehosted 22 servers and replatformed 6 (databases to Azure SQL Managed
Instance). Cutovers were scheduled on Sundays after the branch weekly
close. The bank's auditors reviewed the landing zone design before the
first production cutover.

After migration the bank added the Cloud Security Posture Service with
reporting mapped to the RBI framework, and moved to Premium managed support
because of the 24x7 requirement for incident response.

## Timeline

- Week 1 to 3: Discovery and Assessment
- Week 4 to 5: Landing Zone Build, followed by audit review (2 weeks)
- Week 8 to 13: Two migration waves
- Week 14 to 17: Hypercare
- Total: 17 weeks from kickoff to end of hypercare

## Commercials

Total project fee approximately INR 17.6 lakh. Post-migration, Managed
Cloud Support Premium for 28 servers and CSPS for 3 cloud accounts on a
24-month term.

## Outcomes

- The bank's external auditors raised no findings on the migrated
  environment in the annual IT audit that followed.
- All data remained within the two Indian regions throughout.
- Report generation that previously ran overnight on the old reporting
  server completed in under 40 minutes.
- CSPS identified 31 configuration findings in its first scan, of which 4
  were high risk (mainly over-privileged service accounts inherited from
  the old environment). Meridian's Premium support team remediated all 4
  within the first month.

## Client quote

"The auditors were the audience that mattered to us. Meridian understood
that and built the evidence trail as they went, not afterwards."
Chief Information Security Officer, Sahyadri Cooperative Bank