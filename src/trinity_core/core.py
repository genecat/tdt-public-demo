"""Trinity Core: concentration, dispersion, and static balance (Stage 4).

Locked behavior matches ``TDT_v1_computation_spec.md`` and the lineage implementation
in ``ev_ai_cross_model_static_balance_audit.py`` (``balance_S``, ``text_concentration_dispersion``).
No thresholds, tags, or sham logic.
"""

from __future__ import annotations

import math
import re
import statistics
from collections import Counter
from typing import Any

# Lineage-frozen constant (EPS in audit script).
EPSILON = 0.08

# Phase 2 row diagnostics: ``primary_weakness`` string values.
PRIMARY_WEAKNESS_SEMANTIC = "semantic_repetition_score"
PRIMARY_WEAKNESS_TOPIC = "topic_drift_score"
PRIMARY_WEAKNESS_SPECIFICITY = "specificity_vagueness_score"
PRIMARY_WEAKNESS_STRUCTURAL = "structural_coherence_score"
PRIMARY_WEAKNESS_INTERNAL = "internal_consistency_score"
# Labeling-only: no single signal clearly dominates (see ``_primary_weakness_from_scores``).
PRIMARY_WEAKNESS_MULTI_FACTOR = "multi_factor"

# --- primary_weakness label selection (raw scores in rows are unchanged) ---
_PRIMARY_WEAKNESS_TOPIC_LABEL_SOFTEN = 0.88
_PRIMARY_WEAKNESS_TOPIC_LABEL_MAX_OTHER_PAD = 0.10
_PRIMARY_WEAKNESS_DOMINANCE_MARGIN = 0.095

# --- instruction_alignment_score v1 (Phase 2; first pass) ---
INSTRUCTION_ALIGNMENT_MODE_FULL = "full"
INSTRUCTION_ALIGNMENT_MODE_DEGRADED = "degraded"
# Degraded mode is a capped non-answer / side-step proxy only (must not match full alignment).
_INSTRUCTION_ALIGNMENT_DEGRADED_CAP = 0.40
_INSTRUCTION_ALIGNMENT_MIN_TASK_CHARS = 12
# Refusal / evasion cues (case-insensitive search on lowercased text).
_IA_REFUSAL_REGEX = re.compile(
    r"(?:"
    r"\bi\s+can'?t\s+(?:comply|assist|help|provide)|"
    r"\bi\s+am\s+unable\s+to|"
    r"\bi\s+don'?t\s+have\s+access\s+to\s+(?:your|the)\s+prompt|"
    r"\bas\s+an\s+ai\s+language\s+model|"
    r"\bi\s+cannot\s+(?:fulfill|comply|answer)|"
    r"\bunable\s+to\s+comply|"
    r"\bnot\s+able\s+to\s+answer\s+that"
    r")",
    re.IGNORECASE,
)
# Task-derived exclusion: quoted phrase after "do not mention/include".
_IA_TASK_EXCLUSION_QUOTED = re.compile(
    r"\bdo\s+not\s+(?:mention|include|use)\s+[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)

# --- critical_slot_integrity_score v1 (Phase 2; rubric expected_item_count only) ---
CRITICAL_SLOT_INTEGRITY_MODE_FULL = "full"
CRITICAL_SLOT_INTEGRITY_MODE_DEGRADED = "degraded"
# Degraded mode cannot reach full rubric-aware slot scores (reserved for future proxies).
_CRITICAL_SLOT_INTEGRITY_DEGRADED_CAP = 0.40

# --- information_density_score v1 (Phase 2; response_text only, three channels) ---
_INFORMATION_DENSITY_MIN_TOKENS = 12
_INFORMATION_DENSITY_TTR_TARGET = 0.62
_INFORMATION_DENSITY_CONTENT_TARGET = 0.50
_INFORMATION_DENSITY_HAPAX_TARGET = 0.40
# English function words; content tokens are ``len >= 2``, not pure digits, not in this set.
_ID_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "if",
        "as",
        "at",
        "by",
        "for",
        "from",
        "in",
        "into",
        "is",
        "am",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "it",
        "its",
        "of",
        "on",
        "to",
        "too",
        "with",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "shall",
        "can",
        "this",
        "that",
        "these",
        "those",
        "i",
        "you",
        "he",
        "she",
        "we",
        "they",
        "me",
        "him",
        "her",
        "us",
        "them",
        "my",
        "your",
        "our",
        "their",
        "what",
        "which",
        "who",
        "whom",
        "whose",
        "there",
        "here",
        "when",
        "where",
        "why",
        "how",
        "all",
        "each",
        "every",
        "both",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "nor",
        "not",
        "only",
        "own",
        "same",
        "so",
        "than",
        "very",
        "just",
        "also",
        "now",
        "then",
        "once",
        "because",
        "while",
        "although",
        "though",
        "about",
        "above",
        "after",
        "again",
        "against",
        "among",
        "around",
        "before",
        "below",
        "between",
        "beyond",
        "during",
        "except",
        "following",
        "including",
        "like",
        "near",
        "off",
        "over",
        "since",
        "through",
        "toward",
        "towards",
        "under",
        "until",
        "upon",
        "within",
        "without",
        "any",
        "either",
        "neither",
        "one",
        "ones",
        "via",
        "per",
    }
)

