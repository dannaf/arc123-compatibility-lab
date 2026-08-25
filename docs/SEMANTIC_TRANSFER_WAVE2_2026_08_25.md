# Semantic transfer wave 2 — 2026-08-25

Related: #6–#10, `docs/LIVE_SEMANTIC_INTERFACE_PROMOTION_2026_08_25.md`

## Owner prompt — verbatim

> Continue more

## 1. P0002 `48f8583b`: frequency-extremum macro state

This historical 0/20-packet failure has the same 3x3 -> 9x9 block-stamping skeleton as `27f8ce4f`, but the trigger predicate differs.

Across its six training demonstrations, the output contains complete copies of the 3x3 input exactly at macro positions whose source input cell has the **least frequent input color**:

- train 1: minority `6`, one active block;
- train 2: minority `9`, two active blocks;
- train 3: minority `1`, three active blocks;
- train 4: minority `3`, one active block;
- train 5: minority `1`, two active blocks;
- train 6: minority `4`, three active blocks.

The held-out input contains five `9`s and four `7`s, so the least-frequent trigger is `7`. The target stamps the full input into exactly the four macro positions containing `7`.

This motivates one generic callosal family:

```text
macro source cell
  + frequency-extremum indicator
        -> active/inactive block
        -> stamped micro-grid or blank block
```

The existing `modal_macro_stamp` remains the canonical most-frequent case (`27f8ce4f`). `src/arc123/frequency_macro_hypotheses.py` adds only the complementary least-frequent case so the learner does not carry duplicate symbolic programs for the same prediction group.

## 2. ARC2 `00576224`: one-bit procedural indicator

The 2x2 input becomes a 6x6 output, i.e. a 3x3 array of 2x2 tiles. Macro rows alternate orientation:

```text
macro-row parity 0 -> original 2x2 tile
macro-row parity 1 -> left-right mirrored tile
macro-row parity 0 -> original tile
```

Thus the missing separator is not a larger pixel neighborhood. It is one procedural bit:

```text
H = macro_row mod 2.
```

Forward:

```text
H=0 -> identity orientation
H=1 -> left-right reflection
```

Backward:

```text
observed tile orientation -> compatible parity class.
```

`src/arc123/relational_tiling_hypotheses.py` implements `AlternatingHorizontalMirrorTile`, and the normal semantic stage now proposes it under the `alternating_mirror_tile` family.

This is a concrete ARC2 instance of the broader SingularityML indicator-state idea: semantic depth grows by a tiny explicit state variable rather than by widening raw marginal scope.

## 3. ARC2 `760b3cac`: diagnosed relational bridge, not yet promoted

This task contains two spatially separated objects:

- an upper color-8 pattern;
- a lower color-4 directional/arrow-like pattern.

The upper object is copied as a horizontal mirror into the neighboring left or right 3-column region. Which side is chosen is controlled by the orientation of the lower color-4 object:

- lower marker at the right side -> mirror-copy upper object to the right;
- lower marker at the left side -> mirror-copy upper object to the left.

The held-out lower object has the right-pointing configuration and the target correspondingly adds the reflected upper pattern on the right.

This is a different missing-interface class from the parity tile:

```text
source object A geometry
bridge object B orientation
        -> transformation/placement of A
```

The important representation point is that the controlling feature is not local to the cells being changed. It is an explicit **cross-object bridge state**. This task should therefore be a regression for the next learner layer: induce a small relation between object descriptors and a transformation parameter, instead of trying another local pixel template.

## 4. Current transfer clusters

The real failures now cluster as follows:

```text
coordinate quotient:
  a85d4709

procedural/run state:
  d037b0a7

macro/micro or block selection:
  007bbfb7
  27f8ce4f  (most-frequent trigger)
  48f8583b  (least-frequent trigger)

one-bit procedural indicator:
  00576224  (macro-row parity -> tile orientation)

overlapping local fibers:
  ARC2 4cd1b7b2

topology:
  00d62c1b

object geometry:
  84f2aca1
  00dbd492

cross-object relational bridge:
  ARC2 760b3cac

unsupported interface state:
  f3e62deb -> remain UNKNOWN at color->direction interface
```

The next architecture target should therefore be **relational bridge induction over object descriptors**: when changed cells are explained by one object but the transformation parameter varies with a second object, search a compact bridge table over the second object's orientation/count/position descriptors and require that it restore exact training compatibility.
