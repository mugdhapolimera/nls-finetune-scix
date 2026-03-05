#!/usr/bin/env python3
"""Collect and clean SciX help documentation from adsabs.github.io.

Reads all .md files from _includes/_help/ in the local adsabs.github.io repo,
strips Jekyll front matter and template directives, and outputs clean markdown
files organized by category.

Usage:
    python scripts/collect_help_docs.py \
        --source ~/github/adsabs.github.io \
        --output data/reference/
"""

import argparse
import re
from pathlib import Path


def strip_front_matter(text: str) -> str:
    """Remove YAML front matter delimited by --- lines."""
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3:].lstrip("\n")
    return text


def clean_jekyll_directives(text: str) -> str:
    """Remove or simplify Jekyll template directives."""
    # Remove {% if ... %} / {% else %} / {% endif %} / {% unless %} / {% endunless %} lines
    text = re.sub(r'{%\s*(?:if|elsif|else|endif|unless|endunless)\b[^%]*%}', '', text)

    # Remove {% include ... %} tags
    text = re.sub(r'{%\s*include\b[^%]*%}', '', text)

    # Remove other {% ... %} tags (for, endfor, assign, capture, etc.)
    text = re.sub(r'{%[^%]*%}', '', text)

    # Replace {{ include.site }} with "SciX" (the common variable)
    text = re.sub(r'\{\{\s*include\.site\s*\}\}', 'SciX', text)

    # Replace {{ site.ads_base_url }} and {{ site.scix_base_url }} with base URLs
    text = re.sub(r'\{\{\s*site\.ads_base_url\s*\}\}', 'https://ui.adsabs.harvard.edu', text)
    text = re.sub(r'\{\{\s*site\.scix_base_url\s*\}\}', 'https://scixplorer.org', text)

    # Remove any remaining {{ ... }} template variables
    text = re.sub(r'\{\{[^}]*\}\}', '', text)

    # Clean up resulting empty lines (collapse 3+ newlines to 2)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text


def clean_html_artifacts(text: str) -> str:
    """Clean up HTML entities and tags that don't render well in plain markdown."""
    # Convert &ldquo; and &rdquo; to regular quotes
    text = text.replace('&ldquo;', '"').replace('&rdquo;', '"')
    text = text.replace('&lsquo;', "'").replace('&rsquo;', "'")
    text = text.replace('&amp;', '&')
    text = text.replace('&nbsp;', ' ')

    # Remove <br> tags
    text = re.sub(r'<br\s*/?>', '\n', text)

    # Keep <figure> / <img> blocks but simplify — just extract alt text and caption
    # Remove empty figure/figcaption tags
    text = re.sub(r'</?figure>', '', text)
    text = re.sub(r'</?figcaption>', '', text)
    text = re.sub(r'</?center>', '', text)
    text = re.sub(r'</?em>', '*', text)

    return text


def collect_help_docs(source_dir: Path) -> dict[str, list[tuple[str, str]]]:
    """Walk _includes/_help/ and collect cleaned content grouped by category.

    Returns:
        Dict mapping category name to list of (filename, cleaned_content) tuples.
    """
    help_root = source_dir / "_includes" / "_help"
    if not help_root.is_dir():
        raise FileNotFoundError(f"Help directory not found: {help_root}")

    categories: dict[str, list[tuple[str, str]]] = {}

    # Skip non-content directories
    skip_dirs = {"_site", ".jekyll-cache"}

    for category_dir in sorted(help_root.iterdir()):
        if not category_dir.is_dir() or category_dir.name in skip_dirs:
            continue

        category = category_dir.name
        posts_dir = category_dir / "_posts"
        if not posts_dir.is_dir():
            continue

        docs = []
        for md_file in sorted(posts_dir.glob("*.md")):
            raw = md_file.read_text(encoding="utf-8", errors="replace")
            cleaned = strip_front_matter(raw)
            cleaned = clean_jekyll_directives(cleaned)
            cleaned = clean_html_artifacts(cleaned)
            cleaned = cleaned.strip()
            if cleaned:
                docs.append((md_file.stem, cleaned))

        if docs:
            categories[category] = docs

    return categories


def write_output(categories: dict[str, list[tuple[str, str]]], output_dir: Path) -> None:
    """Write one .md file per category."""
    help_dir = output_dir / "help"
    help_dir.mkdir(parents=True, exist_ok=True)

    for category, docs in sorted(categories.items()):
        out_path = help_dir / f"{category}.md"
        parts = [f"# {category.replace('_', ' ').title()}\n"]
        for filename, content in docs:
            title = filename.replace("-", " ").replace("_", " ").title()
            parts.append(f"## {title}\n\n{content}\n")

        out_path.write_text("\n".join(parts), encoding="utf-8")
        print(f"  {out_path} ({len(docs)} doc(s))")

    # Write a README
    readme_path = output_dir / "README.md"
    readme_path.write_text(
        "# Reference Material\n\n"
        "Collected reference material for generating NL-to-query training pairs.\n\n"
        "## Contents\n\n"
        "- `help/` — Cleaned SciX help documentation, one file per category.\n"
        "  Collected from `adsabs.github.io/_includes/_help/` using\n"
        "  `scripts/collect_help_docs.py`.\n\n"
        "## Regenerating\n\n"
        "```bash\n"
        "python scripts/collect_help_docs.py \\\n"
        "    --source /path/to/adsabs.github.io \\\n"
        "    --output data/reference/\n"
        "```\n",
        encoding="utf-8",
    )
    print(f"  {readme_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Collect and clean SciX help documentation."
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Path to local adsabs.github.io repo clone.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/reference"),
        help="Output directory (default: data/reference/).",
    )
    args = parser.parse_args()

    if not args.source.is_dir():
        parser.error(f"Source directory not found: {args.source}")

    print(f"Collecting help docs from: {args.source}")
    categories = collect_help_docs(args.source)
    print(f"Found {sum(len(d) for d in categories.values())} docs in {len(categories)} categories.\n")

    print("Writing output:")
    write_output(categories, args.output)
    print("\nDone.")


if __name__ == "__main__":
    main()
