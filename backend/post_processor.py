"""
post_processor.py — Local French Text Post-Processor
=====================================================
Applies multiple transformation layers to humanize French text
AFTER the Gemini API pass, reducing AI-detection and plagiarism scores
without any external API calls.

Transformations applied (in order):
  1. AI Cliché Killer          – 80+ cliché → natural replacements
  2. Contraction & Informal    – on a, ça, informal forms
  3. Sentence Rhythm Injector  – burstiness / variance of lengths
  4. Punctuation Naturalizer   – semicolons, em-dashes, ellipsis
  5. N-gram Breaker            – rephrase repeated 4+ word sequences
  6. Safety Preservation       – quotes, numbers, proper nouns, tech terms
"""

from __future__ import annotations

import logging
import random
import re
import statistics
from typing import Optional

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ---------------------------------------------------------------------------
# 1. AI CLICHÉ DICTIONARY  (80+ entries)
#    Each key maps to a *list* of possible replacements; one is picked
#    at random.  An empty list means "delete the phrase entirely".
# ---------------------------------------------------------------------------
AI_CLICHE_MAP: dict[str, list[str]] = {
    # ── Formal connectors (10) ────────────────────────────────────────
    "En conclusion":        ["Pour résumer", "Au final", "En fin de compte"],
    "Pour conclure":        ["En somme", "Au bout du compte", "Finalement"],
    "En résumé":            ["Pour faire court", "En bref", "Globalement"],
    "En somme":             ["Tout compte fait", "Au final", "Bref"],
    "En définitive":        ["Au fond", "Tout bien considéré", "En réalité"],
    "Par conséquent":       ["Du coup", "Résultat", "Ce qui fait que"],
    "Ainsi":                ["Comme ça", "De cette façon", "C'est pourquoi"],
    "De ce fait":           ["Résultat", "Du coup", "C'est pour ça que"],
    "Il s'ensuit que":      ["Ce qui veut dire que", "Du coup", "Résultat"],
    "En outre":             ["D'ailleurs", "Aussi", "Et puis"],

    # ── Academic / formal phrases (10) ─────────────────────────────────
    "Il convient de noter":       ["On remarque que", "Notons que", "Fait intéressant"],
    "Il convient de souligner":   ["Soulignons que", "Notons bien que", "Point important"],
    "Il est intéressant de noter": ["On note que", "Fait notable", "Ce qui frappe"],
    "Il est à noter que":         ["Notons que", "Remarquons que", "On voit que"],
    "Il est essentiel de":        ["On doit", "C'est crucial de", "Il faut"],
    "Il est fondamental de":      ["On ne peut pas ignorer", "C'est la base", "C'est essentiel de"],
    "Il convient de mentionner":  ["Mentionnons que", "Précisons que", "Ajoutons que"],
    "Il est pertinent de":        ["On gagne à", "C'est utile de", "Ça vaut le coup de"],
    "Il apparaît que":            ["On voit que", "Visiblement", "De toute évidence"],
    "Force est de constater que": ["On constate que", "Les faits montrent que", "C'est clair que"],

    # ── Passive constructions (8) ──────────────────────────────────────
    "Il a été démontré que":          ["Les résultats montrent que", "On constate que", "Les études confirment que"],
    "Il a été observé que":           ["On observe que", "Les données montrent que", "On remarque que"],
    "Il a été prouvé que":            ["Les preuves indiquent que", "On sait maintenant que", "Les faits confirment que"],
    "Il a été établi que":            ["On sait que", "C'est un fait que", "Les recherches confirment que"],
    "Il est généralement admis que":  ["On admet souvent que", "La plupart reconnaissent que", "C'est communément accepté que"],
    "Il est largement reconnu que":   ["Beaucoup s'accordent à dire que", "On reconnaît que", "C'est bien connu que"],
    "Il peut être argumenté que":     ["On pourrait dire que", "Certains avancent que", "L'idée c'est que"],
    "Il est communément admis que":   ["On admet que", "Tout le monde sait que", "C'est connu"],

    # ── Overused transitions (13) ──────────────────────────────────────
    "De plus":                  ["Autre point", "Ajoutons que", "Sans oublier que", "D'autre part"],
    "Par ailleurs":             ["D'un autre côté", "Autre chose", "Aussi"],
    "Néanmoins":                ["Mais", "Cela dit", "Pourtant", "Cependant"],
    "Toutefois":                ["Mais", "En revanche", "Quand même"],
    "Cependant":                ["Mais", "Par contre", "Pourtant", "Malgré tout"],
    "En revanche":              ["Par contre", "À l'inverse", "D'un autre côté"],
    "D'une part":               ["D'abord", "Premièrement", "Pour commencer"],
    "D'autre part":             ["Ensuite", "Par ailleurs", "Et puis"],
    "Qui plus est":             ["En plus de ça", "Sans compter que", "Ajoutons que"],
    "En effet":                 ["Effectivement", "C'est vrai que", "D'ailleurs"],
    "Tout d'abord":             ["D'abord", "Pour commencer", "En premier lieu"],
    "Dans un premier temps":    ["D'abord", "Au départ", "Pour commencer"],
    "Dans un second temps":     ["Ensuite", "Après ça", "Puis"],

    # ── AI filler phrases — removed or minimized (13) ─────────────────
    "il est important de souligner":        [],
    "il est crucial de noter":              [],
    "il est important de mentionner":       [],
    "il est essentiel de mentionner":       [],
    "il est primordial de":                 ["il faut"],
    "il convient de préciser que":          ["précisons que"],
    "il est nécessaire de rappeler que":    ["rappelons que"],
    "il est important de rappeler que":     ["rappelons que"],
    "il importe de souligner que":          [],
    "il faut souligner que":               ["notons que"],
    "il faut noter que":                    ["à noter que"],
    "il va sans dire que":                  ["évidemment", "bien sûr"],
    "on ne saurait trop insister sur":      ["insistons sur"],

    # ── Wordy / stilted expressions (14) ───────────────────────────────
    "dans le but de":           ["pour", "afin de"],
    "dans le cadre de":         ["lors de", "pendant", "pour"],
    "au niveau de":             ["pour", "concernant", "côté"],
    "en ce qui concerne":       ["pour", "concernant", "côté", "sur le plan de"],
    "eu égard à":               ["vu", "compte tenu de", "étant donné"],
    "à cet égard":              ["sur ce point", "là-dessus", "à ce sujet"],
    "en matière de":            ["pour", "question", "côté"],
    "au sein de":               ["dans", "parmi", "à l'intérieur de"],
    "vis-à-vis de":             ["face à", "par rapport à", "envers"],
    "à l'heure actuelle":       ["aujourd'hui", "actuellement", "en ce moment"],
    "au jour d'aujourd'hui":    ["aujourd'hui", "actuellement", "maintenant"],
    "dans la mesure où":        ["puisque", "vu que", "étant donné que"],
    "il est clair que":         ["clairement", "sans aucun doute", "c'est évident que"],
    "sans aucun doute":         ["clairement", "à coup sûr", "manifestement"],

    # ── Emphatic / superlative hedges (9) ──────────────────────────────
    "extrêmement important":    ["crucial", "capital", "majeur"],
    "absolument essentiel":     ["indispensable", "incontournable", "vital"],
    "tout à fait":              ["complètement", "vraiment", "parfaitement"],
    "véritablement":            ["vraiment", "réellement", "sincèrement"],
    "indéniablement":           ["sans conteste", "clairement", "c'est sûr"],
    "incontestablement":        ["sans discussion", "clairement", "c'est certain"],
    "considérablement":         ["beaucoup", "nettement", "sensiblement"],
    "significativement":        ["nettement", "de manière notable", "beaucoup"],
    "fondamentalement":         ["au fond", "en réalité", "à la base"],

    # ── Miscellaneous AI patterns (12) ─────────────────────────────────
    "joue un rôle crucial":                 ["est déterminant", "pèse lourd", "compte beaucoup"],
    "joue un rôle important":               ["compte beaucoup", "a du poids", "est clé"],
    "joue un rôle essentiel":               ["est indispensable", "est central", "est au cœur de"],
    "revêt une importance particulière":    ["est particulièrement important", "mérite attention", "pèse lourd"],
    "mérite d'être souligné":               ["vaut la peine d'être noté", "est remarquable", "attire l'attention"],
    "il est impératif de":                  ["on doit", "il faut absolument", "c'est vital de"],
    "constitue un élément clé":             ["est un point central", "est au cœur de", "est fondamental"],
    "représente un défi majeur":            ["pose un vrai problème", "est un gros défi", "reste difficile"],
    "offre de nombreuses possibilités":     ["ouvre pas mal de portes", "permet beaucoup de choses", "donne plein d'options"],
    "permet de mettre en lumière":          ["éclaire", "montre bien", "met en évidence"],
    "contribue de manière significative":   ["aide beaucoup", "apporte énormément", "fait avancer"],
    "dans ce contexte":                     ["ici", "dans cette situation", "face à ça"],
}

