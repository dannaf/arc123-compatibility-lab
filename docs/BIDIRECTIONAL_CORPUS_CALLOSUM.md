# Bidirectional Corpus-Callosum Compatibility Learning for ARC1/2/3

Date: 2026-08-25  
Primary implementation tracker: #6  
Related experiment/research issues: #7–#9  
Theory provenance: `dannaf/SingularityML#3659`, `#3644–#3658`, `#3541/#3542`

## 1. Executive thesis

The historical corpus-callosum architecture should be retained, but its mathematical primitive should be sharpened.

Historically, the architecture emphasized a deterministic supervised conditional across two hemispheres:

```text
input/perception side X  -- corpus callosum -->  output/effect side Y
                         P(Y | X)
```

with minimal crossing arity, exact zeros, abstention on unsupported keys, and feature/perception refinement when raw pixels do not suffice.

The strengthened architecture is:

> **The authoritative local object is a nonnegative crossing joint/subjoint. Forward and backward conditionals are two disintegrations of that same crossing object. Learning seeks the smallest semantic callosal representation whose directional views match through one joint, whose local pieces glue globally, whose exact zeros are certified, and whose externally relevant prediction/action is stable.**

So the primitive becomes

```text
                 M(lhs, bridge, rhs)
                /                  \
      forward conditional       backward conditional
      P(rhs | lhs,bridge)       P(lhs,bridge | rhs)
```

The two conditionals are generally **not equal**. The transformation/dynamics need not be invertible. A deterministic forward map can have a genuinely one-to-many backward conditional.

This turns the corpus callosum from a one-way prediction table into a bidirectional compatibility separator.

---

## 2. Why this is a consolidation, not a replacement

The prior ARC CompatibilityNet work already established the key ingredients:

- use only crossing information when possible;
- increment crossing arity only until the relation becomes deterministic;
- deterministic conditionals are sparse / "half-zero" objects, so exact zeros do inference work;
- unsupported contexts abstain rather than hallucinate;
- when the same projected context produces different outcomes, the context language is inadequate and must be refined;
- cross-example conflicts suggest bridge/latent variables, while within-example conflicts often require richer perception/relational channels;
- ARC1/2 and ARC3 are two observable forms of one iterative learner.

The forward/backward theory adds four things:

1. **shared-joint semantics** instead of treating a directional conditional as fundamental;
2. **retrodictive/abductive backdrive** from observed effects/residuals toward possible causes/hypotheses;
3. **exact singularity landmarks** based on equality/compatibility at an interface, distinct from representation adequacy;
4. **temporal gluing and wraparound semantics** for ARC3 trajectory models.

---

## 3. Formal local object

Let

- `U` = left/cause/context/perception state;
- `H` = optional bridge/procedural/hypothesis state;
- `V` = right/effect/output/next-state state.

A **callosal joint** is

```text
M(u,h,v) >= 0,
Σ_{u,h,v} M(u,h,v) = 1
```

or a subnormalized version when convenient.

Its two directional conditionals are

```text
F(v | u,h) = M(u,h,v) / Σ_v M(u,h,v)
B(u,h | v) = M(u,h,v) / Σ_{u,h} M(u,h,v)
```

when the relevant denominator is positive.

A zero-mass conditioning context is **inactive/dead**, not epsilon-filled.

### Compatibility of separately proposed directions

If `F` and `B` are proposed independently, they are compatible iff there exists some nonnegative `M` satisfying both disintegration equations.

For fixed finite conditional tables this is a linear feasibility problem in `M`:

```text
M(u,h,v) = F(v|u,h) * Σ_c M(u,h,c)
M(u,h,v) = B(u,h|v) * Σ_{a,g} M(a,g,v)
Σ M = 1
M >= 0
```

Exact zeros can be added as linear equalities.

### Hidden-zero query

For event `E`, optimize

```text
max_{M in Fiber(I)} M(E).
```

If the optimum is exactly zero, `E` is a compatibility-forced zero relative to the declared interface. Store a replayable dual/certificate where available.

---

## 4. Important guardrail: raw evidence compatibility is trivial

Forward/backward matching is useful only after **semantic compression**.

