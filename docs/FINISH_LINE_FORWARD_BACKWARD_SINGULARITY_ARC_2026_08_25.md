# Finish line for Forward–Backward Singularity Learning on ARC1/2/3

Date: 2026-08-25

This document defines what would be sufficient to move from promising ARC microscopes and reusable semantic families to a defensible ARC learning architecture claim.

## 1. Claim boundary

The target is **not** "solve ARC by accumulating task-specific programs." The target is a generic learner that discovers a compact semantic separator/corpus-callosum state from visible evidence, maintains exact forward/backward compatibility through that separator, refines the representation when compatibility or prediction faithfulness fails, preserves UNKNOWN when support is absent, and commits only at prediction/action singularity.

For ARC1/2, held-out test outputs must never enter live inference. For ARC3, future observations not yet emitted by the environment must never enter inference.

## 2. Core semantic object

The authoritative learned object should be a shared callosal relation/joint/fiber

`M(U,H,V)`

where:
- `U` is an input/perceptual/source semantic state,
- `H` is optional bridge/procedural/context state,
- `V` is an output/effect semantic state.

Forward and backward conditionals are views of the same object:

`F(V | U,H)` and `B(U,H | V)`.

The learner must not require `F == B` and must not assume invertibility. It must require that both views admit the same nonnegative local joint/coupling and that adjacent local objects agree on shared separators when they are intended to glue into one task/path law.

## 3. Soundness requirements

A finish-line implementation must satisfy all of the following.

1. **No held-out leakage.** The controller receives only training demonstrations + test input for ARC1/2.
2. **UNKNOWN != IMPOSSIBLE.** Unseen or unsupported semantic keys remain UNKNOWN unless an exact compatibility argument forces zero support.
3. **No false exactness.** A hypothesis is called training-exact only if every asserted training cell/effect agrees exactly and the prediction is complete where the hypothesis claims completeness.
4. **Prediction singularity is explicit.** A test answer may be committed when every surviving globally compatible complete hypothesis agrees on that answer, even if latent program singularity has not been reached.
5. **Action singularity is explicit for ARC3.** An action may be committed when all relevant surviving compatible world models agree on the action, even if world-model identification is incomplete.
6. **Bidirectional compatibility is semantic, not cycle loss.** Forward/backward models must share a joint/coupling; approximate `B(F(x)) ~= x` is insufficient.
7. **Provenance for zeros.** Every hard zero/elimination is tagged as observed contradiction, logical/structural consequence, or compatibility-forced hidden zero. Missing observations never become zeros by default.

## 4. Representation grammar required for a serious ARC1/2 learner

Rather than a flat task-specific DSL, use a typed grammar whose primitives are reusable semantic descriptors and whose compositions are searched by evidence.

### Perception types
- cell/color/value;
- row/column summaries and positions;
- connected components **and** non-connected same-color pattern objects;
- bounding boxes, masks, holes, frames, enclosure/reachability;
- counts/frequencies/ranks/extrema;
- symmetry/asymmetry/orientation;
- relative object position, containment, adjacency, alignment;
- macro/micro tilings and quotient coordinates;
- sequence/run/ray/propagation state;
- small indicator state such as parity, phase, latch, count modulo k.

### Transformation types
- recolor/map;
- copy/move/translate;
- reflect/rotate/scale/tile;
- fill/erase/extract;
- propagate along row/column/ray;
- select by descriptor predicate;
- compose transformations;
- conditional transformation selected by bridge state.

### Constraint types
- equality/inequality;
- all-different/permutation;
- exact cardinality;
- overlap/separator equality;
- topology/reachability;
- conservation/invariance where applicable.

## 5. Generic refinement algorithm

A finish-line learner should operate approximately as follows.

1. Start with the smallest raw/local semantic interface.
2. Fit/propose forward and backward views from training evidence.
3. Solve/check the common compatibility fiber.
4. If empty, inspect the minimal conflict topology and propose the smallest semantic lift capable of separating the conflict.
5. If nonempty but known training structure is not faithfully represented, mark a **representation gap**, not an incompatibility, and refine the semantic state.
6. Candidate lifts come from the typed grammar, not from task IDs.
7. Score each lift by:
   - exact contradiction removal,
   - shrinkage of compatibility fiber / prediction groups,
   - reduction of UNKNOWN without inventing support,
   - description length / semantic-state size,
   - transfer evidence from other tasks/synthetic contracts.
8. Backdrive any newly certified zero or singleton into incident constraints.
9. Repeat until prediction singularity, justified abstention/UNKNOWN, or resource bound.

