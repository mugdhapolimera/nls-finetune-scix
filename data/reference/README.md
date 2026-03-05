# Reference Material

Collected reference material for generating NL-to-query training pairs.

## Contents

- `help/` — Cleaned SciX help documentation, one file per category.
  Collected from `adsabs.github.io/_includes/_help/` using
  `scripts/collect_help_docs.py`.

## Regenerating

```bash
python scripts/collect_help_docs.py \
    --source /path/to/adsabs.github.io \
    --output data/reference/
```