Raw ARC evidence always admits a giant empirical joint:

- ARC1/2: store each visible training input/output pair as one atom;
- ARC3: store every observed `(state, action, next-state)` transition as one atom.

Deriving both directions from that log is validity-by-construction but proves no generalization.

The substantive problem is:

> Find a compact, generic, reusable representation `R` such that the callosal joints over `R` remain exact enough to reproduce all declared evidence, preserve structural zeros, glue across worlds/time, and support the correct held-out prediction/action.

This is the ARC analogue of the `ABCABD` order-1 warning: a low-order model can be perfectly forward/backward compatible while being wrong about stronger structure.

---

## 5. ARC1/2: static transformation as bidirectional callosal learning

ARC1/2 has no external time evolution inside a task. Instead, each training pair is a parallel evidence world.

For a locus/object/relation `i` in demonstration `d`, define a semantic scope

```text
U_{d,i} = selected input/perception context
H       = candidate rule/program/bridge/procedural state
V_{d,i} = selected output/effect context
```

and a callosal factor

```text
M_{d,i}(U_{d,i}, H, V_{d,i}).
```

### Forward hemisphere

Forward reasoning is the familiar corpus-callosum use:

```text
input/perception + candidate program
        -> predicted output/effect.
```

For sufficiently expressive context, deterministic ARC tasks should often produce sparse or deterministic rows.

### Backward hemisphere

Backward reasoning uses the visible TRAIN output/effect to infer what causes/program states remain possible:

```text
observed train output/residual
        -> compatible source feature / parameter / transform / bridge states.
```

This is **abduction**, not necessarily inversion.

If a transformation maps many different inputs to the same output, then

```text
P(output | input, H)
```

may be deterministic while

```text
P(input,H | output)
```

is multi-valued. That is correct.

### Leak boundary

Backward reasoning may use only:

- visible training outputs;
- learner-generated partial predictions on the held-out input;
- constraints implied by already learned hypotheses.

It must never read the held-out test output.

### Why backward reasoning helps

A forward-only learner asks:

> What transformation might explain this input?

A backward learner also asks:

> Given this output difference, what input object/relation/parameter could have caused it?

That turns residuals into active constraints on the hypothesis space.

Examples:

- an output object has exactly the shape of one input component after rotation: eliminate unrelated source components;
- a recolored region has a boundary matching one input enclosure: eliminate transforms that act on all components;
- a duplicated pattern in the output requires a source tile of a particular period: backdrive the period/selection parameter;
- a known output cell is incompatible with every completion of a candidate partial rule: certify that hypothesis state as zero.

### Program sharing across demonstration worlds

The same semantic program/bridge variables should connect multiple demonstrations when the hypothesis says the same rule applies.

This yields a global task fiber:

```text
Fiber(task) = all callosal assignments/program states
              compatible with every training world simultaneously.
```

A local hypothesis that fits one demonstration but cannot participate in any member of this global fiber is globally dead even if it remains locally plausible.

That is a natural ARC form of a hidden zero.

---

## 6. ARC1/2 singularity and commitment

Distinguish three levels.

### Local callosal singularity

At one selected interface, forward and backward declarations admit the same crossing joint/fiber and all exact overlap conditions agree.

This is an equality/compatibility state, not yet a solved ARC task.

### Program singularity

Only one semantic program/state survives all training evidence.

Useful, but stronger than necessary.

### Prediction singularity

Several programs may survive, but all induce the same complete held-out prediction.

```text
{surviving programs} / ~prediction
```

has one equivalence class.

This is sufficient to commit the ARC1/2 answer.

If several prediction groups remain, the learner is **unsingular/ambiguous**. If benchmark protocol nevertheless forces an answer, the heuristic guess must be reported separately from the exact singularity state.

---

## 7. ARC1/2 refinement policy from incompatibility topology

Do not respond to every conflict by indiscriminately increasing raw arity.

### Case A — within-world conflict

Same compressed local context inside one demonstration produces incompatible output behavior.

Likely missing:

- object identity;
- relative position;
- region membership;
- local/global geometry;
- another relational/perceptual derived variable.

