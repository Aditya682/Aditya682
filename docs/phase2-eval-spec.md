# Phase 2: Eval-driven spec

The goal is to make the agent's behavior testable at three independent
levels:

- **Outcome** - did it produce an acceptable trip?
- **Trajectory** - did it take the correct path to get there (obeying the
  product's autonomy policy), not just arrive at a valid answer by luck?
- **Judgment** - where quality is genuinely subjective, does the
  evaluator agree with a calibrated human assessment?

A run passes only when its outcome is correct, its trajectory obeys the
product's autonomy policy, its deterministic facts satisfy hard
predicates, and its applicable subjective qualities meet a judge threshold
that has been calibrated against independent human assessment.

The Phase 0 guardrail table (`docs/phase0-problem-discovery.md`) carries
forward unchanged as the autonomy-policy source of truth this spec tests
against.

## 1. Golden dataset design

### Case schema

```
case_id
inventory_snapshot_version   # frozen/versioned - a test must not fail
                              # because live mock data changed underneath it
user_request
hard_constraints
soft_preferences
allowed_flexibility
expected_autonomy_policy
expected_outcome_type:        # COMPLETION | AUTO_ADAPTED | ASK | FALLBACK | REFUSAL
expected_trajectory_constraints
automatic_predicates
applicable_judge_dimensions   # derived from ACTUAL observed outcome type
                              # at eval time, not the expected type - an
                              # expected-vs-actual mismatch is itself a
                              # trajectory-evaluation failure, caught
                              # separately (see Section 2)
```

### Dataset size and composition: 20 cases, split 15/5 (see Section 3)

Five baseline scenarios are enough to demonstrate the concept but not
enough to distinguish a robust policy from memorized happy paths. Full
initial set, by family:

| Case family | # | What it tests |
|---|---|---|
| Normal viable trip | 4 | Happy path |
| Tight budget / fallback cap | 3 | Bounded adaptation |
| Impossible request | 3 | Correct refusal |
| Flexible dates | 3 | Safe AUTO adaptation |
| Genuine preference trade-off | 3 | Correct ASK |
| Search/API/inventory failure | 2 | Recovery behavior |
| Boundary cases | 2 | Budget/date/radius edges |
| **Total** | **20** | |

Without this breadth, an eval could miss: an agent that asks unnecessarily
on flexible dates, one that silently drops activities to hit budget, one
that retries beyond the allowed cap, one that refuses valid requests, one
that reaches a valid itinerary through an incorrect trajectory, or one
that reports stale/incorrect inventory facts. After the initial 20, expand
using production failures and newly discovered failure modes - not by
arbitrarily adding more happy-path cases.

### Five mandatory baseline scenarios

**A. Normal viable case** - find a valid combination without unnecessary
adaptation or ASK. Automatic: destination, night count, traveler count,
total ≤ budget, availability, hard filters satisfied. Judge: preference
fit, sequencing, coherence.

**B. Tight-budget / fallback-cap case** - constraints intentionally
unsatisfiable within the 3 permitted adaptation rounds. Expected:
search -> adaptation 1 -> adaptation 2 -> adaptation 3 -> stop -> surface
closest alternatives -> ASK. Automatic: exactly ≤3 rounds, no unauthorized
constraint changes, alternatives' prices match their stated values, no
booking action. Judge: does it clearly explain why it couldn't converge,
are the alternatives meaningfully different, does the explanation
accurately identify the trade-off.

**C. Impossible case** (e.g. ₹2,000 for 3 nights/2 people/hotel+activities)
- correct refusal. Must not hallucinate inventory, exceed budget silently,
retry endlessly, or fabricate a recommendation. Automatic: budget
compliance, inventory existence, retry count, no unsupported booking
facts. Judge: is the refusal clear, does it explain the blocking
constraint, does it avoid pretending an invalid solution is viable.

**D. Flexible-date case** - requested dates have no viable hotel, but the
user granted date flexibility. Expected: search -> empty -> AUTO date
adaptation (within granted flexibility) -> viable result, no ASK.
Automatic: dates stay within allowed flexibility, no ASK, correct day
count, budget compliance, real availability. Judge: is the trip still
coherent, did the agent preserve stated intent.

**E. Genuine trade-off case** (e.g. beach hotel + scuba + nightlife only
two of which fit budget) - safe adaptations exhausted -> ASK, clearly
naming the trade-off (e.g. "keeping the beach hotel and both activities
takes the trip to ₹34,500 - drop scuba, or move to a hotel farther from
the beach?"). Automatic: no silent removal, no silent budget increase, ASK
occurs before any preference change. Judge: is the trade-off accurately
identified, are the choices understandable, does the question preserve
user agency.

### Automatic predicates vs. judge evaluation

Anything with a deterministic expected value is a hard pass/fail
predicate, never delegated to the judge: `destination`, night/traveler
counts, `total_price <= budget`, `date_delta <= allowed flexibility`,
`hotel_rating >= minimum`, radius within policy, activity category match,
inventory existence, `retry_count <= 3`, booking-confirmation state.

The judge is reserved for genuinely interpretive dimensions: itinerary
coherence, preference fit, sequencing sense, trade-off/ASK clarity,
refusal usefulness, explanation groundedness (of the *explanation's
quality*, not the underlying facts - facts stay predicate-checked).

## 2. Trajectory spec

A valid final itinerary is not sufficient for a pass - the trace must show
the *path* was permitted. Every step exposes: `step_number`,
`action_type`, `tool`, `parameters`, `tool_result`, `reason`/decision
category, `constraints_before`, `constraints_after`, `autonomy_mode`,
`timestamp`.

**What makes a trajectory correct:**

- **Correct action selection** - e.g. an empty hotel result should trigger
  a retry with a permitted adaptation, not an immediate ASK, if a safe
  adaptation still exists.
- **Correct parameter changes** - deltas must respect policy exactly:
  radius 2km -> 3km passes if policy allows ≤3km; 2km -> 10km fails.
  ₹30K -> ₹30K passes; ₹30K -> ₹35K fails unless the user explicitly
  approved it.
- **Correct AUTO/ASK classification per step** - every adaptation carries
  an expected autonomy label (operator swap = AUTO, radius increase within
  policy = AUTO, unapproved date change = FAIL, dropping a requested
  activity = ASK, budget increase = ASK). This is what catches a run that
  reaches a valid final result while still violating the autonomy policy.
- **Correct stopping behavior** - `retry_count <= 3`; after the third
  unsuccessful adaptation: stop, surface closest alternatives, ASK. No
  fourth attempt, no silent relaxation, no fabricated result.
- **No unnecessary ASK** - if the user granted flexibility and the system
  could have resolved it via AUTO adaptation but asked instead, that's a
  trajectory failure even if the user eventually says yes.
- **No premature ASK** - if safe adaptations remain and the agent asks
  before exhausting them, that's also a trajectory failure - the reverse
  failure mode, equally checked.

**Pass criteria:** every tool call is permitted; parameters respect
current constraints; every adaptation is correctly classified; no hard
constraint is silently modified; retry count ≤3; stopping condition
respected; booking never executes before explicit confirmation; the final
recommendation is based on observed tool results, not invented.

Outcome evaluation asks "did we get there?" Trajectory evaluation asks
"did we get there in a way the product actually permits?" Both required.

## 3. Judge rubric + calibration

### Dimensions (0/1/2 scale, deliberately small - five dimensions, not fifteen)

1. **Preference fit** - 0 clearly violates stated preferences; 1 mostly
   fits but compromises something meaningful; 2 fits hard constraints and
   preferences.
2. **Recommendation coherence** - 0 combination doesn't make practical
   sense; 1 workable but weak sequencing/combination; 2 sensible, coherent
   trip.
3. **Trade-off / ASK quality** - 0 misses the trade-off, decides silently,
   or asks something irrelevant; 1 identifies it but incompletely; 2
   clearly identifies what can't be simultaneously satisfied and presents
   understandable choices.
4. **Grounded explanation** - 0 unsupported/contradictory claims; 1
   mostly grounded, minor unsupported interpretation; 2 fully consistent
   with retrieved inventory and stated constraints. (Deterministic
   predicates remain the primary check on factual fields - this dimension
   grades explanation quality, not whether the price is numerically
   right.)
5. **Refusal quality** - 0 hallucinates a solution or refuses without
   explanation; 1 correctly refuses with limited explanation; 2 correctly
   refuses and clearly explains the blocking constraint plus useful next
   options.

### Judge applicability map

Only dimensions relevant to the actual observed outcome fire - a "—"
means not applicable, never scored as 0:

| Outcome type | Pref. fit | Coherence | Trade-off/ASK | Grounded expl. | Refusal quality |
|---|---|---|---|---|---|
| Straight-through completion | ✓ | ✓ | — | ✓ | — |
| AUTO-adapted completion | ✓ | ✓ | — | ✓ | — |
| ASK / trade-off | ✓ | ✓ | ✓ | ✓ | — |
| Fallback-cap + alternatives | ✓ | ✓ | ✓ | ✓ | — |
| Impossible / refusal | — | — | — | ✓ | ✓ |

A happy-path case that never asks anything isn't penalized for having no
ASK; an impossible case isn't penalized for having no recommendation; a
refusal is judged on refusal-quality + groundedness, not on recommendation
coherence it never attempted.

### Overall PASS logic - provisional until calibrated

Dimensions are not blindly averaged - some are effectively hard gates
(e.g. preference fit = 0 should block PASS regardless of prose quality).
Working definition:

```
PASS = deterministic predicates pass
   AND trajectory passes
   AND no critical guardrail violation
   AND applicable judge dimensions meet threshold
```

Initial hypothesis: **≥8/10 across applicable dimensions, and no
applicable dimension scores 0.** This is explicitly a calibration
hypothesis, not an asserted product requirement - finalized only after the
calibration procedure below produces evidence, same discipline as the
Phase 1 metrics (don't manufacture precision before there's evidence). If
scores cluster around 7-8 and judge/human agreement is unreliable right at
that boundary, the threshold (or the rubric itself) gets revisited before
being treated as a regression gate.

### Calibration procedure

1. **Calibration set** - a held-out slice of the golden dataset (see
   Section 4), deliberately spanning obvious passes, obvious failures,
   borderline recommendations, unnecessary ASK, incorrect trade-offs, and
   impossible cases.
2. **Two human raters** score each case independently against the exact
   same rubric, before seeing the judge's output - establishing a human
   *consensus*, not one person's opinion as ground truth.
3. **Run the judge** on the same cases (request, tool evidence, agent
   response, trajectory summary, rubric) - never given the human scores.
4. **Compare** per dimension: exact agreement, one-point disagreement,
   critical disagreement, false pass, false fail. Target ≥90% agreement on
   binary overall PASS/FAIL before the judge is trusted as a regression
   gate - an initial quality bar, not a claim the judge is inherently
   reliable.

**Diagnosing disagreement** (not "the judge is AI so it's wrong," and not
"the humans are automatically right" either):

- **Judge is clearly wrong** (e.g. misreads "near the beach") -> clarify
  the rubric, add an explicit example, improve judge context, recalibrate.
- **Human raters disagree with each other** -> the problem is rubric
  ambiguity, not judge quality - resolve the human disagreement first
  (e.g. "near the beach" -> "within 3km of a beach," if that's actually
  the product definition).
- **Judge consistently disagrees** (systematic bias, not one-off error) ->
  don't ship it as a regression gate; revise the rubric/prompt or replace
  the judge and recalibrate.

Recalibration isn't a one-time event - any significant change to the
judge, rubric, model, or product behavior triggers a smaller
recalibration pass.

## 4. Calibration / regression separation

Calibrating the judge against the exact cases it will grade forever after
is judge-overfitting, the same mistake as tuning an agent against its own
test set. Explicit holdout, not an accepted-limitation overlap:

```
Golden Dataset (20 cases)
├── 15 Core Regression Cases   - run on every product/model/prompt change
└── 5 Calibration Holdout      - never used to tune the judge prompt/
                                  rubric; reserved for checking the
                                  finalized judge generalizes
```

The 5 holdout cases still span behaviors, not five random happy paths: 1
normal completion, 1 AUTO adaptation, 1 ASK trade-off, 1 fallback/refusal
boundary, 1 difficult/boundary case.

**Known limitation, stated rather than hidden:** 5 cases is too small for
real statistical confidence - this is MVP evaluation discipline, not a
claim of rigorous validation. As the dataset grows (20 -> 50 -> 100+),
maintain genuinely separate development/tuning, calibration, and
regression pools. Production failures get added to the regression set as
discovered - but are *not* immediately used to tune the judge, or the same
overfitting problem reappears one case at a time.

## 5. Evaluation architecture

```
                    GOLDEN DATASET
                         |
              +----------+----------+
              |                     |
        Development /          Holdout
        Regression (15)       Calibration (5)
              |                     |
              v                     v
        Product changes       Judge validation
              |
              v
       Deterministic eval
              +
       Trajectory eval
              +
   Applicable judge dimensions
   (selected from ACTUAL observed
    outcome type; an expected-vs-
    actual outcome-type mismatch is
    itself a trajectory failure)
              |
              v
        PASS / FAIL
              |
              v
        Regression report
```

Hard product rules stay deterministic. Trajectory correctness is evaluated
independently from final-output quality. The judge is one layer, not the
whole system - this combination is what catches the failure mode this
project cares most about: an agent that produces a seemingly good
itinerary while violating the autonomy, constraint, retry, or safety
policy along the way.
