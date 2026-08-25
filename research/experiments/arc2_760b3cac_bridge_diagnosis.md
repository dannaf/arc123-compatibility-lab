# ARC2 `760b3cac` cross-object bridge diagnosis

Date: 2026-08-25
Related: #10, `docs/SEMANTIC_TRANSFER_WAVE2_2026_08_25.md`

## Observation from all visible training pairs

Each input has:

- an upper color-8 shape in the central 3-column band;
- a lower color-4 directional shape.

The output preserves both originals and adds a horizontally reflected copy of the upper 8-shape into one neighboring 3-column band.

The side of the added copy is controlled by the lower 4-shape:

```text
lower 4-shape has its asymmetric tip/marker on the right -> add mirrored 8-shape on the right
lower 4-shape has its asymmetric tip/marker on the left  -> add mirrored 8-shape on the left
```

The held-out lower shape is of the right-control type, and the target adds the reflected upper 8-shape on the right.

## Compatibility interpretation

A representation containing only the changed upper object is insufficient: the same transformation family has a parameter (`left` or `right`) whose value is determined by a spatially separate object.

The semantic crossing should therefore contain an explicit bridge variable:

```text
U = descriptor of source object A (upper 8 shape)
H = orientation descriptor of controller object B (lower 4 shape)
V = reflected-copy placement/effect

M(U,H,V)
```

Forward:

```text
P(V | U,H)
```

predicts the transformation and placement.

Backward:

```text
P(H | U,V)
```

uses the observed training-side effect to constrain which controller orientation is compatible.

This is not a world-level bridge: the bridge is a relation between two objects inside one evidence world.

## Implementation target

The generic learner should:

1. segment separated non-background components / grouped objects;
2. derive small descriptors including color, bbox, orientation/asymmetry, relative position;
3. when one object's transformation parameter varies across demonstrations, search descriptors of other objects as candidate bridge keys;
4. accept the smallest bridge key that restores exact training compatibility;
5. preserve UNKNOWN if a test bridge state was not supported by training;
6. record the learned shared callosal table and backward elimination trace.

Do not add a `760b3cac` task-specific rule. This task is a regression target for generic cross-object bridge induction.