Action: add/split a **perception/procedural feature**.

### Case B — cross-world conflict

A local mapping is stable within each demonstration but differs between demonstrations.

Likely missing:

- global mode;
- marker presence;
- count/parity;
- panel condition;
- task phase;
- another bridge variable constant or structured over the evidence world.

Action: induce a **bridge/context latent** only if evidence supports it.

### Case C — forward/backward compatible but stronger observation fails

The current quotient has a valid joint yet cannot reproduce a longer-range or higher-level fact.

This is the `ABCABD` pattern.

Action: **representation split**, not incompatibility declaration.

### Case D — multiple rules fit every local cell independently but cannot form one common program

Action: solve/refine the **global compatibility fiber** over rule composition/order/scope.

### Case E — one arbitrary fitted representative fails

Do not infer impossibility. Test the full compatible fiber or an exact compressed equivalent.

---

## 8. ARC3: transition callosum

ARC3 makes the same structure temporal and causal.

For transition step `t`, define

```text
U_t = current semantic/perceptual context
A_t = chosen action
H_t = optional phase/bridge/latent/procedural state
V_t = observed effect / next semantic state
```

The authoritative transition joint is

```text
M_t(U_t, A_t, H_t, V_t).
```

### Forward dynamics

```text
F(V_t | U_t, A_t, H_t)
```

predicts the effect of an action.

### Reverse/inverse dynamics

```text
B(U_t, A_t, H_t | V_t)
```

asks which causes/actions/context states are compatible with the observed or desired effect.

Again, this is not required to be a functional inverse.

A button may lead deterministically to a door opening, while the same open-door observation may be reachable by several histories/actions. Forward deterministic, backward multi-valued is entirely valid.

### Raw evidence store should be shared

Every real transition should enter one shared transition-evidence object. Forward and backward empirical tables should be projections of that store rather than independently memorized logs.

The useful mismatch then appears at the **compressed/generalized representation level**.

---

## 9. ARC3 temporal memory and bridge induction

A memoryless representation may declare

```text
same compressed state + same action -> different effects.
```

If the environment is deterministic, this does not mean the world is inconsistent. It means the state representation has merged contexts that must be distinguished.

Candidate refinements include:

- previous observation/action;
- level/phase state;
- a monotone latch such as `has_key`;
- object relation/state;
- a learned predictive causal state;
- a procedural counter/parity/bridge.

This is the temporal form of corpus-callosum arity lifting.

The refinement should be the smallest evidence-supported state split that restores a common transition joint.

### Bidirectional causal state

A useful semantic target is:

```text
forward state  = equivalence class of histories with same future/effect law
reverse state  = equivalence class of futures/effects with same compatible past/cause law
bidirectional state = feasible pair of forward/reverse states.
```

Some Cartesian pairs may be impossible. Those missing pairs are natural hidden-zero objects.

---

## 10. ARC3 path gluing

For an unrolled trajectory, local transition/window joints form a chain.

If adjacent window joints agree exactly on their shared semantic separator, the running-intersection/junction-tree construction gives a global finite-path law.

Therefore a good ARC3 learner can maintain local calibrated windows/separators rather than materializing a giant path distribution.

But two guardrails remain:

1. a too-small semantic state can still be internally calibrated and wrong about longer-range behavior;
2. recurrent/periodic quotient models can introduce genuine loops that require wraparound closure.

---

## 11. ARC3 wraparound / recurrent closure

When the compressed model identifies states around a cycle, open-chain agreement is no longer the entire story.

Use the repository's existing CBN/wraparound discipline:

```text
open the loop
-> propagate the whole admissible coupling/separator fiber
-> apply the closer
-> test whether the closure fiber is nonempty.
```

Do not reject a model merely because one arbitrary representative fails to close.

A genuine empty closure is an exact incompatibility/representation certificate and can backdrive a state split or zero.

---

## 12. Hidden zeros in ARC123

Use a provenance-sensitive taxonomy.

### Visible contradiction zero

A concrete prediction disagrees with a visible training output or observed ARC3 transition under the explicitly declared scope.

### Structural/program zero

A deterministic transform/gate/procedural relation excludes a state by definition.

