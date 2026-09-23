# Phase 0: Problem discovery

## 1. Deterministic or not?

Not fully. Final ranking over a *known* inventory can be deterministic, but
finding a viable combination is adaptive: search hotels + activities for
the stated constraints; if inventory is empty, unavailable, or pushes the
package over budget, the next action depends on what the previous search
returned (relax rating/location, change activity set, shift dates,
redistribute budget, retry) - not `score(all_known_options) -> return
highest`. Modeled as an agentic workflow with bounded autonomy, not an
unconstrained autonomous agent.

## 2. Today's manual process, and where judgment actually sits

Search accommodation -> compare (price, location, rating, room type,
cancellation, amenities) -> search activities -> compose (hotel + N
activities, sum total) -> iterate if over budget (swap hotel, drop/swap an
activity, change location). The searches themselves are mechanical. Human
judgment sits specifically at the iteration step, resolving competing
preferences when constraints can't all be satisfied simultaneously (e.g.
"I'd rather stay farther from the beach than drop the nightlife
experience") - not "everywhere in the flow."

## 3. Recommendation-wrong vs. booking-wrong

Different failure classes. A wrong *recommendation* is a decision-quality
problem the user can inspect and reject - the agent can search, retry,
compare and explain with real autonomy here. A wrong *booking* is an
external, financially and often irreversibly consequential side effect -
hard autonomy boundary before any transaction, with the confirmation
exposing the actual commitment (hotel, dates, total, cancellation terms),
not a bare "book this?".

## Corrected autonomy boundary (decision-level, not stage-level)

Principle: **the agent may silently change search parameters only when the
change preserves the user's stated intent and doesn't alter a meaningful
preference. It must ask when it changes the user's priorities or creates a
new commitment.**

| Retry / adaptation | AUTO or ASK | Why |
|---|---|---|
| Retry failed API/search request | AUTO | No product decision; just recover |
| Try another hotel within same stated filters | AUTO | Same intent |
| Relax hotel rating (within predefined tolerance) | AUTO | Minor constraint relaxation - *tolerance source is an open question, see below* |
| Expand search radius (within predefined bound) | AUTO | Preserves location intent - *same open question* |
| Try another activity of the same category | AUTO | e.g. one scuba operator -> another |
| Search a nearby date when user said dates are flexible | AUTO | Flexibility was explicitly granted |
| Widen dates when dates were fixed | ASK | Changes a hard constraint |
| Increase budget | ASK | Changes a hard constraint |
| Redistribute budget between hotel/activity | ASK | Changes the user's implicit priorities |
| Remove an activity to fit budget | ASK | Removes something the user asked for |
| Replace nightlife with sightseeing | ASK | Changes preference category |
| Replace beach hotel with inland hotel | ASK, unless location flexibility was granted | Meaningful experience change |
| Downgrade hotel quality materially | ASK | Changes quality preference |
| Use non-refundable instead of refundable | ASK | Changes financial/risk preference |
| Book anything | ASK / explicit confirmation | External financial commitment |

**Open question, not yet resolved:** the relaxation tolerances (rating
delta, radius) are currently an implicit hardcoded product default. Should
this be a fixed policy, or captured once at intake ("how much flexibility
should I use before checking with you?")? Carry into Phase 2/3.

Search loop:
```
Search
  -> No viable combination?
       -> Classify failure
            - Recoverable search failure -> AUTO retry
            - Safe constraint relaxation (within tolerance) -> AUTO retry
            - Preference trade-off required -> ASK
```

## Retry cap and convergence

Bounded adaptation budget, not unlimited retry: initial search + up to 3
adaptation rounds (attempt 1 = same constraints, attempts 2-3 = predefined
safe relaxations in order). The agent cannot invent an unplanned fourth
relaxation.

At the cap: not a bare "cannot fulfill." Return the closest viable
alternatives with the specific constraint each one trades off, e.g.:

> I couldn't find a package matching all your preferences within ₹30,000.
> Closest options: ₹31,800 (keeps beach hotel + both activities) / ₹28,900
> (keeps hotel + nightlife, drops scuba) / ₹29,600 (keeps all activities,
> hotel 3.5km farther from the beach). Which trade-off would you prefer?

"3" is a stated starting policy, not a fixed truth - instrument
convergence-rate-per-attempt, cap-hit rate, most common failing
constraint, user's chosen fallback, and abandonment rate, and adjust from
real behavior (feeds Phase 6).

Stopping condition: the agent stops when it finds a valid result,
encounters a preference-changing decision, or exhausts its bounded
adaptation budget. It cannot silently keep relaxing constraints.

## The confirmation screen cannot trust the LLM

Hard product requirement: **any value presented as a booking commitment
must come from a trusted booking/inventory system or a deterministic
calculation over trusted records - never from model-generated text.** The
LLM may explain the confirmation object; it cannot author it.

```
Agent -> recommendations -> Booking/Inventory source of truth
      -> deterministic validation -> Confirmation UI -> User -> Booking API
```

Confirmation object is structured data (hotel_id, dates, room_type,
guests, hotel_price, activity_price, taxes, total, cancellation_policy),
not LLM prose.

**Pre-booking re-validation (gap found against this project's existing
`tools/booking.py`, which does not currently do this):** after the user
confirms, re-fetch current availability/price, compare against what was
displayed, and only proceed on a match. On a mismatch (e.g. ₹25,400 ->
₹28,900), stop and re-confirm with the user rather than silently
proceeding - inventory can change between recommendation and booking.

## Why agentic - final

This is agentic because the system isn't simply calculating a ranking
over a fixed dataset. It has a goal and constraints, takes search actions,
observes the results, and adapts its next search within explicitly
bounded policies.

The agent should not have unrestricted autonomy. Safe search recovery and
predefined constraint relaxation happen automatically. Any change that
alters a user's preference or hard constraint requires user input. Booking
is always behind an explicit confirmation boundary, itself re-validated
against live inventory before executing.

The agent owns search and adaptation. The user retains control over
preference trade-offs and financial commitments.

> Autonomy is granted to exploration, not to preference decisions or
> irreversible commitments.

## Phase 2 seed: guardrail table (draft)

| Action | Autonomy | Guardrail |
|---|---|---|
| Search inventory | AUTO | Bounded by user constraints |
| Retry failed search | AUTO | Max retry/adaptation budget |
| Switch equivalent inventory | AUTO | Same category/preferences |
| Minor hotel/radius relaxation | AUTO | Predefined tolerance (source TBD - see open question) |
| Change dates | ASK | Unless user explicitly allowed flexibility |
| Increase budget | ASK | Never silently |
| Remove activity | ASK | Never silently |
| Change activity category | ASK | Never silently |
| Materially downgrade hotel | ASK | Never silently |
| Change cancellation terms | ASK | Explicit approval |
| Generate recommendation | AUTO | Must be grounded in retrieved inventory, not invented |
| Display price | AUTO | Must come from trusted source, never LLM-asserted |
| Display cancellation policy | AUTO | Must come from trusted source |
| Initiate booking | GATE | Explicit user confirmation |
| Price/availability changed at confirm time | GATE | Re-confirm, don't silently proceed |
| Execute payment | GATE | Explicit confirmation + trusted payment flow |
| Destructive/irreversible action | DENY/GATE | No autonomous execution |
