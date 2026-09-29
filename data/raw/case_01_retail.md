# Case Study 1: Kestrel Retail Group

Industry: Retail (multi-brand apparel)
Headquarters: Chennai
Size: 2,400 employees, 86 stores
Service: Cloud Migration plus Managed Cloud Support (Standard)
Cloud: Amazon Web Services (ap-south-1, Mumbai)
Engagement year: 2024

## Situation

Kestrel ran its point-of-sale back office, inventory system, and e-commerce
backend from a colocation facility whose contract was ending in nine
months. The estate was 42 servers, most of them virtual machines on ageing
hardware. Two outages in the previous festive season had cost an estimated
INR 1.9 crore in lost sales. The board set a hard deadline: be out of the
colocation facility before the contract expired and before the next festive
season.

## What we did

Discovery over three weeks found that 6 of the 42 servers were unused and
could be retired. The remaining 36 split into 30 rehost workloads and 6
replatform workloads (self-managed SQL Server databases moved to Amazon
RDS).

We built the landing zone in two weeks, then migrated in three waves of 12
servers. The inventory database was the most sensitive workload, so it
moved in the second wave with an extended rehearsal window. The e-commerce
backend moved in the third wave over a weekend, timed away from the
promotional calendar.

## Timeline

- Week 1 to 3: Discovery and Assessment
- Week 4 to 5: Landing Zone Build
- Week 6 to 12: Three migration waves
- Week 13 to 16: Hypercare
- Total: 16 weeks from kickoff to end of hypercare

## Commercials

Migration fees (rehost 30 servers, replatform 6 workloads), assessment, and
landing zone came to a total project fee of approximately INR 31.2 lakh.
Kestrel then subscribed to Managed Cloud Support Standard for 36 servers on
a 24-month term, approximately INR 32.0 lakh over the term. Combined
programme value: approximately INR 63.2 lakh.

## Outcomes

- All three waves cut over without data loss. Wave 2 required one
  rehearsal re-run, which Meridian performed at no charge.
- The colocation exit was completed 5 weeks before contract expiry.
- Infrastructure run cost, comparing the final three months in colocation
  with the first three months on AWS after hypercare tuning, fell by 22
  percent.
- During the following festive season, the e-commerce backend handled
  roughly 3.1 times the previous year's peak order volume with no
  unplanned downtime.

## Client quote

"We had a hard date and a bad memory of last year's outages. Meridian gave
us a plan we could put in front of the board and then actually kept to it."
Chief Technology Officer, Kestrel Retail Group