### Compatibility-forced hidden zero

All local pieces may look individually possible, but no common task/trajectory joint permits the event.

Examples:

- hypothesis `H` explains each demo locally in some representative fit but no one global parameterization explains all demos;
- forward and reverse compressed conditionals each have positive rows but no shared callosal joint exists;
- a candidate ARC3 state/action mode has no completion through the learned transition/phase fiber;
- a forward/reverse causal-state pair never appears because global path compatibility forces it to zero.

### Merely unseen

No evidence yet. Keep `UNKNOWN`.

This is especially important in ARC3 exploration: unseen action/effect combinations are often exactly the epistemic frontier that should be probed, not deleted.

---

## 13. Singularity landmarks for ARC123

Track separate events; never conflate them.

```text
t_local_eq     local F/B callosal compatibility achieved
t_gap          first exact F/B/shared-joint gap at current representation
t_zero(E)      target event first becomes certified zero
t_split        first evidence forcing representation/state split
t_global       all demonstrations/windows glue into one task/path fiber
t_pred         ARC1/2 prediction-equivalence singularity
t_action       ARC3 action-equivalence singularity
t_wrap         first recurrent/wraparound closure failure
t_empty        declared global model fiber becomes empty
```

A model can have `t_local_eq` very early and still need later `t_split` events.

That is not failure of compatibility; it is evidence that compatibility must be maintained at a richer semantic interface.

---

## 14. The unified ARC123 learning loop

```text
OBSERVE
  -> build/update generic perceptions
  -> update shared callosal evidence
  -> derive forward and backward local views
  -> reconcile through exact shared-joint/fiber constraints
  -> propagate visible/certified hidden zeros
  -> classify mismatch topology
  -> choose minimal semantic refinement or probe
  -> backdrive consequences
  -> group surviving global hypotheses by external consequence
  -> commit at prediction/action singularity
```

Expanded:

1. **Observe / attend.** Select a high-information demo region or ARC3 state feature.
2. **Propose a semantic scope.** Choose a minimal set of generic perceptions + optional procedural/bridge variables.
3. **Forward fit.** Ask what output/effect distribution the scope predicts.
4. **Backward fit.** Ask what source/context/hypothesis states the observed effect permits.
5. **Shared-joint check.** Require one `M` to realize both.
6. **Cross-world/time calibration.** Enforce separator/program-state agreement across demonstrations/windows.
7. **Zero mining.** Maximize candidate events over the compatible fiber; certify exact zeros.
8. **Backdrive.** Remove dead hypotheses/parameters/contexts from every incident factor.
9. **Refine when needed.** Perception split, bridge induction, temporal state split, composition, or fiber/wraparound refinement.
10. **Choose the next experiment.** Prefer evidence expected to split surviving prediction/action groups or resolve a compatibility gap.
11. **Collapse/commit.** Commit when all survivors agree on the externally relevant prediction/action.

---

## 15. Active experiment choice

The forward/backward view gives a cleaner target for `CHOOSE_NEXT_DEMO`, `ATTEND`, and ARC3 exploration.

Prefer queries/actions that maximize one or more of:

- number of surviving semantic states separated;
- expected reduction in callosal fiber dimension/support;
- discrimination between prediction/action equivalence classes;
- expected discovery of a hard/hidden zero;
- resolution of a forward/backward mismatch;
- information about a suspected bridge/state split;
- low action cost / reversibility / safety in ARC3.

This is better than merely maximizing prediction entropy. The learner should target **compatibility uncertainty**.

For ARC1/2 the experiments are internal and reversible: inspect another demo, region, object pair, or residual.

For ARC3 the experiments are actual environment actions and must be action-budgeted.

---

## 16. Relationship to the current IHL controller

The existing controller already has the right outer loop:

```text
ATTEND
PROPOSE
APPLY_HYPOTHESIS
COMPARE
FIND_COUNTEREXAMPLE
SPECIALIZE
PROMOTE_CONSTRAINT
COMPOSE
MERGE_RULES
COMMIT
```

The current compatibility layer mainly evaluates partial forward predictions against visible outputs.

