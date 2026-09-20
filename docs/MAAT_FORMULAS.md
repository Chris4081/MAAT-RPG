# MAAT Formulas

This document explains the most important MAAT formulas used in MAAT-RPG and the wider MAAT system.

## The Five MAAT Fields

MAAT uses five structural fields:

- `H` = Harmonie / Harmony
- `B` = Balance
- `S` = Schopfungskraft / Creative power
- `V` = Verbundenheit / Connectedness
- `R` = Respekt / Respect

In MAAT language, these are not just mood labels. They describe structural qualities of a system.

## Intuition Behind the Fields

### H: Harmony

Harmony asks:

- Do the parts fit the whole?
- Is the answer internally coherent?
- Does the structure hold together?

In practical MAAT-RPG terms, H is about internal consistency.

### B: Balance

Balance asks:

- Are competing pressures handled well?
- Is the answer stable between caution and usefulness?
- Are tensions integrated rather than ignored?

In practical terms, B matters whenever the system must avoid both rigidity and drift.

### S: Creative Power

Creative power asks:

- Is there genuine synthesis?
- Are new connections being made?
- Is the response alive, not just mechanically safe?

S is important because MAAT is not meant to crush creativity.

### V: Connectedness

Connectedness asks:

- Is the answer anchored in the actual conversation?
- Is it connected to the user, the context, and the state?
- Does it respond to the real situation instead of drifting away?

In MAAT-RPG, V is especially important for profile, story, and memory alignment.

### R: Respect

Respect is the hard constraint.

R asks:

- Is the answer honest?
- Does it avoid invented certainty?
- Does it treat the user and the truth with care?

In MAAT thinking, R is not negotiable. It functions like a boundary condition.

## Stability

The core stability formula is:

```text
Stability = min(R, 4th_root(H * B * S * V))
```

Meaning:

- the system can only be as stable as its weakest structural coordination
- but it is also capped by Respect

Why `min(R, ...)`?

Because even a very elegant answer should not count as truly stable if it violates respect, truthfulness, or ethical constraint.

## Maat_world

Another broad MAAT expression is:

```text
Maat_world = (H * B * S * V * R) / DeltaE
```

Meaning:

- structural quality grows when the five fields work together
- it drops when disorder, friction, or energy loss grows

`DeltaE` can be read as disorder cost, friction, or destabilizing expenditure.

## PLP

In MAAT-RPG, the most practically relevant formula is PLP:

```text
PLP = ((H * B * S * V * R) * K) / (Hindernisse + DeltaE + epsilon)
```

## What PLP Means

PLP is not just "what I am", but "what I can reliably achieve" in a concrete reply.

It combines:

- structural integrity through `HBSVR`
- `K` as context-truth or knowledge-nearness
- a penalty for barriers and uncertainty

### K: Context or Knowledge Nearness

`K` asks:

- Is the answer close to the actual known context?
- Is it anchored in what is really available?
- Is it epistemically near the truth instead of floating away?

### Hindernisse

`Hindernisse` means obstacles.

Examples:

- contradictions
- missing data
- ambiguous wording
- unsupported numbers
- weak anchoring to the current context

### DeltaE

`DeltaE` in the PLP context represents uncertainty or interpretive effort.

It rises when:

- the problem is complex
- the answer must infer too much
- the system spends too much effort bridging missing structure

### epsilon

`epsilon` is a small stabilizing constant so the denominator never collapses to zero.

## How PLP Is Used in MAAT-RPG

MAAT-RPG uses PLP for hallucination-risk control before final output.

The rough behavior is:

- high PLP -> normal answer allowed
- medium PLP -> answer is softened and uncertainty is marked
- low PLP -> hard claims are blocked and replaced with a safer answer

This makes PLP a practical bridge between MAAT theory and live AI behavior.

## Why HBSVR Matters

If you ask "what is HBSVR for?", the short answer is:

It is a structural lens for judging whether a response is:

- coherent
- balanced
- creative
- connected
- respectful

Instead of using only probability or confidence, MAAT asks whether the whole shape of the response is stable.

## Important Distinction

MAAT does not aim to eliminate creativity.

The point is:

- not to make answers flat
- but to stop elegant hallucinations from pretending to be reliable truth

That is why S stays inside the formula. Creativity is preserved, but it is not allowed to dominate the other fields.

## In One Sentence

MAAT formulas try to measure whether a system is not only producing output, but doing so in a way that is coherent, balanced, creative, connected, and respectful under real-world uncertainty.
