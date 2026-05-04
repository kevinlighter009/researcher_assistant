# Pending patch: add `rl` category to SKILL.md

This file is a manual checklist — sandbox restrictions prevented writing the patch directly to `SKILL.md` during the session that introduced the `doc/papers/rl/` folder. Apply the four edits below (all in `SKILL.md`).

## 1. Frontmatter description (line ~3)

**Find:**
```
description: Use when reading a research-paper PDF (typically autonomous-driving — VLA, diffusion decoder, world model, end-to-end planning, perception, datasets) ...
```

**Replace with:**
```
description: Use when reading a research-paper PDF (typically autonomous-driving — VLA, diffusion decoder, world model, end-to-end planning, perception, RL, datasets) ...
```

## 2. Add `rl` row to the `primary_category` enum table

**Find:**
```
| `perception` | 3D detection, BEV, occupancy, HD-mapping |
| `datasets` | Datasets and benchmarks |
| `misc` | Anything that doesn't fit |
```

**Replace with:**
```
| `perception` | 3D detection, BEV, occupancy, HD-mapping |
| `rl` | Reinforcement learning (model-free, model-based, RL-coach IL hybrids, RLHF) for driving policies |
| `datasets` | Datasets and benchmarks |
| `misc` | Anything that doesn't fit |
```

## 3. Add tie-breaker bullet for `rl`

**Find:**
```
- Paper's contribution is upstream of planning (3D detection, BEV, occupancy, mapping)? → `perception`
- Paper introduces or evaluates on a new dataset / benchmark and that's the contribution? → `datasets`
```

**Replace with:**
```
- Paper's contribution is upstream of planning (3D detection, BEV, occupancy, mapping)? → `perception`
- Paper's headline is an RL algorithm, RL coach, model-based RL world-model-for-RL, or RL-from-feedback for the driving policy? → `rl` (use `world_model` only if the generative model itself is the central contribution and RL is a downstream consumer; use `vla` only if an LLM/VLM is the policy backbone)
- Paper introduces or evaluates on a new dataset / benchmark and that's the contribution? → `datasets`
```

## 4. Bump "7 enumerated values" → "8 enumerated values" (3 occurrences)

Find every occurrence of `7 enumerated values` and replace with `8 enumerated values`. As of the last reading of SKILL.md these appeared in:

- The Step 5 YAML rules block (`primary_category: <one of the 7 enumerated values>`)
- The Step 5 closing rules (`primary_category` must be one of the 7 enumerated values exactly)
- The Step 6 self-check (`primary_category` is one of the 7 enumerated values)

After applying these four edits, delete this patch file.