The bidirectional extension should add explicit objects such as:

```text
CallosalScope
CallosalJoint
ForwardConditionalView
BackwardConditionalView
SeparatorState
ZeroCertificate
RepresentationGap
PredictionGroup
ActionGroup
```

The main conceptual change is that `COMPARE` should not be only

```text
predicted cell == observed cell ?
```

but also

```text
do the forward and backward declarations admit one shared callosal joint?
do adjacent/world-shared factors glue?
which events are impossible in every compatible realization?
```

---

## 17. Recommended first implementation sequence

### Stage B0 — exact finite shared-joint core

Implement a small finite `CallosalJoint` and exact rational compatibility checker.

Required controls:

- bijective deterministic map;
- many-to-one deterministic map;
- all-positive incompatible directional conditionals;
- dead conditioning context;
- underdetermined compatible fiber.

### Stage B1 — ARC1/2 static backdrive

Use synthetic/generic ARC-like fixtures first.

Demonstrate that known TRAIN output residuals eliminate source objects/parameters/hypotheses through backward conditioning without test-target leakage.

### Stage B2 — bridge vs perception diagnosis

Rebuild the existing bridge-marker style case and a within-example relational conflict.

Show that conflict topology selects different refinement families.

### Stage B3 — ARC3 transition core

Normalize observed transitions into the same `CallosalJoint` API.

Demonstrate forward/reverse conditionals, including irreversible controls.

### Stage B4 — memory refinement

Introduce a trajectory whose compressed memoryless state conflicts, then restore compatibility by the smallest learned phase/bridge state.

### Stage B5 — recurrent wraparound

Add an exact loop-closure fixture with set-valued coupling semantics.

### Stage B6 — real ARC packets

Only after the above contracts pass, wire the mechanism into retained ARC1/2 development packets and blind public-real ARC3 play.

No historical task-shaped schema or oracle semantics may enter the live path.

---

## 18. Benchmark measurements

For every refinement step record:

```text
representation id
raw context width
semantic/procedural state count
maximum callosal arity
number of joint cells
number of forward rows
number of backward rows
support-state counts: UNKNOWN/LIVE/ZERO/DEAD_CONTEXT
fiber dimension or feasible-solution summary
new zero certificates
counterexample topology
refinement chosen
prediction/action group count
query/action cost
```

Also report:

- false-zero claims;
- unsupported exact predictions;
- representation splits;
- bridge inductions;
- maximum carried separator state;
- arithmetic/LP cost;
- held-out leakage checks.

---

## 19. Success criteria

### Tier 1 — semantic correctness

Forward/backward conditionals are derived from or reconciled through one exact shared callosal joint. No inversion assumption; no epsilon zeros.

### Tier 2 — useful backdrive

Backward evidence eliminates hypotheses/parameters and produces inspectable reductions beyond forward-only matching.

### Tier 3 — adaptive representation

The learner distinguishes incompatibility from insufficient representation and makes the correct minimal refinement on the benchmark taxonomy.

### Tier 4 — ARC12 transfer

Bidirectional callosal learning materially improves fresh ARC1/2 curated transfer without test-target leakage or task-shaped fitters.

### Tier 5 — ARC3 action efficiency

The same semantic engine improves blind real-game exploration/action choice by learning compressed transition states and using compatibility uncertainty to select probes.

### Full target

A reusable compact semantic separator/state language that supports exact forward/backward compatibility, hidden-zero backdrive, and prediction/action singularity across ARC1/2/3.

---

## 20. Claim boundary

This document does **not** claim that bidirectional compatibility solves ARC.

In particular:

- the raw evidence joint is trivial;
- a low-order compressed joint can be compatible and still too coarse;
- a forward/backward cycle loss is weaker than shared-joint compatibility;
- shared-joint compatibility is weaker than representation adequacy/generalization;
- polynomial-size semantic state across arbitrary ARC tasks is an open research target.

The intended contribution is a stricter, more informative learning architecture:

> **learn one compact crossing object; use it in both directions; let exact compatibility gaps and hidden zeros drive semantic refinement; and commit only when the surviving compatible theories collapse to one externally relevant consequence.**
