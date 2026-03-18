"""IntentSpec dataclass for structured intent extraction from natural language.

This module defines the typed intent specification that the NER extractor produces
and the assembler consumes. It represents the structured understanding of a user's
search intent before query generation.

The IntentSpec is the contract between:
- NER extraction (produces IntentSpec)
- Few-shot retrieval (uses IntentSpec for similarity)
- Query assembly (consumes IntentSpec to build ADS query)
"""

from dataclasses import asdict, dataclass, field
from json import dumps as json_dumps
from json import loads as json_loads

# Valid ADS operators that wrap queries
# Note: Do NOT add new operators here without adding corresponding gating rules in ner.py
OPERATORS: frozenset[str] = frozenset(
    {
        "citations",  # Find papers that cite the search results
        "references",  # Find papers referenced by the search results
        "trending",  # Find currently popular papers
        "useful",  # Find high-utility papers
        "similar",  # Find textually similar papers
        "reviews",  # Find review articles
    }
)


@dataclass
class IntentSpec:
    """Structured representation of user's search intent.

    This dataclass is the intermediate representation between natural language
    input and ADS query syntax. All fields are extracted by NER and validated
    against FIELD_ENUMS before use.

    Attributes:
        free_text_terms: Topic phrases to search in abs:/title: fields (AND'd together)
        or_terms: Topic phrases that should be OR'd together (e.g., "rocks or volcanoes")
        authors: Author names (will be formatted as "Last, F")
        affiliations: Institutional affiliations for aff: field
        objects: Astronomical objects for object: field
        year_from: Start year for pubdate range (inclusive)
        year_to: End year for pubdate range (inclusive)
        doctype: Document types (must be in DOCTYPES enum)
        property: Record properties (must be in PROPERTIES enum)
        collection: Collection/discipline filter (must be in COLLECTIONS enum)
        bibgroup: Bibliographic groups (must be in BIBGROUPS enum)
        esources: Electronic source types (must be in ESOURCES enum)
        data: Data archive sources (must be in DATA_SOURCES enum)
        operator: Optional wrapper operator (must be in OPERATORS set)
        operator_target: Optional target for operator (e.g., bibcode)
        raw_user_text: Original user input (preserved for debugging)
        confidence: Confidence scores for each extracted field
    """

    # Free text fields
    free_text_terms: list[str] = field(default_factory=list)
    or_terms: list[str] = field(default_factory=list)  # Topics to combine with OR
    authors: list[str] = field(default_factory=list)
    affiliations: list[str] = field(default_factory=list)
    bibstems: list[str] = field(default_factory=list)
    objects: list[str] = field(default_factory=list)
    planetary_features: list[str] = field(default_factory=list)

    # Year range
    year_from: int | None = None
    year_to: int | None = None

    # Constrained enum fields (must be validated against FIELD_ENUMS)
    doctype: set[str] = field(default_factory=set)
    property: set[str] = field(default_factory=set)
    collection: set[str] = field(default_factory=set)
    bibgroup: set[str] = field(default_factory=set)
    esources: set[str] = field(default_factory=set)
    data: set[str] = field(default_factory=set)

    # Operator fields
    operator: str | None = None
    operator_target: str | None = None

    # Negation (LLM-only patterns)
    negated_terms: list[str] = field(default_factory=list)
    negated_properties: set[str] = field(default_factory=set)
    negated_doctypes: set[str] = field(default_factory=set)

    # Field presence (has:body, has:data, etc.)
    has_fields: set[str] = field(default_factory=set)

    # Identifiers (bibcodes, DOIs, arXiv IDs)
    identifiers: list[str] = field(default_factory=list)

    # Keyword terms (keyword: field)
    keyword_terms: list[str] = field(default_factory=list)

    # arXiv class (e.g., astro-ph.HE)
    arxiv_classes: list[str] = field(default_factory=list)

    # ORCID identifiers
    orcid_ids: list[str] = field(default_factory=list)

    # Relative date ranges (stored as raw strings since they use NOW- syntax)
    entdate_range: str | None = None  # e.g., "[NOW-7DAYS TO *]"

    # Metric ranges
    citation_count_min: int | None = None
    citation_count_max: int | None = None
    read_count_min: int | None = None
    mention_count_min: int | None = None
    mention_count_max: int | None = None
    credit_count_min: int | None = None
    credit_count_max: int | None = None
    author_count_min: int | None = None
    author_count_max: int | None = None
    page_count_min: int | None = None
    page_count_max: int | None = None

    # Acknowledgment/grant
    ack_terms: list[str] = field(default_factory=list)
    grant_terms: list[str] = field(default_factory=list)

    # Title-specific terms (title:"X" as distinct from abs:"X")
    title_terms: list[str] = field(default_factory=list)

    # Full-text search (full:"X")
    full_text_terms: list[str] = field(default_factory=list)

    # Advanced
    exact_match_fields: dict[str, str] = field(default_factory=dict)  # {field: value} for =field:"value"

    # Raw clauses that can't be decomposed into structured fields
    # (e.g., complex boolean, pos(), nested operators, identifiers)
    passthrough_clauses: list[str] = field(default_factory=list)

    # Metadata
    raw_user_text: str = ""
    confidence: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate operator is in OPERATORS set if provided."""
        if self.operator is not None and self.operator not in OPERATORS:
            raise ValueError(
                f"Invalid operator '{self.operator}'. Must be one of: {sorted(OPERATORS)}"
            )

    def has_constraints(self) -> bool:
        """Check if any constrained fields are set."""
        return bool(
            self.doctype
            or self.property
            or self.collection
            or self.bibgroup
            or self.esources
            or self.data
        )

    def has_content(self) -> bool:
        """Check if the intent has any searchable content."""
        return bool(
            self.free_text_terms
            or self.or_terms
            or self.authors
            or self.affiliations
            or self.bibstems
            or self.objects
            or self.planetary_features
            or self.year_from
            or self.year_to
            or self.has_constraints()
            or self.negated_terms
            or self.has_fields
            or self.citation_count_min is not None
            or self.mention_count_min is not None
            or self.credit_count_min is not None
            or self.author_count_min is not None
            or self.page_count_min is not None
            or self.ack_terms
            or self.grant_terms
            or self.title_terms
            or self.full_text_terms
            or self.identifiers
            or self.keyword_terms
            or self.arxiv_classes
            or self.orcid_ids
            or self.entdate_range
            or self.passthrough_clauses
        )

    _SET_FIELDS = (
        "doctype", "property", "collection", "bibgroup", "esources", "data",
        "negated_properties", "negated_doctypes", "has_fields",
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization.

        Note: Sets are converted to sorted lists for deterministic output.
        """
        d = asdict(self)
        # Convert sets to sorted lists for JSON serialization
        for key in self._SET_FIELDS:
            d[key] = sorted(d[key])
        return d

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json_dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, d: dict) -> "IntentSpec":
        """Create IntentSpec from dictionary.

        Handles conversion of lists back to sets for enum fields.
        Filters out unknown keys to prevent crashes from extra fields.
        """
        from dataclasses import fields as dc_fields

        valid_keys = {f.name for f in dc_fields(cls)}
        filtered = {k: v for k, v in d.items() if k in valid_keys}
        # Convert lists to sets for enum fields
        for key in cls._SET_FIELDS:
            if key in filtered and isinstance(filtered[key], list):
                filtered[key] = set(filtered[key])
        return cls(**filtered)

    @classmethod
    def from_json(cls, json_str: str) -> "IntentSpec":
        """Deserialize from JSON string."""
        return cls.from_dict(json_loads(json_str))

    def to_compact_dict(self) -> dict:
        """Non-empty fields only, no metadata. For LLM training output."""
        d = self.to_dict()
        # Strip metadata fields that shouldn't appear in training output
        d.pop("raw_user_text", None)
        d.pop("confidence", None)
        return {
            k: v
            for k, v in d.items()
            if v is not None and v != [] and v != {} and v != "" and v != 0
        }

    @classmethod
    def from_compact_dict(cls, d: dict) -> "IntentSpec":
        """Create IntentSpec from compact dict, filtering unknown keys.

        Unlike from_dict(), this safely ignores keys that don't correspond
        to IntentSpec fields (e.g., extra metadata from LLM output).
        """
        from dataclasses import fields as dc_fields

        valid_keys = {f.name for f in dc_fields(cls)}
        filtered = {k: v for k, v in d.items() if k in valid_keys}
        # Convert lists to sets for enum fields
        for key in cls._SET_FIELDS:
            if key in filtered and isinstance(filtered[key], list):
                filtered[key] = set(filtered[key])
        return cls(**filtered)

    def __repr__(self) -> str:
        """Compact representation for debugging."""
        parts = []
        if self.free_text_terms:
            parts.append(f"topics={self.free_text_terms}")
        if self.or_terms:
            parts.append(f"or_topics={self.or_terms}")
        if self.authors:
            parts.append(f"authors={self.authors}")
        if self.year_from or self.year_to:
            parts.append(f"years={self.year_from}-{self.year_to}")
        if self.operator:
            parts.append(f"op={self.operator}")
        if self.negated_terms:
            parts.append(f"NOT={self.negated_terms}")
        if self.has_fields:
            parts.append(f"has={sorted(self.has_fields)}")
        if self.identifiers:
            parts.append(f"identifiers={self.identifiers}")
        if self.keyword_terms:
            parts.append(f"keywords={self.keyword_terms}")
        if self.arxiv_classes:
            parts.append(f"arxiv_classes={self.arxiv_classes}")
        if self.orcid_ids:
            parts.append(f"orcids={self.orcid_ids}")
        if self.entdate_range:
            parts.append(f"entdate={self.entdate_range}")
        if self.citation_count_min is not None:
            parts.append(f"cite_min={self.citation_count_min}")
        if self.mention_count_min is not None:
            parts.append(f"mention_min={self.mention_count_min}")
        if self.credit_count_min is not None:
            parts.append(f"credit_min={self.credit_count_min}")
        if self.author_count_min is not None:
            parts.append(f"author_count_min={self.author_count_min}")
        if self.page_count_min is not None:
            parts.append(f"page_count_min={self.page_count_min}")
        if self.passthrough_clauses:
            parts.append(f"passthrough={self.passthrough_clauses}")
        if self.has_constraints():
            constraints = []
            if self.doctype:
                constraints.append(f"doctype={sorted(self.doctype)}")
            if self.property:
                constraints.append(f"property={sorted(self.property)}")
            if self.bibgroup:
                constraints.append(f"bibgroup={sorted(self.bibgroup)}")
            parts.extend(constraints)
        return f"IntentSpec({', '.join(parts)})"