The key architectural requirement is that **counterexample topology chooses the family of semantic lift**. Examples:
- within-row conflict -> positional/coordinate state;
- depth-dependent column conflict -> run/phase state;
- inside/outside conflict -> topology;
- same source behavior controlled by another object -> relational bridge;
- repeated macro blocks -> quotient/macro-micro state;
- regular alternate behavior -> small parity/phase indicator.

## 6. Relative completeness target

Absolute completeness for ARC is not a formally defined finite theorem target. A useful internal theorem is therefore **completeness relative to a bounded semantic grammar**:

> Given a finite typed descriptor/transformation grammar G, a finite composition-depth bound d, and exact training data, the search enumerates or otherwise covers every program/interface in G up to d, rejects exactly contradicted candidates, preserves unsupported candidates as UNKNOWN where appropriate, and returns prediction singularity iff all surviving complete candidates agree on the held-out-input prediction.

This is a concrete theorem/software target. It separates two questions:
- Is search complete relative to our grammar?
- Is the grammar expressive enough for the task distribution?

The first can be engineered/proved. The second is empirical and can be improved by counterexample-driven grammar growth.

## 7. Minimum empirical finish line: ARC1/2

### Gate A — integration
- Full unit suite passes.
- Frozen P0004 rerun over the exact P0002 twenty-task denominator executes from public source pins.
- At least the six independently replayed former failures are exact through the live learner.
- No new operator receives task ID or held-out target.

### Gate B — transfer, not patching
For every promoted semantic family:
- at least two independent real tasks **or** one real task + a synthetic/adversarial family contract;
- an UNKNOWN/adversarial case proving unsupported keys do not silently extrapolate;
- a negative control showing nearby wrong semantic states are rejected.

### Gate C — frozen unseen cohort
Before the final refinement wave, select and hash a new ARC1/2 cohort not used to design the last set of semantic operators. Freeze task IDs and source commits. Then run once under the same live boundary.

A defensible architecture claim requires meaningful exact solves on that frozen cohort and a failure taxonomy for every miss. The score should be compared against:
1. the old raw/local learner;
2. the same semantic grammar with backward compatibility/backdrive disabled;
3. the full forward-backward learner.

The forward-backward system must show measurable improvement in exact solves, false-commit rate, or search/sample efficiency over those ablations.

### Gate D — false-positive discipline
On adversarially perturbed training sets and unsupported held-out semantic keys:
- no invented deterministic mapping;
- incompatible declarations produce an exact conflict/certificate where the implementation claims one;
- compatible-but-underdetermined cases remain UNKNOWN or prediction-nonsingular.

## 8. ARC3 finish line

Extend the same object to transitions:

`M(S_t, A_t, H_t, S_{t+1})`.

Required capabilities:
- forward prediction of effects;
- backward abduction from observed effects to possible prior state/action/bridge state;
- representation refinement when `(compressed state, action)` appears to have contradictory effects;
- action selection by expected compatibility-fiber contraction / information gain;
- action singularity stopping rule;
- temporal window/separator calibration so locally compatible transitions glue into a global trajectory law;
- wraparound/full-fiber closure for genuinely cyclic compressed state models.

Evaluation must compare action count and task completion, not only offline next-state accuracy.

## 9. What would count as "over the finish line" for the research thesis

A strong but attainable research finish line would be:

1. A typed semantic grammar and generic enumerative/compositional refinement engine, not task dispatch.
2. Relative-completeness tests for bounded grammar/depth.
3. Exact shared-joint/coupling semantics for every bidirectional local interface.
4. Event-driven hidden-zero/singleton backdrive.
5. Prediction/action singularity as the commit rule.
6. Frozen source-pinned ARC1/2 development and unseen cohorts with reproducible receipts.
7. Ablations demonstrating that semantic refinement and backward compatibility each add value.
8. A controlled ARC3 implementation using the same representation/compatibility substrate.
9. A claim ledger clearly distinguishing mechanism success, relative completeness, benchmark score, and any broader AGI claim.

At that point it would be defensible to say that **Forward–Backward Singularity Learning is a working ARC learning methodology**. It would still not imply that ARC1/2/3 are fully solved, nor that the method is computationally optimal.

## 10. Current gap after the 2026-08-25 promotion

The repository now has reusable semantic families and a live semantic stage, but it still lacks the main finish-line component:

> a generic search over a typed semantic descriptor/transform grammar in which conflict structure proposes/refines `U`, `H`, and `V`, rather than one Python proposer per semantic family.

This is the architectural bottleneck. More hand-written families can improve a score, but they do not by themselves close the methodology.

The priority therefore is:

**freeze benchmark -> validate current integration -> implement typed descriptor lattice and generic bridge/transform search -> rerun frozen unseen cohort -> ablate forward-only vs forward-backward -> port the same substrate to ARC3.**