# Hedging / stance-softening (higher density → more vague risk).
_HEDGE_LEX = frozenset(
    {
        "maybe",
        "perhaps",
        "might",
        "could",
        "would",
        "should",
        "possibly",
        "probably",
        "likely",
        "unlikely",
        "generally",
        "roughly",
        "somewhat",
        "sort",
        "kind",
        "basically",
        "essentially",
        "unclear",
        "depends",
        "depending",
        "seems",
        "seem",
        "appears",
        "appear",
        "think",
        "guess",
        "hopefully",
        "partially",
        "partly",
        "um",
        "uh",
        "well",
    }
)
# Generic / non-committal referents.
_VAGUE_LEX = frozenset(
    {
        "something",
        "anything",
        "nothing",
        "everything",
        "someone",
        "somehow",
        "somewhere",
        "stuff",
        "thing",
        "things",
        "aspects",
        "situation",
        "alignment",
    }
)
# Concrete / operational anchors (presence lowers vagueness risk).
_CONCRETE_OPS_LEX = frozenset(
    {
        "ship",
        "implement",
        "implementing",
        "deadline",
        "deadlines",
        "metric",
        "metrics",
        "owner",
        "owners",
        "contract",
        "api",
        "spike",
        "measure",
        "adoption",
        "expand",
        "slice",
        "lock",
        "write",
        "reads",
        "read",
        "scope",
        "risks",
        "mitigate",
        "feasible",
        "week",
        "weeks",
        "days",
        "q1",
        "q2",
        "q3",
        "q4",
    }
)
# Discourse scaffolding (presence lowers structural fragmentation risk).
_STRUCTURE_LEX = frozenset(
    {
        "first",
        "firstly",
        "second",
        "secondly",
        "third",
        "thirdly",
        "next",
        "then",
        "finally",
        "lastly",
        "overall",
        "summary",
        "step",
        "steps",
        "part",
        "parts",
    }
)
# Commitment polarity (co-occurrence suggests unresolved tension).
_STANCE_POS_LEX = frozenset(
    {
        "recommend",
        "approve",
        "support",
        "proceed",
        "ship",
        "adopt",
        "accept",
        "endorse",
        "defend",
    }
)
_STANCE_NEG_LEX = frozenset(
    {
        "reject",
        "refuse",
        "avoid",
        "cancel",
        "oppose",
        "withdraw",
        "deny",
        "block",
        "halt",
    }
)
_CONTRAST_LEX = frozenset(
    {
        "but",
        "however",
        "although",
        "though",
        "whereas",
        "nevertheless",
        "yet",
    }
)
# internal_consistency v2: forward vs delay/hold cues (lexical only).
_IC_FORWARD_ACTION = re.compile(
    r"\b(launch|ship|proceed|rollout|move\s+forward|moving\s+forward)\b",
    re.IGNORECASE,
)
_IC_HOLD_OR_DELAY = re.compile(
    r"\b(postpone|postponed|waiting|wait\s+until|not\s+launch|launch\s+yet|"
    r"do\s+not\s+launch|halt|delay|uncertainty)\b",
    re.IGNORECASE,
)


def balance_S(c: float, d: float) -> float:
    """Static balance S = clip(1 - |c-d|/(c+d+ε), 0, 1) with ε = EPSILON."""
    c = max(0.0, float(c))
    d = max(0.0, float(d))
    dist = abs(c - d) / (c + d + EPSILON)
    return float(max(0.0, min(1.0, 1.0 - dist)))


def text_concentration_dispersion(text: str) -> tuple[float, float]:
    """Benchmark-blind lexical proxies for concentration *c* and dispersion *d* in [0, 1]."""

    if not text or not str(text).strip():
        return 0.25, 0.25
    words = str(text).split()
    n = len(words)
    if n < 2:
        lens = [len(text)]
    else:
        lens = [len(w) for w in words]
    mu = sum(lens) / len(lens)
    var = sum((x - mu) ** 2 for x in lens) / max(len(lens), 1)
    uniq = len(set(w.lower() for w in words))
    ttr = uniq / max(n, 1)
    c = float(max(0.0, min(1.0, 1.0 - ttr)))
    d = float(max(0.0, min(1.0, (var**0.5) / (mu + 0.5))))
    return c, d


def _repetition_tokens(text: str) -> list[str]:
    """Lowercase alphanumeric-only tokens (punctuation stripped) for repetition cues."""
    out: list[str] = []
    for w in str(text).split():
        t = "".join(ch for ch in w.lower() if ch.isalnum())
        if t:
            out.append(t)
    return out