# Total entries check (logged at import time)
_TOTAL_CLICHES = len(AI_CLICHE_MAP)
logger.debug("AI cliché dictionary loaded: %d entries", _TOTAL_CLICHES)

# Sorted by descending length so longer phrases match first
_SORTED_CLICHES: list[tuple[str, list[str]]] = sorted(
    AI_CLICHE_MAP.items(), key=lambda x: len(x[0]), reverse=True
)

# Pre-compile regex patterns with word boundaries for cliché matching
_CLICHE_PATTERNS: list[tuple[re.Pattern, list[str], str]] = []
for _phrase, _replacements in _SORTED_CLICHES:
    # Use case-insensitive match; no word-boundary on multi-word phrases
    # (they naturally delimit themselves)
    _pat = re.compile(re.escape(_phrase), re.IGNORECASE)
    _CLICHE_PATTERNS.append((_pat, _replacements, _phrase))


# ---------------------------------------------------------------------------
# Safety: regex helpers to identify protected spans
# ---------------------------------------------------------------------------
# Quoted strings:  «…», "…", '…', "…"
_QUOTE_RE = re.compile(
    r'«[^»]*»'                  # French guillemets
    r'|"[^"]*"'                  # Curly double
    r"|'[^']*'"                  # Curly single
    r'|"[^"]*"',                 # Straight double
    re.DOTALL,
)
_TECH_TERM_RE  = re.compile(r'\b[A-Za-z]+[./][A-Za-z]+\b')   # node.js, FastAPI
_MIXED_CASE_RE = re.compile(r'\b[a-z]+[A-Z][A-Za-z]*\b')     # camelCase
_ACRONYM_RE    = re.compile(r'\b[A-Z]{2,}\b')                 # NATO, API, IA
_NUMBER_DATE_RE = re.compile(r'\b\d[\d/.\-:,]*\b')            # 2024, 12/03, 3.14


