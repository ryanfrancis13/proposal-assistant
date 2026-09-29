# Case Study 5: Gyanpath Learning

Industry: Education technology
Headquarters: Bengaluru
Size: 320 employees, 1.8 million registered learners
Service: Cloud Migration (replatform-heavy) and FinOps review
Cloud: Amazon Web Services (ap-south-1, Mumbai)
Engagement year: 2023

## Situation

Gyanpath's learning platform had grown quickly on a mix of rented
dedicated servers and a small AWS footprint. Traffic was highly seasonal,
peaking during exam preparation periods at up to five times the baseline.
The company was over-provisioned for most of the year and under-provisioned
at peak, and its engineering team was small.

## What we did

The estate was 18 servers. Discovery took two weeks. Because the company
wanted to benefit from elasticity, we replatformed 12 workloads (web
tier onto auto-scaling groups, databases onto Amazon RDS, session storage
onto a managed cache) and rehosted 6 supporting servers.

Refactoring the video processing pipeline into a serverless design was
discussed but scoped out of the standard engagement because it required
code changes on Gyanpath's side. It was handled later by Gyanpath's own
engineers.

Six months after migration we performed a FinOps cost optimisation review.

## Timeline

- Week 1 to 2: Discovery and Assessment
- Week 3 to 4: Landing Zone Build
- Week 5 to 9: Two migration waves
- Week 10 to 13: Hypercare
- Total: 13 weeks from kickoff to end of hypercare

## Commercials

Total project fee approximately INR 28.7 lakh. The replatform-heavy
approach raised the per-workload cost relative to a pure rehost. The FinOps
review was purchased separately at INR 95,000.

## Outcomes

- Peak-season capacity increased roughly fourfold with auto-scaling, without
  pre-provisioning.
- After the FinOps review, the customer's monthly cloud bill fell by
  approximately 14 percent through rightsizing and removal of idle
  resources.
- Deployment time for the web tier dropped from about 40 minutes to about
  9 minutes.

## Client quote

"We did not need a giant programme. We needed our platform to stop
falling over at exam time and our bill to stop being a surprise."
Co-founder and CTO, Gyanpath Learning