def _type_jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity on token-type sets; empty/empty → 1.0 (perfect overlap)."""
    if not a and not b:
        return 1.0
    union = len(a | b)
    if union == 0:
        return 1.0
    return len(a & b) / union


def semantic_repetition_score(text: str) -> float:
    """Lexical proxy for repeated wording in [0, 1] (v2 multi-cue).

    Combines: mode token excess, adjacent bigram/trigram diversity loss, ordered
    re-hits of repeated n-grams, and mean max pairwise Jaccard overlap between
    coarse sentence segments. Stdlib-only; empty or fewer than two tokens → 0.0.
    """
    if not text or not str(text).strip():
        return 0.0
    tokens = _repetition_tokens(text)
    n = len(tokens)
    if n < 2:
        return 0.0

    parts: list[float] = []

    # Dominant token excess: share of tokens beyond the first instance of the mode.
    counts = Counter(tokens)
    max_c = max(counts.values())
    parts.append((max_c - 1) / max(n - 1, 1))

    # Adjacent bigrams: uniqueness deficit + fraction of positions that repeat an earlier bigram.
    bigs = [tuple(tokens[i : i + 2]) for i in range(n - 1)]
    nb = len(bigs)
    parts.append(1.0 - len(set(bigs)) / nb)
    seen_b: set[tuple[str, str]] = set()
    dup_b = 0
    for b in bigs:
        if b in seen_b:
            dup_b += 1
        else:
            seen_b.add(b)
    parts.append(dup_b / nb)

    # Trigrams (same two cues) when available.
    if n >= 3:
        tris = [tuple(tokens[i : i + 3]) for i in range(n - 2)]
        nt = len(tris)
        parts.append(1.0 - len(set(tris)) / nt)
        seen_t: set[tuple[str, str, str]] = set()
        dup_t = 0
        for t in tris:
            if t in seen_t:
                dup_t += 1
            else:
                seen_t.add(t)
        parts.append(dup_t / nt)

    # Cross-segment redundancy: split on sentence boundaries; Jaccard overlap of token sets.
    raw_segs = re.split(r"[.!?]+|\n+", text)
    seg_tokens = [_repetition_tokens(s) for s in raw_segs if s.strip()]
    seg_tokens = [s for s in seg_tokens if len(s) >= 2]
    if len(seg_tokens) >= 2:
        accum = 0.0
        for i, si in enumerate(seg_tokens):
            set_i = set(seg_tokens[i])
            best = 0.0
            for j, sj in enumerate(seg_tokens):
                if i == j:
                    continue
                set_j = set(sj)
                union = len(set_i | set_j)
                if union == 0:
                    continue
                inter = len(set_i & set_j)
                best = max(best, inter / union)
            accum += best
        parts.append(accum / len(seg_tokens))

    peak = max(parts)
    mean_p = sum(parts) / len(parts)
    # Weight max so a single strong repetition channel (e.g. mode excess) surfaces clearly.
    blended = 0.42 * peak + 0.58 * mean_p
    return float(max(0.0, min(1.0, blended)))


# v3 topic drift: segment-leading ordinals / numbering (procedural stabilizer cues).
_TOPIC_DRIFT_ORD_LEADS = frozenset(
    {
        "first",
        "second",
        "third",
        "fourth",
        "fifth",
        "next",
        "then",
        "finally",
        "lastly",
        "overall",
        "last",
        "summary",
        "step",
    }
)
# Types with len<=2 often glue sentences without topical continuity; ignore for same-thread glue.
_TOPIC_DRIFT_TINY_STOP = frozenset(
    {
        "a",
        "i",
        "we",
        "us",
        "to",
        "of",
        "is",
        "it",
        "in",
        "on",
        "at",
        "an",
        "as",
        "be",
        "do",
        "no",
        "so",
        "if",
        "or",
        "the",
        "and",
        "but",
        "are",
        "was",
        "for",
        "yes",
        "not",
        "yet",
        "all",
        "can",
        "had",
        "our",
        "may",
        "any",
    }
)


def _topic_drift_first_alnum_word(seg: str) -> str:
    for w in seg.strip().lower().split():
        t = "".join(ch for ch in w if ch.isalnum())
        if t:
            return t
    return ""


def _topic_drift_closing_scaffold_hit(seg: str) -> bool:
    """Closing / wrap-up lines without a leading ordinal (e.g. 'At the end of the pilot...')."""
    low = seg.strip().lower()
    if re.match(r"^at\s+the\s+(end|beginning|start|close|last)\b", low):
        return True
    if re.match(r"^(in|as)\s+(summary|conclusion|closing)\b", low):
        return True
    if re.match(r"^to\s+summarize\b", low):
        return True
    return False


def _topic_drift_enumeration_stability(seg_strings: list[str]) -> float:
    """Higher when many segments open with ordered / procedural / closing scaffolding."""
    if len(seg_strings) < 2:
        return 0.0
    hits = 0
    for s in seg_strings:
        fw = _topic_drift_first_alnum_word(s)
        if fw in _TOPIC_DRIFT_ORD_LEADS:
            hits += 1
            continue
        parts = s.strip().split()
        if parts and re.match(r"^\d+[.)]\s*$", parts[0]):
            hits += 1
            continue
        if _topic_drift_closing_scaffold_hit(s):
            hits += 1
    return min(1.0, hits / float(len(seg_strings)))


def _topic_drift_same_thread_stability(seg_tok: list[list[str]]) -> float:
    """Higher when many token types recur across multiple segments (same-thread glue)."""
    type_segs: dict[str, set[int]] = {}
    for i, seg in enumerate(seg_tok):
        for t in set(seg):
            if len(t) <= 2 and t in _TOPIC_DRIFT_TINY_STOP:
                continue
            type_segs.setdefault(t, set()).add(i)
    threaded = [t for t, segs in type_segs.items() if len(segs) >= 2]
    if not threaded:
        return 0.0
    return min(1.0, len(threaded) / max(len(type_segs), 1))


def _topic_drift_hedge_discourse_metric(tokens: list[str]) -> tuple[float, float]:
    """Returns (hedge_discourse_strength [0,1], concrete_anchor_ratio [0,1])."""
    n_tok = len(tokens)
    if n_tok == 0:
        return 0.0, 0.0
    hedge_w = sum(1 for t in tokens if t in _HEDGE_LEX) + 1.12 * sum(1 for t in tokens if t in _VAGUE_LEX)
    conc = sum(1 for t in tokens if t in _CONCRETE_OPS_LEX)
    # Strength scales with density; capped for blending.
    h = min(1.0, hedge_w / float(n_tok) * 4.25)
    c_r = conc / float(n_tok)
    return h, c_r


def topic_drift_score(text: str) -> float:
    """Lexical proxy for topic drift [0, 1] (v4: v3 gaps + hedge/carry + procedural/closing).

    Extends v3 with (1) carry dampening when hedge/vague discourse is dense and concrete
    anchors are sparse—reduces false drift on vague-but-on-topic prose; (2) closing-step
    scaffolding (e.g. 'At the end...') in the procedural stabilizer for ordered answers;
    (3) a narrow extra stabilizer when procedural coverage is very high on multi-step text.
    """
    if not text or not str(text).strip():
        return 0.0
    raw_segs = re.split(r"[.!?]+|\n+", text)
    seg_tok: list[list[str]] = []
    seg_strings: list[str] = []
    for s in raw_segs:
        st = s.strip()
        if not st:
            continue
        toks = _repetition_tokens(s)
        if toks:
            seg_strings.append(st)
            seg_tok.append(toks)
    n = len(seg_tok)
    if n < 2:
        return 0.0

    all_tokens = _repetition_tokens(text)
    hedge_r, conc_r = _topic_drift_hedge_discourse_metric(all_tokens)
    # Weaken carry-driven drift when text is vague-leaning; preserve true drift when concrete anchors abound (e.g. c-2).
    concrete_shield = max(0.0, min(1.0, 1.0 - 6.5 * conc_r))
    carry_damp = 1.0 - 0.46 * hedge_r * concrete_shield

    local_gaps: list[float] = []
    for i in range(n - 1):
        a, b = set(seg_tok[i]), set(seg_tok[i + 1])
        local_gaps.append(1.0 - _type_jaccard(a, b))
    mean_local = sum(local_gaps) / len(local_gaps)
    med_local = statistics.median(local_gaps)
    local_gap = 0.42 * med_local + 0.58 * mean_local

    opening_gaps: list[float] = []
    if n >= 3:
        anchor = set(seg_tok[0])
        for i in range(2, n):
            opening_gaps.append(1.0 - _type_jaccard(set(seg_tok[i]), anchor))
    opening_gap = sum(opening_gaps) / len(opening_gaps) if opening_gaps else 0.0

    carry_gaps: list[float] = []
    cumulative: set[str] = set(seg_tok[0])
    for i in range(1, n):
        types_i = set(seg_tok[i])
        if not types_i:
            carry_gaps.append(1.0)
            continue
        recall = len(types_i & cumulative) / len(types_i)
        carry_gaps.append(1.0 - recall)
        cumulative |= types_i
    mean_carry = sum(carry_gaps) / len(carry_gaps)
    mean_carry_adj = mean_carry * carry_damp

    # v3: lower raw weights than v2; renormalize (carry channel uses damped carry).
    w_sum = 0.24 + 0.19 + 0.22
    raw_lex = (0.24 * local_gap + 0.19 * opening_gap + 0.22 * mean_carry_adj) / w_sum

    dims = (local_gap, opening_gap, mean_carry_adj)
    highs = sum(1 for x in dims if x >= 0.48)
    lo, mid, hi = sorted(dims)
    spread = hi - lo

    if highs <= 1:
        if raw_lex > 0.62:
            raw_lex = 0.62 + (raw_lex - 0.62) * 0.36
        elif raw_lex > 0.52:
            raw_lex = 0.52 + (raw_lex - 0.52) * 0.68
        if spread > 0.52 and mid < 0.44:
            raw_lex *= 0.86

    proc = _topic_drift_enumeration_stability(seg_strings)
    rep = _topic_drift_same_thread_stability(seg_tok)
    discourse_stab = min(0.52, hedge_r * concrete_shield * 0.92)
    # Weight ``proc`` strongly so full ordinal + closing coverage (c-4) materially stabilizes.
    stab = min(0.86, 0.42 * proc + 0.36 * rep + 0.22 * discourse_stab)
    # Narrow: near-complete ordered steps + closing continuity (clean procedural controls).
    # Requires multi-segment answers with procedural hit rate >= 0.93 — skips chaotic drift (c-2).
    if n >= 4 and proc >= 0.93:
        stab = min(0.91, stab + 0.13)
    after_stab = raw_lex * (1.0 - stab)

    edges = n - 1
    scale = 0.27 + 0.73 * min(1.0, edges / 3.0)
    blended = after_stab * scale
    return float(max(0.0, min(1.0, blended)))


def specificity_vagueness_score(text: str) -> float:
    """Risk-style score: higher = vaguer / less actionable [0, 1].

    Up-weights hedging and vague nominals; down-weights numeric anchors and
    operational vocabulary. Stdlib-only.
    """
    if not text or not str(text).strip():
        return 0.0
    tokens = _repetition_tokens(text)
    n = len(tokens)
    if n == 0:
        return 0.0

    hedge_h = sum(1 for t in tokens if t in _HEDGE_LEX)
    vague_h = sum(1 for t in tokens if t in _VAGUE_LEX)
    # "sort"/"kind" often appear in bigrams "sort of" / "kind of" — count extra when following token is "of"
    of_h = sum(
        1
        for i in range(len(tokens) - 1)
        if tokens[i] in ("sort", "kind") and tokens[i + 1] == "of"
    )

    vague_lexical = min(
        1.0,
        (hedge_h + 1.35 * vague_h + 0.85 * of_h) / float(n) * 5.5,
    )

    num_groups = len(re.findall(r"\d+(?:\.\d+)?", text))
    pct_hits = len(re.findall(r"\d+\s*%", text))
    ops_h = sum(1 for t in tokens if t in _CONCRETE_OPS_LEX)
    concrete_raw = min(
        1.0,
        (num_groups * 1.15 + pct_hits * 0.9 + ops_h * 0.55) / max(float(n), 1.0) * 4.0,
    )

    # Blend: hedge channel scaled down when concrete anchors are strong.
    blended = vague_lexical * (1.0 - 0.72 * concrete_raw) + 0.08 * vague_lexical
    return float(max(0.0, min(1.0, blended)))


def structural_coherence_score(text: str) -> float:
    """Risk-style structural fragmentation: higher = choppier / less readable shape [0, 1].

    Penalizes uneven segment lengths, many tiny segments, and many sentence splits; lightly
    rewards explicit scaffolding tokens; small comma-vs-endings cue for run-on shape.
    """
    if not text or not str(text).strip():
        return 0.0
    raw_segs = re.split(r"[.!?]+|\n+", text)
    lens: list[int] = []
    for s in raw_segs:
        if not s.strip():
            continue
        toks = _repetition_tokens(s)
        if toks:
            lens.append(len(toks))
    m = len(lens)
    if m == 0:
        return 1.0
    if m < 2:
        return 0.06

    mean_l = sum(lens) / m
    var = sum((x - mean_l) ** 2 for x in lens) / m
    std = math.sqrt(var)
    cv = min(1.0, std / mean_l) if mean_l > 0 else 1.0

    tiny_frac = sum(1 for x in lens if x <= 2) / m
    multi_seg = min(1.0, (m - 1) / 7.0)

    whole = _repetition_tokens(text)
    n_tok = len(whole)
    mark_h = sum(1 for w in whole if w in _STRUCTURE_LEX)
    marker_bonus = min(0.22, (mark_h / max(n_tok, 1)) * 7.0)

    comma = text.count(",")
    ends = max(1, text.count(".") + text.count("!") + text.count("?"))
    runon = min(1.0, (comma + 1) / float(ends) / 4.5)

    raw_frag = 0.38 * cv + 0.30 * tiny_frac + 0.22 * multi_seg + 0.10 * runon
    score = raw_frag - marker_bonus
    return float(max(0.0, min(1.0, score)))


def _internal_consistency_v2_directive_templates(low: str) -> float:
    """High-precision contradiction templates in [0, 1]. Lexical only."""
    m = 0.0
    # Classic approve / reject polarity in one response
    if re.search(r"\brecommend\b", low) and re.search(r"\breject\b", low):
        m = max(m, 0.88)
    if re.search(r"\bsupport\b", low) and re.search(r"\boppose\b", low):
        m = max(m, 0.90)
    if re.search(r"\bproceed\b", low) and re.search(r"\brefuse\b", low):
        m = max(m, 0.86)
    # Negated modal + rollout verbs
    if re.search(
        r"\bshould\s+not\b.{0,56}\b(launch|ship|proceed|rollout)\b", low, re.DOTALL
    ) or re.search(r"\bdo\s+not\s+launch\b", low):
        m = max(m, 0.88)
    # Explicit "not launch" / hedged launch refusal
    if re.search(r"\bnot\s+launch\b", low) or re.search(r"\blaunch\s+yet\b", low):
        m = max(m, 0.78)
    # Immediate go vs wait/postpone (push-pull)
    if _IC_FORWARD_ACTION.search(low) and _IC_HOLD_OR_DELAY.search(low):
        m = max(m, 0.76)
    # proceed + postpone in one answer (classic split directive)
    if re.search(r"\bproceed\b", low) and re.search(r"\bpostpone\b", low):
        m = max(m, 0.82)
    # Dual recommendation: forward vs waiting
    if low.count("recommend") >= 2:
        if re.search(r"recommend.{0,140}wait", low, re.DOTALL) and (
            re.search(r"recommend.{0,140}(forward|now)", low, re.DOTALL)
            or "moving forward" in low
        ):
            m = max(m, 0.85)
    elif re.search(r"recommend.{0,120}wait", low, re.DOTALL) and (
        re.search(r"recommend.{0,120}(forward|now)", low, re.DOTALL) or "moving forward" in low
    ):
        m = max(m, 0.84)
    # should launch + should not (same theme, opposing modals)
    if (
        low.count("should") >= 2
        and "launch" in low
        and "not" in low
        and re.search(r"\bwe\s+should\s+launch\b", low)
        and re.search(r"\bwe\s+should\s+not\b", low)
    ):
        m = max(m, 0.80)
    return float(min(1.0, m))


def internal_consistency_score(text: str) -> float:
    """Risk-style internal conflict proxy: higher = more contradiction / tension [0, 1].

    v2: baseline stance/negation channels plus directive-conflict templates, stronger
    weight on negated recommendations, and contrast only when paired with opposing action
    cues. Lexical only; not logical inference.
    """
    if not text or not str(text).strip():
        return 0.0
    tokens = _repetition_tokens(text)
    n = len(tokens)
    if n == 0:
        return 0.0

    low = str(text).lower()
    pos_c = sum(1 for t in tokens if t in _STANCE_POS_LEX)
    neg_c = sum(1 for t in tokens if t in _STANCE_NEG_LEX)
    delay_opp = bool(_IC_HOLD_OR_DELAY.search(low))
    stance_tension = 0.0
    if pos_c >= 1 and neg_c >= 1:
        stance_tension = min(1.0, math.sqrt(float(pos_c * neg_c)) / float(n) * 7.5)
    elif pos_c >= 1 and delay_opp:
        # Forward stance language alongside delay / not-launch cues (v2).
        stance_tension = min(1.0, math.sqrt(float(pos_c * 2.0)) / float(n) * 8.2)

    cont = sum(1 for t in tokens if t in _CONTRAST_LEX)
    contrast_bare = min(1.0, cont / float(n) * 5.0)

    neg_d = sum(1 for t in tokens if t in ("not", "never", "without"))
    neg_sig = min(1.0, neg_d / float(n) * 5.5)

    legacy_clash = 0.0
    if re.search(r"recommend.{0,72}\b(not|never|no)\b", low, re.DOTALL) or re.search(
        r"\b(not|never)\b.{0,72}recommend", low, re.DOTALL
    ):
        legacy_clash = max(legacy_clash, 0.48)
    if re.search(r"proceed.{0,72}\b(not|never)\b", low, re.DOTALL) or re.search(
        r"\b(not|never).{0,72}proceed", low, re.DOTALL
    ):
        legacy_clash = max(legacy_clash, 0.48)
    if "should not" in low and re.search(r"\b(we|i)\s+should\b", low):
        legacy_clash = max(legacy_clash, 0.44)
    if low.count("yes") >= 1 and low.count("no") >= 2 and n <= 40:
        legacy_clash = max(legacy_clash, 0.18)

    neg_rec_pair = 0.0
    if re.search(
        r"\brecommend\b.{0,96}\b(wait|waiting|postpone|not\s+to|not\s+)", low, re.DOTALL
    ) and re.search(r"\brecommend\b.{0,96}\b(now|forward|immediate|launch|proceed)\b", low, re.DOTALL):
        neg_rec_pair = 0.92
    elif re.search(r"\brecommend\b.{0,96}\b(wait|waiting)\b", low, re.DOTALL) and (
        "moving forward" in low or re.search(r"\b(now|forward|immediate)\b", low)
    ):
        neg_rec_pair = 0.88

    template_peak = _internal_consistency_v2_directive_templates(low)
    # Unified conflict channel: templates and legacy hits on comparable [0, 1] scale.
    legacy_scaled = min(1.0, legacy_clash / 0.48)
    conflict_core = max(template_peak, legacy_scaled, neg_rec_pair)

    forward_hit = bool(_IC_FORWARD_ACTION.search(low))
    hold_hit = bool(_IC_HOLD_OR_DELAY.search(low))
    contrast_paired = 0.0
    if cont >= 1 and forward_hit and hold_hit:
        contrast_paired = min(1.0, 0.42 + 0.12 * float(min(cont, 4)))

    raw = (
        0.20 * stance_tension
        + 0.20 * contrast_bare
        + 0.08 * neg_sig
        + 0.40 * conflict_core
        + 0.12 * contrast_paired
    )
    return float(max(0.0, min(1.0, raw)))


def _ia_refusal_risk(low: str) -> float:
    """[0, 1] risk from refusal / evasion phrasing."""
    if not low.strip():
        return 0.85
    if _IA_REFUSAL_REGEX.search(low):
        return 0.88
    return 0.0


def _ia_exclusion_risk(resp_l: str, task_l: str, rubric: dict[str, Any]) -> float:
    """[0, 1] risk from forbidden phrases (rubric) or quoted 'do not mention \"X\"' in task."""
    phrases: list[str] = []
    fp = rubric.get("forbidden_phrases")
    if isinstance(fp, (list, tuple)):
        for p in fp:
            if isinstance(p, str) and p.strip():
                phrases.append(p.strip().lower())
    for m in _IA_TASK_EXCLUSION_QUOTED.finditer(task_l):
        inner = m.group(1).strip().lower()
        if inner:
            phrases.append(inner)
    if not phrases:
        return 0.0
    hits = sum(1 for p in phrases if p in resp_l)
    if hits == 0:
        return 0.0
    return float(min(1.0, 0.52 + 0.24 * float(hits - 1)))


def _ia_format_risk(response_raw: str, resp_l: str, rubric: dict[str, Any]) -> float:
    """[0, 1] risk from rubric-only format / length rules."""
    risks: list[float] = []
    words = resp_l.split()
    n_words = len(words)

    mw = rubric.get("max_words")
    if isinstance(mw, int) and mw > 0 and n_words > mw:
        excess = (n_words - mw) / float(mw)
        risks.append(min(1.0, 0.45 + 0.35 * min(1.0, excess)))

    mn = rubric.get("min_words")
    if isinstance(mn, int) and mn > 0 and n_words < mn:
        deficit = (mn - n_words) / float(mn)
        risks.append(min(1.0, 0.45 + 0.4 * min(1.0, deficit)))

    ef = rubric.get("expected_format")
    if isinstance(ef, str):
        ef_n = ef.strip().lower()
        lines = [ln for ln in response_raw.splitlines() if ln.strip()]
        n_lines = len(lines)
        if ef_n in ("bullets", "bullet", "bullet_list"):
            if n_words >= 10 and n_lines >= 1:
                bullet_lines = sum(
                    1 for ln in lines if re.match(r"^\s*[-*•]\s+\S", ln) is not None
                )
                if bullet_lines == 0:
                    risks.append(0.82 if n_lines >= 2 else 0.72)
        elif ef_n in ("numbered", "number", "ordered"):
            if n_words >= 10 and n_lines >= 1:
                num_lines = sum(
                    1 for ln in lines if re.match(r"^\s*\d+[\.)]\s+\S", ln) is not None
                )
                if n_lines >= 2 and num_lines < max(1, int(0.35 * n_lines)):
                    risks.append(0.78)
                elif num_lines == 0 and n_lines >= 2:
                    risks.append(0.74)
    if not risks:
        return 0.0
    return float(max(risks))


def instruction_alignment_score_and_mode(
    response_text: str,
    instruction_task_text: str | None = None,
    instruction_rubric: dict[str, Any] | None = None,
) -> tuple[float, str]:
    """v1 instruction alignment: refusal / exclusions / rubric format (full) or capped proxy (degraded).

    Returns ``(score, mode)`` with ``score`` in ``[0, 1]`` (↑ worse). ``mode`` is
    ``INSTRUCTION_ALIGNMENT_MODE_FULL`` or ``INSTRUCTION_ALIGNMENT_MODE_DEGRADED``.
    """
    if not isinstance(response_text, str):
        response_text = ""
    rubric: dict[str, Any] = instruction_rubric if isinstance(instruction_rubric, dict) else {}

    task = instruction_task_text
    if task is not None and not isinstance(task, str):
        task = None
    if task is not None and not task.strip():
        task = None

    low = str(response_text).lower().strip()

    if task is None or len(task.strip()) < _INSTRUCTION_ALIGNMENT_MIN_TASK_CHARS:
        r = _ia_refusal_risk(low)
        if len(low) < 16 and len(low.split()) < 5:
            r = max(r, 0.42)
        r = float(max(0.0, min(1.0, r)))
        r = min(_INSTRUCTION_ALIGNMENT_DEGRADED_CAP, r)
        return r, INSTRUCTION_ALIGNMENT_MODE_DEGRADED

    task_l = task.strip().lower()
    c_ref = _ia_refusal_risk(low)
    c_exc = _ia_exclusion_risk(low, task_l, rubric)
    c_fmt = _ia_format_risk(str(response_text), low, rubric)
    # OR-style combine so one strong channel is not diluted when others are zero (first pass).
    cr = min(1.0, max(0.0, c_ref))
    ce = min(1.0, max(0.0, c_exc))
    cf = min(1.0, max(0.0, c_fmt))
    raw = 1.0 - (1.0 - cr) * (1.0 - ce) * (1.0 - cf)
    return float(max(0.0, min(1.0, raw))), INSTRUCTION_ALIGNMENT_MODE_FULL


def _csi_count_substantive_list_items(response_raw: str) -> int:
    """Count lines that look like substantive bullets or numbered items (v1).

    Matches the same leading patterns as ``_ia_format_risk`` list detection; one line
    contributes at most one item.
    """
    lines = [ln for ln in str(response_raw).splitlines() if ln.strip()]
    n = 0
    for ln in lines:
        if re.match(r"^\s*[-*•]\s+\S", ln) is not None or re.match(r"^\s*\d+[\.)]\s+\S", ln) is not None:
            n += 1
    return n


def critical_slot_integrity_score_and_mode(
    response_text: str,
    instruction_task_text: str | None = None,
    instruction_rubric: dict[str, Any] | None = None,
) -> tuple[float, str]:
    """v1 critical slot integrity: rubric ``expected_item_count`` vs list items (full) or capped stub (degraded).

    Full mode when ``instruction_task_text`` is present and usable (same length gate as
    instruction alignment). In full mode, only ``instruction_rubric['expected_item_count']``
    (positive int) produces non-zero risk via deficit scaling. Degraded mode is capped and
    does not use task/rubric slot expectations (v1 stub score 0.0).
    """
    if not isinstance(response_text, str):
        response_text = ""
    rubric: dict[str, Any] = instruction_rubric if isinstance(instruction_rubric, dict) else {}

    task = instruction_task_text
    if task is not None and not isinstance(task, str):
        task = None
    if task is not None and not task.strip():
        task = None

    if task is None or len(str(task).strip()) < _INSTRUCTION_ALIGNMENT_MIN_TASK_CHARS:
        r = 0.0
        r = min(_CRITICAL_SLOT_INTEGRITY_DEGRADED_CAP, float(max(0.0, min(1.0, r))))
        return r, CRITICAL_SLOT_INTEGRITY_MODE_DEGRADED

    n_exp = rubric.get("expected_item_count")
    if not isinstance(n_exp, int) or n_exp <= 0:
        return 0.0, CRITICAL_SLOT_INTEGRITY_MODE_FULL

    actual = _csi_count_substantive_list_items(str(response_text))
    if actual >= n_exp:
        return 0.0, CRITICAL_SLOT_INTEGRITY_MODE_FULL

    deficit = (n_exp - actual) / float(n_exp)
    risk = min(1.0, 0.45 + 0.4 * min(1.0, deficit))
    return float(max(0.0, min(1.0, risk))), CRITICAL_SLOT_INTEGRITY_MODE_FULL


def _id_token_is_content(t: str) -> bool:
    if len(t) < 2:
        return False
    if t.isdigit():
        return False
    return t not in _ID_STOPWORDS


def information_density_score(text: str) -> float:
    """Lexical substance-density risk in [0, 1] (↑ worse). v1: ``response_text`` only.

    Blends type-token (uniqueness) shortfall, low content-word share, and low hapax-token
    share. Fewer than ``_INFORMATION_DENSITY_MIN_TOKENS`` alphanumeric tokens → ``0.0``.
    """
    if not text or not str(text).strip():
        return 0.0
    tokens = _repetition_tokens(str(text))
    n = len(tokens)
    if n < _INFORMATION_DENSITY_MIN_TOKENS:
        return 0.0

    ttr = len(set(tokens)) / float(n)
    deficit_ttr = max(0.0, _INFORMATION_DENSITY_TTR_TARGET - ttr)
    r_ttr = min(1.0, 0.45 + 0.50 * min(1.0, deficit_ttr / _INFORMATION_DENSITY_TTR_TARGET))

    c_count = sum(1 for t in tokens if _id_token_is_content(t))
    content_ratio = c_count / float(n)
    deficit_c = max(0.0, _INFORMATION_DENSITY_CONTENT_TARGET - content_ratio)
    r_content = min(
        1.0,
        0.45 + 0.55 * min(1.0, deficit_c / _INFORMATION_DENSITY_CONTENT_TARGET),
    )

    freq = Counter(tokens)
    hapax_n = sum(1 for t in tokens if freq[t] == 1)
    hapax_share = hapax_n / float(n)
    deficit_h = max(0.0, _INFORMATION_DENSITY_HAPAX_TARGET - hapax_share)
    r_hapax = min(
        1.0,
        0.45 + 0.55 * min(1.0, deficit_h / _INFORMATION_DENSITY_HAPAX_TARGET),
    )

    blended = (r_ttr + r_content + r_hapax) / 3.0
    return float(max(0.0, min(1.0, blended)))


# --- reasoning_progression_score v1 (Phase 2; response_text only; forward-movement / anti-stall) ---
_REASONING_PROGRESSION_MIN_TOKENS = 12
_REASONING_PROGRESSION_MIN_SEGMENTS = 2
_REASONING_PROGRESSION_CARRY_MIN_TYPES = 3
# Contrast / pivot cues without mandatory resolution.
_RP_CONTRAST_LEX = frozenset(
    {
        "but",
        "however",
        "although",
        "though",
        "yet",
        "whereas",
        "nevertheless",
        "nonetheless",
    }
)
# Forward / resolution cues (conservative; omit ambiguous tokens like ``so``).
_RP_FORWARD_LEX = frozenset(
    {
        "therefore",
        "thus",
        "hence",
        "consequently",
        "accordingly",
        "recommend",
        "recommends",
        "recommended",
        "recommendation",
        "conclude",
        "concludes",
        "conclusion",
        "summary",
    }
)


def _rp_bigram_jaccard(a: list[str], b: list[str]) -> float:
    """Jaccard on adjacent token bigram sets; fewer than two tokens in either → 0.0."""
    if len(a) < 2 or len(b) < 2:
        return 0.0
    ba = set(zip(a[:-1], a[1:]))
    bb = set(zip(b[:-1], b[1:]))
    union = len(ba | bb)
    if union == 0:
        return 0.0
    return len(ba & bb) / union


def reasoning_progression_score(text: str) -> float:
    """Risk-style stall / non-progression proxy in [0, 1] (↑ worse). v1: ``response_text`` only.

    Blends cross-segment near-duplication of reasoning-shaped text, contrast/hedge density
    without forward markers, and low new-type carry into later segments. Fewer than
    ``_REASONING_PROGRESSION_MIN_SEGMENTS`` substantive segments or fewer than
    ``_REASONING_PROGRESSION_MIN_TOKENS`` total alphanumeric tokens → ``0.0``.
    """
    if not text or not str(text).strip():
        return 0.0
    raw = str(text)
    all_tokens = _repetition_tokens(raw)
    n_tok = len(all_tokens)
    if n_tok < _REASONING_PROGRESSION_MIN_TOKENS:
        return 0.0

    raw_segs = re.split(r"[.!?]+|\n+", raw)
    seg_tok: list[list[str]] = []
    for s in raw_segs:
        toks = _repetition_tokens(s)
        if toks:
            seg_tok.append(toks)
    n_seg = len(seg_tok)
    if n_seg < _REASONING_PROGRESSION_MIN_SEGMENTS:
        return 0.0

    # (1) Cross-segment duplication: per segment i>0, max vs prior of max(unigram Jaccard, bigram Jaccard).
    dup_parts: list[float] = []
    for i in range(1, n_seg):
        si = seg_tok[i]
        set_i = set(si)
        best = 0.0
        for j in range(i):
            sj = seg_tok[j]
            set_j = set(sj)
            u = _type_jaccard(set_i, set_j)
            bj = _rp_bigram_jaccard(si, sj)
            best = max(best, u, bj)
        dup_parts.append(best)
    r_dup = sum(dup_parts) / len(dup_parts)

    # (2) Contrast density damped by forward-marker density.
    c_hit = sum(1 for t in all_tokens if t in _RP_CONTRAST_LEX)
    f_hit = sum(1 for t in all_tokens if t in _RP_FORWARD_LEX)
    contrast_d = min(1.0, (c_hit / float(n_tok)) * 7.0)
    forward_d = min(1.0, (f_hit / float(n_tok)) * 7.0)
    r_osc = contrast_d * (1.0 - 0.85 * forward_d)
    r_osc = float(max(0.0, min(1.0, r_osc)))

    # (3) Low new-type carry: later segments should introduce types not seen earlier.
    carry_parts: list[float] = []
    cumulative: set[str] = set(seg_tok[0])
    for i in range(1, n_seg):
        types_i = set(seg_tok[i])
        if len(types_i) < _REASONING_PROGRESSION_CARRY_MIN_TYPES:
            continue
        new_types = types_i - cumulative
        new_share = len(new_types) / float(len(types_i))
        carry_parts.append(1.0 - new_share)
        cumulative |= types_i
    if not carry_parts:
        r_carry = 0.0
    else:
        r_carry = sum(carry_parts) / len(carry_parts)

    blended = 0.35 * r_dup + 0.35 * r_osc + 0.30 * r_carry
    return float(max(0.0, min(1.0, blended)))


# --- constraint_stability_score v1 (Phase 2; response_text only; narrow % contradiction slice) ---
_CONSTRAINT_STABILITY_MIN_TOKENS = 12
_CONSTRAINT_STABILITY_MIN_SEGMENTS = 2
# Tight character window for pairs of percentage literals (stdlib-only first pass).
_CONSTRAINT_STABILITY_PCT_WINDOW_CHARS = 420
_CONSTRAINT_STABILITY_PCT_MIN_DELTA = 5.0
_CONSTRAINT_STABILITY_PCT_REGEX = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def constraint_stability_score(text: str) -> float:
    """Risk-style constraint wobble in [0, 1] (↑ worse). v1: ``response_text`` only.

    Gates on token/segment length, then a cue gate requiring at least two ``%`` literals.
    Scores only **tight-window** contradictory percentage pairs (|Δ| ≥ threshold).
    """
    if not text or not str(text).strip():
        return 0.0
    raw = str(text)
    all_tokens = _repetition_tokens(raw)
    if len(all_tokens) < _CONSTRAINT_STABILITY_MIN_TOKENS:
        return 0.0

    raw_segs = re.split(r"[.!?]+|\n+", raw)
    n_seg = sum(1 for s in raw_segs if _repetition_tokens(s))
    if n_seg < _CONSTRAINT_STABILITY_MIN_SEGMENTS:
        return 0.0

    pct_hits: list[tuple[float, int]] = []
    for m in _CONSTRAINT_STABILITY_PCT_REGEX.finditer(raw):
        pct_hits.append((float(m.group(1)), m.start()))
    if len(pct_hits) < 2:
        return 0.0

    pair_deltas: list[float] = []
    for i in range(len(pct_hits)):
        v1, p1 = pct_hits[i]
        for j in range(i + 1, len(pct_hits)):
            v2, p2 = pct_hits[j]
            if abs(p1 - p2) > _CONSTRAINT_STABILITY_PCT_WINDOW_CHARS:
                continue
            d = abs(v1 - v2)
            if d >= _CONSTRAINT_STABILITY_PCT_MIN_DELTA:
                pair_deltas.append(d)
    if not pair_deltas:
        return 0.0

    n_pairs = len(pair_deltas)
    peak = max(pair_deltas)
    raw_score = 0.66 + 0.10 * float(n_pairs - 1) + 0.004 * float(peak - _CONSTRAINT_STABILITY_PCT_MIN_DELTA)
    return float(max(0.0, min(1.0, raw_score)))


def _primary_weakness_from_scores(
    sem: float,
    tdr: float,
    spec_v: float,
    struct: float,
    inc: float,
) -> str:
    """Pick ``primary_weakness`` from risk scores using a labeling-only policy.

    ``topic_drift_score`` is softened and capped against the strongest non-drift signal for
    comparison only (stored ``topic_drift_score`` is unchanged). If the top adjusted score
    does not lead the runner-up by more than ``_PRIMARY_WEAKNESS_DOMINANCE_MARGIN``,
    returns ``PRIMARY_WEAKNESS_MULTI_FACTOR``.
    """
    sem_f = float(sem)
    tdr_f = float(tdr)
    spec_f = float(spec_v)
    struct_f = float(struct)
    inc_f = float(inc)

    max_other = max(sem_f, spec_f, struct_f, inc_f)
    tdr_adj = min(
        tdr_f * _PRIMARY_WEAKNESS_TOPIC_LABEL_SOFTEN,
        max_other + _PRIMARY_WEAKNESS_TOPIC_LABEL_MAX_OTHER_PAD,
    )

    adjusted: list[tuple[str, float]] = [
        (PRIMARY_WEAKNESS_SEMANTIC, sem_f),
        (PRIMARY_WEAKNESS_TOPIC, tdr_adj),
        (PRIMARY_WEAKNESS_SPECIFICITY, spec_f),
        (PRIMARY_WEAKNESS_STRUCTURAL, struct_f),
        (PRIMARY_WEAKNESS_INTERNAL, inc_f),
    ]
    adjusted.sort(key=lambda kv: (-kv[1], kv[0]))
    top_score = adjusted[0][1]
    second_score = adjusted[1][1]
    if top_score - second_score <= _PRIMARY_WEAKNESS_DOMINANCE_MARGIN:
        return PRIMARY_WEAKNESS_MULTI_FACTOR
    return adjusted[0][0]


def compute_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """For each normalized record, add ``c``, ``d``, and ``S`` (row-level audit fields).

    Each input row must include ``response_text`` (other keys are preserved).
    """
    out: list[dict[str, Any]] = []
    for rec in records:
        text = rec["response_text"]
        if not isinstance(text, str):
            raise TypeError("record missing str response_text (should be caught at ingestion).")
        c, d = text_concentration_dispersion(text)
        s = balance_S(c, d)
        row = dict(rec)
        row["c"] = c
        row["d"] = d
        row["S"] = s
        sem = semantic_repetition_score(text)
        tdr = topic_drift_score(text)
        spec_v = specificity_vagueness_score(text)
        struct = structural_coherence_score(text)
        inc = internal_consistency_score(text)
        row["semantic_repetition_score"] = sem
        row["topic_drift_score"] = tdr
        row["specificity_vagueness_score"] = spec_v
        row["structural_coherence_score"] = struct
        row["internal_consistency_score"] = inc
        task_raw = rec.get("instruction_task_text")
        rubric_raw = rec.get("instruction_rubric")
        ia_score, ia_mode = instruction_alignment_score_and_mode(text, task_raw, rubric_raw)
        row["instruction_alignment_score"] = ia_score
        row["instruction_alignment_mode"] = ia_mode
        csi_score, csi_mode = critical_slot_integrity_score_and_mode(text, task_raw, rubric_raw)
        row["critical_slot_integrity_score"] = csi_score
        row["critical_slot_integrity_mode"] = csi_mode
        row["information_density_score"] = information_density_score(text)
        row["reasoning_progression_score"] = reasoning_progression_score(text)
        row["constraint_stability_score"] = constraint_stability_score(text)
        row["combined_row_risk"] = (
            float(sem) + float(tdr) + float(spec_v) + float(struct) + float(inc)
        ) / 5.0
        row["primary_weakness"] = _primary_weakness_from_scores(sem, tdr, spec_v, struct, inc)
        out.append(row)
    return out


def pool_pooled_S(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Arithmetic mean of ``S`` over *rows* (v1 default pooling per computation spec).

    When ``rows`` is empty, returns ``{"pooled_S": nan, "n": 0}`` with ``nan`` represented as
    ``float("nan")``.
    """
    if not rows:
        return {"pooled_S": float("nan"), "n": 0}
    total = 0.0
    for r in rows:
        total += float(r["S"])
    n = len(rows)
    return {"pooled_S": total / n, "n": n}