def _build_protection_mask(text: str) -> list[bool]:
    """Return a boolean mask; True = character must not be changed."""
    mask = [False] * len(text)
    for pattern in (_QUOTE_RE, _TECH_TERM_RE, _MIXED_CASE_RE,
                    _ACRONYM_RE, _NUMBER_DATE_RE):
        for m in pattern.finditer(text):
            for i in range(m.start(), m.end()):
                mask[i] = True
    return mask


def _is_span_safe(mask: list[bool], start: int, end: int) -> bool:
    """True when no character in [start, end) is protected."""
    if start < 0 or end > len(mask):
        return True  # out-of-bounds → treat as safe (mask might be stale)
    return not any(mask[start:end])


# ---------------------------------------------------------------------------
# Sentence splitting helper
# ---------------------------------------------------------------------------
_SENT_SPLIT_RE = re.compile(r'(?<=[.!?…])\s+')


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences (delimiter stays attached to its sentence)."""
    parts = _SENT_SPLIT_RE.split(text.strip())
    return [p for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# Core class
# ---------------------------------------------------------------------------
class FrenchPostProcessor:
    """
    Multi-layer local French text post-processor.

    Usage::

        processor = FrenchPostProcessor()
        clean_text = processor.process(raw_text)
    """

    def __init__(
        self,
        burstiness_target_cv: float = 0.40,
        informal_chance: float = 0.30,
        seed: Optional[int] = None,
    ):
        self.burstiness_target_cv = burstiness_target_cv
        self.informal_chance = informal_chance
        if seed is not None:
            random.seed(seed)
        logger.info(
            "FrenchPostProcessor initialised  (cv_target=%.2f, informal=%.0f%%, "
            "clichés=%d)",
            burstiness_target_cv,
            informal_chance * 100,
            _TOTAL_CLICHES,
        )

    # ── public entry point ────────────────────────────────────────────
    def process(self, text: str) -> str:
        """Run all transformation layers and return the processed text."""
        if not text or not text.strip():
            return text

        original_len = len(text)
        logger.info("▶ post-processing start (%d chars)", original_len)

        text = self._apply_cliche_killer(text)
        text = self._apply_contractions(text)
        text = self._apply_rhythm_injector(text)
        text = self._apply_punctuation_naturalizer(text)
        text = self._apply_ngram_breaker(text)

        logger.info(
            "✔ post-processing done (%d → %d chars, Δ%+d)",
            original_len, len(text), len(text) - original_len,
        )
        return text

    # ------------------------------------------------------------------
    # 1. AI Cliché Killer
    # ------------------------------------------------------------------
    def _apply_cliche_killer(self, text: str) -> str:
        replacements_made = 0

        for pattern, alternatives, _orig in _CLICHE_PATTERNS:
            # We rebuild the mask fresh for every pattern because earlier
            # replacements may have shifted positions.
            mask = _build_protection_mask(text)
            new_parts: list[str] = []
            last_end = 0
            matched_any = False

            for m in pattern.finditer(text):
                if not _is_span_safe(mask, m.start(), m.end()):
                    continue

                new_parts.append(text[last_end:m.start()])

                if alternatives:
                    rep = random.choice(alternatives)
                    # Preserve first-letter case
                    if m.group(0)[0].isupper() and rep[0].islower():
                        rep = rep[0].upper() + rep[1:]
                    elif m.group(0)[0].islower() and rep[0].isupper():
                        rep = rep[0].lower() + rep[1:]
                    new_parts.append(rep)
                else:
                    # Delete the phrase; also eat a trailing ", " if present
                    after = text[m.end(): m.end() + 2]
                    if after.startswith(", "):
                        last_end = m.end() + 2
                        replacements_made += 1
                        matched_any = True
                        continue

                replacements_made += 1
                matched_any = True
                last_end = m.end()

            if matched_any:
                new_parts.append(text[last_end:])
                text = "".join(new_parts)

        logger.info("  cliché killer: %d replacements", replacements_made)
        return text

    # ------------------------------------------------------------------
    # 2. Contraction & Informal Injection
    # ------------------------------------------------------------------
    def _apply_contractions(self, text: str) -> str:
        changes = 0

        rules: list[tuple[re.Pattern, str | list[str], float]] = [
            (re.compile(r'\b[Nn]ous avons\b'),   "on a",   self.informal_chance),
            (re.compile(r'\b[Nn]ous sommes\b'),   "on est", self.informal_chance),
            (re.compile(r'\b[Nn]ous pouvons\b'),  "on peut", self.informal_chance),
            (re.compile(r'\b[Nn]ous devons\b'),   "on doit", self.informal_chance),
            (re.compile(r'\b[Nn]ous allons\b'),   "on va",  self.informal_chance),
            (re.compile(r'\b[Cc]ela\b'),          "ça",     self.informal_chance * 0.7),
            (re.compile(r'\bil ne faut pas\b', re.IGNORECASE),
             "il faut éviter de", 0.40),
            (re.compile(r'\bil faut éviter de\b', re.IGNORECASE),
             "il ne faut pas", 0.20),
            (re.compile(r"\b[Ll]'on\b"),          "on",     self.informal_chance),
        ]

        for pat, replacement, prob in rules:
            mask = _build_protection_mask(text)
            parts: list[str] = []
            last_end = 0
            touched = False

            for m in pat.finditer(text):
                if not _is_span_safe(mask, m.start(), m.end()):
                    continue
                if random.random() > prob:
                    continue

                parts.append(text[last_end:m.start()])
                rep = random.choice(replacement) if isinstance(replacement, list) else replacement

                # Keep capitalisation
                if m.group(0)[0].isupper() and rep[0].islower():
                    rep = rep[0].upper() + rep[1:]

                parts.append(rep)
                last_end = m.end()
                changes += 1
                touched = True

            if touched:
                parts.append(text[last_end:])
                text = "".join(parts)

        logger.info("  contractions / informal: %d changes", changes)
        return text

    # ------------------------------------------------------------------
    # 3. Sentence Rhythm Injector (burstiness)
    # ------------------------------------------------------------------
    def _apply_rhythm_injector(self, text: str) -> str:
        paragraphs = text.split("\n")
        new_paragraphs: list[str] = []
        mods = 0

        for para in paragraphs:
            stripped = para.strip()
            if not stripped:
                new_paragraphs.append(para)
                continue

            sentences = _split_sentences(stripped)
            if len(sentences) < 3:
                new_paragraphs.append(para)
                continue

            lengths = [len(s.split()) for s in sentences]
            mean_l = statistics.mean(lengths)
            if mean_l == 0:
                new_paragraphs.append(para)
                continue

            cv = statistics.pstdev(lengths) / mean_l

            if cv < self.burstiness_target_cv:
                sentences, n_changed = self._adjust_burstiness(sentences)
                mods += n_changed

            new_paragraphs.append(" ".join(sentences))

        logger.info("  rhythm injector: %d modifications", mods)
        return "\n".join(new_paragraphs)

    def _adjust_burstiness(
        self, sentences: list[str]
    ) -> tuple[list[str], int]:
        """Tweak sentence lengths to raise variance."""
        changed = 0
        result = list(sentences)

        # A) Split a long sentence at a conjunction
        conj_re = re.compile(
            r'\s+(mais|et|car|or|donc|puis|ensuite|cependant|toutefois|pourtant)\s+',
            re.IGNORECASE,
        )
        for i, s in enumerate(result):
            if len(s.split()) >= 16:
                m = conj_re.search(s)
                if m:
                    left = s[:m.start()].rstrip()
                    conj = m.group(1).strip()
                    right = s[m.end():].lstrip()
                    if not left.endswith(('.', '!', '?')):
                        left += '.'
                    right = conj[0].upper() + conj[1:] + ' ' + right
                    result[i] = left
                    result.insert(i + 1, right)
                    changed += 1
                    break

        # B) Merge two short adjacent sentences
        for i in range(len(result) - 1):
            if len(result[i].split()) <= 6 and len(result[i + 1].split()) <= 6:
                sep = random.choice([" ; ", " — "])
                first = result[i].rstrip()
                if first.endswith('.'):
                    first = first[:-1]
                second = result[i + 1].lstrip()
                if second and second[0].isupper():
                    second = second[0].lower() + second[1:]
                result[i] = first + sep + second
                result.pop(i + 1)
                changed += 1
                break

        return result, changed

    # ------------------------------------------------------------------
    # 4. Punctuation Naturalizer
    # ------------------------------------------------------------------
    def _apply_punctuation_naturalizer(self, text: str) -> str:
        paragraphs = text.split("\n")
        new_paragraphs: list[str] = []
        changes = 0

        for para in paragraphs:
            stripped = para.strip()
            if not stripped:
                new_paragraphs.append(para)
                continue

            sentences = _split_sentences(stripped)
            out: list[str] = []

            for idx, sent in enumerate(sentences):
                # a) Semicolon between consecutive sentences (~12%)
                if (
                    idx > 0
                    and random.random() < 0.12
                    and out
                    and out[-1].endswith('.')
                ):
                    out[-1] = out[-1][:-1] + ' ;'
                    if sent and sent[0].isupper():
                        sent = sent[0].lower() + sent[1:]
                    changes += 1

                # b) Em-dash around a short parenthetical clause (~15%)
                paren_re = re.compile(r',\s*([^,]{8,40}),')
                m = paren_re.search(sent)
                if m and random.random() < 0.15:
                    inner = m.group(1)
                    sent = (
                        sent[:m.start()]
                        + ' \u2014 ' + inner + ' \u2014 '
                        + sent[m.end():]
                    )
                    changes += 1

                out.append(sent)

            new_paragraphs.append(" ".join(out))

        logger.info("  punctuation naturalizer: %d changes", changes)
        return "\n".join(new_paragraphs)

    # ------------------------------------------------------------------
    # 5. N-gram Breaker
    # ------------------------------------------------------------------
    def _apply_ngram_breaker(self, text: str) -> str:
        mask = _build_protection_mask(text)
        words = text.split()
        n = 4
        changes = 0

        if len(words) < n * 2:
            return text

        # Build n-gram → positions index
        ngram_pos: dict[tuple[str, ...], list[int]] = {}
        for i in range(len(words) - n + 1):
            gram = tuple(w.lower().strip(".,;:!?") for w in words[i:i + n])
            ngram_pos.setdefault(gram, []).append(i)

        modified: set[int] = set()

        for gram, positions in ngram_pos.items():
            if len(positions) < 2:
                continue

            for pos in positions[1:]:
                if pos in modified:
                    continue

                # Safety check on the character-level span
                span_text = " ".join(words[pos:pos + n])
                prefix = " ".join(words[:pos])
                c_start = (len(prefix) + 1) if prefix else 0
                c_end = c_start + len(span_text)
                if c_end <= len(mask) and not _is_span_safe(mask, c_start, c_end):
                    continue

                strat = random.choice(["swap", "adverb", "synonym"])

                if strat == "swap" and pos + 2 < len(words):
                    words[pos + 1], words[pos + 2] = words[pos + 2], words[pos + 1]
                    modified.update(range(pos, pos + n))
                    changes += 1

                elif strat == "adverb":
                    adv = random.choice([
                        "notamment", "surtout", "particulièrement",
                        "vraiment", "justement", "précisément",
                        "effectivement",
                    ])
                    ins = pos + random.randint(1, min(2, n - 1))
                    words.insert(ins, adv)
                    modified.update(range(pos, pos + n + 1))
                    changes += 1
                    break  # positions shifted; stop this pass

                elif strat == "synonym":
                    fillers = {"très", "aussi", "donc", "bien", "plus"}
                    for j in range(pos, min(pos + n, len(words))):
                        w = words[j].lower().strip(".,;:!?")
                        if w in fillers:
                            words[j] = random.choice([
                                "assez", "plutôt", "relativement", "fort",
                            ])
                            modified.update(range(pos, pos + n))
                            changes += 1
                            break

        logger.info("  n-gram breaker: %d changes", changes)
        return " ".join(words)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------
    @staticmethod
    def get_stats(text: str) -> dict:
        """Basic text statistics useful for debugging / verification."""
        sentences = _SENT_SPLIT_RE.split(text.strip())
        lengths = [len(s.split()) for s in sentences if s.strip()]
        mean_l = statistics.mean(lengths) if lengths else 0
        std_l  = statistics.pstdev(lengths) if lengths else 0
        cv     = std_l / mean_l if mean_l else 0
        return {
            "char_count":            len(text),
            "word_count":            len(text.split()),
            "sentence_count":        len(lengths),
            "mean_sentence_length":  round(mean_l, 1),
            "sentence_length_cv":    round(cv, 3),
            "cliche_dict_size":      _TOTAL_CLICHES,
        }


# ======================================================================
# __main__ demo
# ======================================================================
if __name__ == "__main__":
    sample = (
        "En conclusion, il est important de souligner que l'intelligence artificielle "
        "joue un rôle crucial dans le développement technologique. Il a été démontré que "
        "les modèles de langage peuvent produire du texte de haute qualité. De plus, nous avons "
        "constaté que cela représente un défi majeur pour la détection de plagiat.\n\n"
        "Il convient de noter que les avancées dans le domaine sont considérablement rapides. "
        "Néanmoins, il est essentiel de mentionner que la qualité varie. Par conséquent, "
        "il est fondamental de mettre en place des mécanismes de contrôle. "
        "Dans le cadre de cette recherche, nous avons analysé les résultats. "
        "Dans le cadre de cette recherche, nous avons aussi examiné les implications.\n\n"
        "En définitive, il est impératif de continuer à explorer ces questions. "
        "Force est de constater que les progrès sont indéniablement significatifs. "
        "Il apparaît que nous sommes à un tournant. Toutefois, il est pertinent de "
        "rester prudent face aux promesses de l'IA. Au jour d'aujourd'hui, "
        "il est clair que l'avenir est prometteur."
    )

    print("=" * 72)
    print("ORIGINAL TEXT")
    print("=" * 72)
    print(sample)

    processor = FrenchPostProcessor(seed=42)

    stats_before = processor.get_stats(sample)
    print("\n── Stats BEFORE ──")
    for k, v in stats_before.items():
        print(f"  {k}: {v}")

    result = processor.process(sample)

    print("\n" + "=" * 72)
    print("PROCESSED TEXT")
    print("=" * 72)
    print(result)

    stats_after = processor.get_stats(result)
    print("\n── Stats AFTER ──")
    for k, v in stats_after.items():
        print(f"  {k}: {v}")

    # Quick sanity diff
    print("\n── Differences ──")
    if sample == result:
        print("  ⚠ No changes (unexpected)")
    else:
        orig_words = set(sample.lower().split())
        new_words  = set(result.lower().split())
        removed = orig_words - new_words
        added   = new_words - orig_words
        if removed:
            print(f"  Removed words: {', '.join(sorted(removed)[:20])}")
        if added:
            print(f"  Added words:   {', '.join(sorted(added)[:20])}")
