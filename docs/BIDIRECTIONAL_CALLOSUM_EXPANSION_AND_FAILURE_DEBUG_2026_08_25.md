# Bidirectional callosum expansion + retained-failure debugging — 2026-08-25

Related: #6–#9, `dannaf/SingularityML#3659`.

## Status matrix

| Task | Benchmark | Result under developed semantic interface | Main lesson |
|---|---|---|---|
| `007bbfb7` | ARC1 | exact held-out prediction | deterministic forward / non-invertible backward; prediction singularity without program singularity |
| `0d3d703e` | ARC1 | exact held-out prediction | bijective color callosal joint; both disintegrations deterministic |
| `a85d4709` | ARC1 | **repaired prior P0001 failure; exact held-out prediction** | missing semantic separator was marker-column <-> constant row color |
| `a699fb00` | ARC1 | existing P0001 exact success | row-span semantics already present in IHL baseline |
| `d037b0a7` | ARC1 / ARC2-carried | **repaired prior P0001 failure; exact held-out prediction** | directional propagation; reverse run-collapse reconstructs training sources |
| `4cd1b7b2` | ARC2-new | exact held-out prediction, no branching | row-support ∩ column-support singleton collapse + backdrive |
| `f3e62deb` | ARC1 eval | intentionally unresolved at color->direction interface | unseen held-out colors have no training support; preserve UNKNOWN rather than hallucinate |
| `00d62c1b` | ARC1 | still a target for live learner; semantic diagnosis sharpened | within-example conflict calls for topological `inside enclosure` perception, not a world bridge |

The first six rows are not a claim of a generic ARC solver. They are mechanism microscopes / prior-failure repairs with small semantic families. The decisive remaining work is autonomous discovery of those interfaces.

## Repaired retained failure: `a85d4709`

P0001 previously produced fallback identity and missed all 9 test cells. The training data has a compact generic relation that the initial controller simply did not represent:

- every input row contains exactly one nonzero marker `5`;
- every output row is constant;
- the marker's **column** determines that row's output color.

The learned crossing joint is

```text
marker column 0 <-> row color 2
marker column 1 <-> row color 4
marker column 2 <-> row color 3
```

Both directions are deterministic on the training support. Applying only the forward disintegration to the held-out input produces

```text
3 3 3
2 2 2
4 4 4
```

which is an exact post-commit match. This is a clean example of a failure caused not by insufficient arity but by a missing **derived coordinate/row semantic variable**.

Executable: `research/experiments/bidirectional_callosum_counterexample_debug.py`.

## Additional success: `0d3d703e`

The training examples induce a compact bijective crossing joint over input/output colors:

```text
1<->5, 2<->6, 3<->4, 8<->9
```

with the full observed map containing eight colors. Forward and backward conditionals are both deterministic. The held-out input maps exactly to `[[9,5,4],[9,5,4],[9,5,4]]`.

This is deliberately simple, but it is useful as the bidirectional bijective control against `007`, where the backward side is one-to-many on output zero.

## Failure-debug discipline: `f3e62deb`

The initial IHL controller failed this task. A natural object-level summary of the visible demonstrations is:

```text
color 8 -> move the hollow square to the right boundary
color 6 -> move the hollow square to the top boundary
```

The two held-out objects use colors 4 and 3. At the **color->direction interface**, those contexts have zero observations, not certified zero probability. Two explicit hypotheses

```text
H1: 8->right, 6->up, 4->down, 3->left
H2: 8->right, 6->up, 4->left, 3->down
```

agree on every observed color/direction pair and disagree on the tests. Therefore this interface has no prediction singularity. The correct internal status is `UNKNOWN`, not `IMPOSSIBLE` and not a guessed direction.

Claim boundary: this does **not** prove that the entire ARC task is information-theoretically underdetermined. It proves that the obvious color->direction semantic separator is insufficient. A different task-internal generic relation or a legitimately learned cross-task ontology could still resolve it. This distinction is exactly the purpose of the new compatibility-vs-representation-gap taxonomy.

## `00d62c1b`: why bridges are the wrong repair

The old revival work already observed that the raw local corpus-callosum keys conflict **within individual examples**. A world-level bridge is constant over a whole example, so it cannot separate cells that require different outcomes inside that same world.

The stronger candidate interface is topological:

```text
U = (input color, border-reachable-zero? / enclosed-zero?)
V = output color
```

with the intended relation

```text
3-boundary stays 3
border-connected 0 stays 0
enclosed 0 -> 4
```

This should be implemented as a generic connectedness/enclosure perception and then subjected to the same forward/backward compatibility checks. Backward from observed output `4` should force `enclosed-zero` on training examples; if a proposed enclosure classifier labels such a cell border-reachable, it receives an exact contradiction and is rejected.

That is a qualitatively better repair than increasing raw pixel arity or adding a global bridge.

## Updated refinement taxonomy

The retained failures now support a concrete diagnostic ladder:

1. **Missing low-dimensional semantic coordinate** — `a85d4709`: derive marker position/row semantics.
2. **Missing procedural transition** — `d037b0a7`: derive directional propagation state.
3. **Missing topological perception** — `00d62c1b`: derive enclosure/reachability state.
4. **Locally insufficient but globally intersecting constraints** — `4cd1b7b2`: row/column fibers meet and backdrive.
5. **Unsupported held-out semantic state** — `f3e62deb` at color->direction: remain UNKNOWN unless another justified refinement resolves it.
6. **Multiple programs but one behavior** — `007bbfb7`: stop at prediction singularity rather than forcing unique program identification.

## Immediate implementation consequence

The live learner should add a **semantic-interface proposal ladder** ahead of blind k-growth:

```text
raw/local
-> coordinate/row/column summaries
-> object/component summaries
-> propagation/ray summaries
-> topology/reachability/enclosure
-> bridge/phase/history state
-> composition
```

Each proposal is admitted only if it reduces a measured compatibility/representation gap on training evidence and has generic unit contracts. The callosal joint remains authoritative; forward prediction and backward abduction are derived views.
