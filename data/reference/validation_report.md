# Gold Examples Validation Report

**Date:** 2026-03-04 18:26:19
**Total examples:** 4938

## Summary

| Check | Pass | Fail/Warn | Rate |
|-------|------|-----------|------|
| Syntax | 4938 | 0 | 100.0% |
| Enum constraints | 4938 | 0 | 100.0% |
| NL quality | 4938 | 0 | 100.0% |
| NL-query alignment | 4782 | 156 | 96.8% |
| API | -- | -- | Not tested |
| **Overall** | **4938** | **0** | **100.0%** |

## By Category

| Category | Total | Pass | Syntax Fail | API Fail | NL Fail |
|----------|-------|------|-------------|----------|---------|
| affiliation | 76 | 76 | 0 | 0 | 0 |
| astronomy | 41 | 41 | 0 | 0 | 0 |
| author | 565 | 565 | 0 | 0 | 0 |
| bibgroup | 328 | 328 | 0 | 0 | 0 |
| citations | 6 | 6 | 0 | 0 | 0 |
| collection | 112 | 112 | 0 | 0 | 0 |
| compound | 224 | 224 | 0 | 0 | 0 |
| content | 382 | 382 | 0 | 0 | 0 |
| conversational | 50 | 50 | 0 | 0 | 0 |
| data | 27 | 27 | 0 | 0 | 0 |
| doctype | 92 | 92 | 0 | 0 | 0 |
| filters | 668 | 668 | 0 | 0 | 0 |
| first_author | 812 | 812 | 0 | 0 | 0 |
| identifier | 12 | 12 | 0 | 0 | 0 |
| identifiers | 6 | 6 | 0 | 0 | 0 |
| metrics | 57 | 57 | 0 | 0 | 0 |
| object | 34 | 34 | 0 | 0 | 0 |
| operator | 346 | 346 | 0 | 0 | 0 |
| positional | 14 | 14 | 0 | 0 | 0 |
| properties | 17 | 17 | 0 | 0 | 0 |
| property | 169 | 169 | 0 | 0 | 0 |
| publication | 402 | 402 | 0 | 0 | 0 |
| second_order | 24 | 24 | 0 | 0 | 0 |
| syntax | 43 | 43 | 0 | 0 | 0 |
| temporal | 50 | 50 | 0 | 0 | 0 |
| topic | 381 | 381 | 0 | 0 | 0 |

## Common Alignment Warnings

- **85x** NL mentions year(s) [...] but query has no date constraint
- **49x** Query uses first-author (^) but NL doesn't mention 'first author'
- **30x** NL mentions refereed/peer-reviewed but query lacks property:refereed
- **6x** NL mentions 'first author' but query lacks ^ operator
- **3x** Category='first_author' but query has no ^ operator
- **1x** Possible citations/references confusion
