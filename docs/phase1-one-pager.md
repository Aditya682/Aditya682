# Book with AI - Phase 1 One-Pager

## Problem

Planning a Goa trip today requires users to manually search across
multiple sources, compare hotels and activities, and repeatedly adjust
combinations when availability or budget doesn't fit. The core problem is
not finding individual options; it is composing a viable trip under
competing constraints.

A user may start with: *3 days in Goa, 2 travelers, ₹30K, beach +
nightlife.* They then have to search accommodation, search activities,
compare prices and policies, combine options, and make trade-offs when the
initial combination doesn't work.

Book with AI reduces this fragmented planning loop to one goal-driven
experience: the system searches, adapts within predefined boundaries,
surfaces viable combinations, and asks the user only when a genuine
preference trade-off is required.

## Target user

**Primary user:** a leisure traveler planning a short Goa trip who has
clear constraints but does not want to manually compare multiple hotels
and activities.

Typical characteristics: 2-4 travelers, short leisure trip, defined
budget, preferences such as beach/nightlife/food/sightseeing, willing to
provide preferences conversationally, wants a practical bookable
combination rather than a list of individual options.

Initial persona: *"I know roughly what kind of Goa trip I want and what I
can spend, but I don't want to spend an hour jumping between tabs figuring
out what combination actually works."*

## Why agentic

This is agentic because the system isn't simply calculating a ranking
over a fixed dataset. It has a goal and constraints, takes search actions,
observes the results, and can adapt its next search within explicitly
bounded policies.

However, the agent should not have unrestricted autonomy. Safe search
recovery and predefined constraint relaxation can happen automatically.
Any change that alters a user's preference or hard constraint requires
user input. Booking is always behind an explicit confirmation boundary.

The agent therefore owns search and adaptation, while the user retains
control over preference trade-offs and financial commitments. (Full
reasoning and the AUTO/ASK boundary table: `docs/phase0-problem-discovery.md`.)

## Value prop

Tell us the Goa trip you want; Book with AI finds and adapts the
combination for you, instead of making you search and compare it
yourself. Less searching -> fewer manual comparisons -> faster viable
itinerary -> control over important trade-offs.

Three concrete outcomes the product must deliver:

1. **Compose** - combine hotel + activities into a coherent trip rather
   than recommending them independently.
2. **Adapt** - automatically recover from availability/budget failures
   using only predefined safe adaptations.
3. **Escalate intelligently** - ask the user only when resolving the
   problem requires changing a meaningful preference or hard constraint.

The product should not optimize for maximum autonomy. It should optimize
for minimum user effort while preserving user control over consequential
decisions.

## Success metrics

Because Phase 1 has no real-user baseline yet, all targets below are
**provisional hypotheses**, not measured benchmarks.

**Baseline-setting method:** run 5 representative Goa trip-planning
scenarios (varied budgets/preferences), manually planned first (recording
time, number of searches/comparisons, viable combinations found, and
trade-offs required), then repeated with the AI system - manual results
become the initial benchmark. After the first 50 eligible AI planning
sessions, revisit every provisional target against observed distributions
and failure modes; targets may be tightened or relaxed from evidence.

| Metric | Definition | Target | Basis |
|---|---|---|---|
| 1. Trip completion rate | % of eligible sessions where the user explicitly approves a viable combination for booking. **Eligible session** = user provided destination(Goa)/dates/traveler count/budget/≥1 preference; an incomplete abandoned request doesn't enter the denominator. A session that hits the fallback cap and is then resolved via a user-approved compromise counts as **both** a completion and a cap-hit - these measure different things (outcome vs. autonomous-convergence-failure). | ≥60% | Provisional; validate after manual benchmark + 50 sessions |
| 2. Fallback-cap-hit rate | % of eligible sessions where the agent exhausts its 3 adaptation rounds without finding a viable combination under current constraints/safe-adaptation policy. A cap-hit later resolved by user compromise still counts here - a successful human resolution after the cap is still evidence the autonomous policy failed to converge. | ≤10% | Provisional; validate after 50 sessions |
| 3. AUTO / ASK rate | % of *adaptation decisions* (not sessions) resolved without changing a meaningful preference/hard constraint (AUTO) vs. requiring user input (ASK). Not to be optimized for maximum AUTO in isolation - rising AUTO with more unwanted trade-offs is a regression. | ≥70% AUTO / ≤30% ASK | Provisional; validate against manual benchmark trade-offs |
| 4. System processing time | Time the system itself spends processing a request - initial search latency, each adaptation-round latency, recommendation-generation latency, total active processing time. Excludes time waiting on the user. | TBD | Establish via 5-scenario benchmark, not asserted |
| 5. Wall-clock time to viable trip | Time from complete initial request to user approval, *including* time waiting for ASK responses. A UX/funnel metric, not a latency metric - reported alongside #4 so a user taking 20 minutes to answer an ASK doesn't make the agent look technically slow. | TBD | Establish via benchmark + observed user response time |
| 6. Booking mismatch rate | % of completed bookings where the final booking differs from the user-approved confirmation on any critical field (hotel/activity, dates, travelers, room/activity selection, total price, material cancellation terms). | <0.5%, zero tolerance for *silent* mismatches | Product safety threshold - hard guardrail |
| 7. Recommendation grounding rate | % of recommendation facts (price, availability, dates, identity, cancellation terms, material constraints) traceable to the current trusted inventory/booking source rather than LLM-asserted. | 100% | Measurement method defined in Phase 2; Phase 1 requirement is that every bookable fact has an identifiable trusted source |
| 8. Planning effort | Count of user actions to reach an approved trip: searches, comparison steps, AUTO adaptations, ASK interactions, total inputs. Compared against the manual benchmark. | Baseline first | Compare against 5-scenario manual benchmark |

**Phase 1 measurement principle:** where there's no real baseline, label
the number a provisional hypothesis, establish the benchmark first, then
use the first 50 eligible sessions to calibrate launch targets.

## Out of scope - Phase 1

To keep the MVP focused on proving agentic trip composition, Phase 1
covers Goa-only hotel + activity planning and booking. Explicitly out:
flights, multi-city/multi-destination trips, inter-city transportation,
full itinerary optimization across every trip component, payment/wallet
infrastructure or building a payment gateway, autonomous payment without
explicit confirmation, travel insurance, visa/passport services,
international travel, fully autonomous booking without a confirmation
gate, arbitrary web browsing outside approved/trusted inventory sources,
long-running personal travel memory/profile, and open-ended concierge
tasks unrelated to the Goa trip.

```
USER GOAL
   |
Goa hotel + activities
   |
SEARCH
   |
SAFE AUTO ADAPTATION
   |
Preference trade-off? --NO--> RECOMMENDATION -> USER CONFIRMATION -> BOOKING / VERIFY
   |
  YES
   |
ASK USER --> RECOMMENDATION -> USER CONFIRMATION -> BOOKING / VERIFY
```

**Phase 1 success** = prove that bounded agentic search can materially
reduce planning effort without taking preference or booking decisions
away from the user.
