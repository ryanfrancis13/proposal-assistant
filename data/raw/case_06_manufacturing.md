# Case Study 6: Alder & Vance Engineering

Industry: Manufacturing (industrial components)
Headquarters: Coimbatore
Size: 1,900 employees, 4 plants
Service: Cloud Migration (hybrid retained)
Cloud: Microsoft Azure (South India)
Engagement year: 2024

## Situation

Alder & Vance ran its ERP, plant scheduling, and quality systems on
on-premises servers at each plant. Plant floor control systems (the
machines and their controllers) had to stay on site for latency and safety
reasons. The company wanted the business systems in the cloud but a
reliable connection back to the plant floor.

## What we did

The migrated estate was 46 servers across the four plants, all business
systems. Discovery took three weeks and drew an explicit boundary between
the business layer (migrated) and the operational technology layer (left in
place). We built a hybrid landing zone with redundant network links from
each plant to Azure.

We rehosted 39 servers and replatformed 7. Network circuit provisioning was
outside Meridian's scope; the customer contracted the carrier links
directly, and we specified the requirements.

An unexpected finding in discovery was that the ERP had an undocumented
dependency on a file share at one plant. This was caught by the dependency
mapping and added to the wave plan before it could cause a failed cutover.

## Timeline

- Week 1 to 3: Discovery and Assessment
- Week 4 to 5: Landing Zone Build
- Week 6 to 15: Migration waves (delayed by two weeks awaiting carrier link
  installation)
- Week 16 to 19: Hypercare
- Total: 19 weeks from kickoff to end of hypercare

## Commercials

Total project fee approximately INR 25.3 lakh. Network circuits were paid by
the customer directly to its carrier.

## Outcomes

- All four plants ran business systems from Azure by the end of the
  engagement, with plant floor systems undisturbed.
- Month-end close, which had taken 5 working days, took 3.
- The two-week schedule slip was caused by carrier installation, not by
  Meridian, and was recorded as a customer dependency in the project log.

## Client quote

"The important line in the plan was the one that said what we were not
moving. Meridian respected it."
Head of IT, Alder & Vance Engineering