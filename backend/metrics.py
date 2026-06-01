"""
Linguistic metrics calculation module for comparing document statistics.
Designed specifically for French text analysis to provide insights on readability,
AI generation probability, vocabulary richness, plagiarism risk, and basic statistics.

Scoring methodology:
    The AI probability score (0-100) is a weighted composite of eight signals:
        1. Burstiness / Sentence-length CV  (25%)
        2. Transition-word density           (20%)
        3. Passive-voice ratio               (15%)
        4. Vocabulary diversity (MATTR)      (15%)
        5. N-gram repetition density         (10%)
        6. Word-length variance              ( 5%)
        7. Question frequency                ( 5%)
        8. First-person usage                ( 5%)
"""

import math
import re
from collections import Counter
from typing import Any, Dict, List, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Comprehensive list of French AI transition words and formulaic phrases (60+).
# High density of these markers correlates strongly with AI-generated text.
AI_TRANSITION_WORDS: List[str] = [
    # Logical connectors
    "de surcroît", "en conclusion", "en effet", "il convient de noter",
    "tout d'abord", "en outre", "par ailleurs", "néanmoins", "en somme",
    "en résumé", "ainsi", "en définitive", "somme toute", "d'une part",
    "d'autre part", "de plus", "qui plus est", "par conséquent",
    "c'est pourquoi", "de ce fait", "en revanche", "toutefois",
    "cependant", "malgré tout", "en dépit de", "quoi qu'il en soit",
    "il est important de", "il est essentiel de", "il est à noter que",
    "il convient de souligner", "il est crucial de", "il est nécessaire de",
    "il est fondamental de", "il est primordial de",
    # Sequence / enumeration
    "premièrement", "deuxièmement", "troisièmement", "en premier lieu",
    "en second lieu", "en dernier lieu", "pour commencer", "pour finir",
    "en fin de compte",
    # Causal / explanatory
    "en raison de", "du fait de", "grâce à", "à cause de", "dans la mesure où",
    "étant donné que", "compte tenu de", "au regard de",
    # Illustrative
    "à titre d'exemple", "par exemple", "notamment", "en particulier",
    "c'est-à-dire", "autrement dit",
    # Conclusive / summary
    "pour conclure", "en guise de conclusion", "dans l'ensemble",
    "globalement", "en substance", "en bref", "pour résumer",
    "il ressort que", "force est de constater",
    # Hedging / academic tone
    "il semble que", "il apparaît que", "on peut considérer que",
    "il est possible de", "il va sans dire que",
]

# Passive-voice patterns (French constructions)
PASSIVE_PATTERNS: List[str] = [
    r"\bil\s+(?:a|avait|aura|aurait)\s+été\b",
    r"\bils?\s+(?:est|sont|était|étaient|sera|seront|serait|seraient)\s+\w+(?:é|ée|és|ées)\b",
    r"\bil\s+est\s+(?:recommandé|conseillé|suggéré|nécessaire|important|essentiel|crucial|primordial|fondamental)\b",
    r"\ba\s+été\s+(?:effectué|réalisé|mis|fait|établi|constaté|observé|démontré|prouvé)\b",
    r"\bont\s+été\s+(?:effectués|réalisés|mis|faits|établis|constatés|observés|démontrés|prouvés)\b",
    r"\best\s+(?:considéré|perçu|vu|reconnu|défini|décrit)\b",
    r"\bsont\s+(?:considérés|perçus|vus|reconnus|définis|décrits)\b",
]

# Sentence-template patterns indicative of formulaic / plagiarised text
TEMPLATE_PATTERNS: List[str] = [
    r"\b\w+\s+permet\s+de\s+\w+",
    r"\bil\s+est\s+important\s+de\s+\w+",
    r"\bil\s+est\s+essentiel\s+de\s+\w+",
    r"\bil\s+est\s+nécessaire\s+de\s+\w+",
    r"\bil\s+convient\s+de\s+\w+",
    r"\bcela\s+(?:permet|implique|signifie|suggère)\b",
    r"\ben\s+ce\s+qui\s+concerne\b",
    r"\bdans\s+le\s+cadre\s+de\b",
    r"\bafin\s+de\s+(?:pouvoir|mieux|garantir|assurer)\b",
    r"\bforce\s+est\s+de\s+constater\b",
    r"\bil\s+(?:ressort|découle|résulte)\s+(?:que|de)\b",
    r"\bjoue\s+un\s+rôle\s+(?:important|essentiel|crucial|clé|majeur)\b",
]

# First-person pronouns (French)
FIRST_PERSON_TOKENS = {"je", "j", "me", "m", "moi", "nous", "on", "mon", "ma", "mes", "notre", "nos"}

# Set of common French stopwords for simplicity analysis
COMMON_FRENCH_WORDS = {
    "le", "la", "les", "de", "des", "un", "une", "et", "en", "que", "est", "a", "pour", "dans", "ce",
    "qui", "il", "elle", "ils", "elles", "sur", "mais", "avec", "nous", "vous", "se", "y", "ou", "par",
    "pas", "plus", "tout", "tous", "fait", "faire", "dire", "pouvoir", "vouloir", "devoir", "savoir",
    "aller", "venir", "prendre", "mon", "ton", "son", "ma", "ta", "sa", "mes", "tes", "ses", "notre",
    "votre", "leur", "nos", "vos", "leurs", "ceci", "cela", "ça", "ne", "ni", "si", "bien", "très",
    "non", "oui", "rien", "aucun", "aucune", "chaque", "quelque", "quelques", "autre", "autres",
    "même", "mêmes", "comme", "quand", "depuis", "pendant", "avant", "après", "sous", "sans", "chez",
}


# ---------------------------------------------------------------------------
# Tokenisation helpers
# ---------------------------------------------------------------------------

def tokenize_words(text: str) -> List[str]:
    """
    Tokenizes text into words. Supports Unicode characters for French accents.

    Args:
        text: The input text.

    Returns:
        List of lowercase word tokens.
    """
    if not text:
        return []
    return re.findall(r'\b\w+\b', text.lower())


def tokenize_sentences(text: str) -> List[str]:
    """
    Splits text into sentences based on standard French punctuation (. ! ?).

    Args:
        text: The input text.

    Returns:
        List of non-empty trimmed sentences.
    """
    if not text:
        return []
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


# ---------------------------------------------------------------------------
# Syllable counting
# ---------------------------------------------------------------------------

def count_syllables_french(word: str) -> int:
    """
    Estimates the number of syllables in a French word using rule-based heuristics.

    Args:
        word: The word to analyze.

    Returns:
        Estimated syllable count (minimum 1).
    """
    word = word.lower().strip()
    if not word:
        return 0

    vowels = "aeiouyéèàùâêîôûëïüæœ"

    count = sum(1 for char in word if char in vowels)

    # Subtract for trigraphs
    if "eau" in word:
        count -= 2 * word.count("eau")
    if "oeu" in word:
        count -= 2 * word.count("oeu")

    # Digraphs (exclude those already consumed by trigraphs)
    temp_word = word.replace("eau", "_").replace("oeu", "_")
    digraphs = ["ai", "au", "ei", "eu", "oi", "ou", "ui", "ae", "oe", "ie", "ue"]
    for dg in digraphs:
        count -= temp_word.count(dg)

    # Suffix adjustments
    if word.endswith("tion") or word.endswith("sion"):
        count -= 1

    # Silent endings (mute 'e')
    if count > 1:
        if word.endswith("e"):
            if len(word) >= 2 and word[-2] not in vowels:
                count -= 1
        elif word.endswith("es"):
            if len(word) >= 3 and word[-3] not in vowels:
                count -= 1
        elif word.endswith("ent"):
            if len(word) >= 4 and word[-4] not in vowels:
                count -= 1

    return max(1, count)


# ---------------------------------------------------------------------------
# Readability
# ---------------------------------------------------------------------------

def calculate_readability(words: List[str], sentence_count: int, syllable_count: int) -> float:
    """
    Calculates Kandel & Moles index (French adaptation of Flesch-Kincaid).
    Formula: 207 - 1.015 * (words/sentences) - 73.6 * (syllables/words)

    Args:
        words: List of word tokens.
        sentence_count: Total sentences.
        syllable_count: Total syllables.

    Returns:
        Readability score (typically 0-100).
    """
    word_count = len(words)
    if word_count == 0 or sentence_count == 0:
        return 0.0

    words_per_sentence = word_count / sentence_count
    syllables_per_word = syllable_count / word_count
    return 207 - (1.015 * words_per_sentence) - (73.6 * syllables_per_word)


def classify_readability(score: float) -> str:
    """
    Provides a qualitative description of Kandel & Moles readability score.

    Args:
        score: Kandel & Moles score.

    Returns:
        Readability classification label.
    """
    if score >= 80:
        return "Très facile (Niveau école primaire)"
    elif score >= 60:
        return "Facile (Niveau collège)"
    elif score >= 50:
        return "Standard / Assez difficile (Niveau lycée)"
    elif score >= 30:
        return "Difficile (Niveau universitaire)"
    else:
        return "Très difficile (Niveau scientifique / juridique)"


# ---------------------------------------------------------------------------
# Sub-signal calculators (each returns 0-100 normalised)
# ---------------------------------------------------------------------------

def _burstiness_score(sentences: List[str]) -> float:
    """
    Measures sentence-length uniformity via the coefficient of variation (CV).

    AI text tends to produce very uniform sentence lengths (low CV).
    Human text shows greater variation (high CV).

    Returns:
        Score 0-100 where 100 = maximally AI-like (very uniform).
    """
    if len(sentences) < 2:
        return 50.0  # insufficient data → neutral

    lengths = [len(tokenize_words(s)) for s in sentences]
    mean = sum(lengths) / len(lengths)
    if mean == 0:
        return 50.0

    variance = sum((x - mean) ** 2 for x in lengths) / len(lengths)
    std_dev = math.sqrt(variance)
    cv = std_dev / mean  # coefficient of variation

    # CV < 0.20 → very uniform → score ≈ 100
    # CV > 0.60 → high variance → score ≈ 0
    if cv <= 0.20:
        return 100.0
    elif cv >= 0.60:
        return 0.0
    else:
        return 100.0 * (1.0 - (cv - 0.20) / 0.40)


def _transition_density_score(text: str, word_count: int) -> float:
    """
    Measures density of formulaic AI transition words/phrases.

    Returns:
        Score 0-100 where 100 = saturated with transitions (AI-like).
    """
    if word_count < 10:
        return 0.0

    text_lower = text.lower()
    count = 0
    for phrase in AI_TRANSITION_WORDS:
        # Use word-boundary matching for multi-word phrases
        pattern = r'\b' + re.escape(phrase) + r'\b'
        count += len(re.findall(pattern, text_lower))

    density = count / word_count
    # 4% density or above → score 100
    if density >= 0.04:
        return 100.0
    return min(100.0, (density / 0.04) * 100.0)


def _passive_voice_score(text: str, sentence_count: int) -> float:
    """
    Counts passive-voice constructions per sentence.

    High passive ratio is characteristic of AI-generated formal French.

    Returns:
        Score 0-100 where 100 = very high passive ratio (AI-like).
    """
    if sentence_count == 0:
        return 0.0

    text_lower = text.lower()
    passive_count = 0
    for pat in PASSIVE_PATTERNS:
        passive_count += len(re.findall(pat, text_lower))

    ratio = passive_count / sentence_count
    # ratio >= 0.40 → score 100  (40 %+ sentences have passive)
    if ratio >= 0.40:
        return 100.0
    return min(100.0, (ratio / 0.40) * 100.0)


def _mattr_score(words: List[str], window_size: int = 50) -> float:
    """
    Moving-Average Type-Token Ratio (MATTR) for vocabulary diversity.

    Unlike simple TTR, MATTR is length-independent: it averages the TTR
    of a sliding window across the entire token sequence.

    Low MATTR → repetitive vocabulary → more AI-like.
    High MATTR → diverse vocabulary → more human.

    Returns:
        Score 0-100 where 100 = very low diversity (AI-like).
    """
    n = len(words)
    if n == 0:
        return 50.0

    # For very short texts, fall back to simple TTR
    if n <= window_size:
        ttr = len(set(words)) / n
    else:
        ttr_sum = 0.0
        count = 0
        for i in range(n - window_size + 1):
            window = words[i:i + window_size]
            ttr_sum += len(set(window)) / window_size
            count += 1
        ttr = ttr_sum / count

    # MATTR typically ranges 0.50 – 0.90 for French prose
    # Low MATTR (≤ 0.55) → score 100  (AI-like, repetitive)
    # High MATTR (≥ 0.85) → score 0   (human-like, diverse)
    if ttr <= 0.55:
        return 100.0
    elif ttr >= 0.85:
        return 0.0
    else:
        return 100.0 * (1.0 - (ttr - 0.55) / 0.30)


def _repetition_score(words: List[str], n_values: Tuple[int, ...] = (3, 4, 5)) -> float:
    """
    Detects repeated n-grams (3-5 word sequences) across the document.

    High repetition of multi-word sequences is a strong signal of AI
    generation or copy-paste plagiarism.

    Returns:
        Score 0-100 where 100 = heavy repetition (AI / plagiarism).
    """
    if len(words) < 10:
        return 0.0

    total_repeated = 0
    total_ngrams = 0

    for n in n_values:
        if len(words) < n:
            continue
        ngrams: List[str] = []
        for i in range(len(words) - n + 1):
            ngrams.append(" ".join(words[i:i + n]))
        total_ngrams += len(ngrams)
        counts = Counter(ngrams)
        # Count only n-grams appearing more than once
        total_repeated += sum(c - 1 for c in counts.values() if c > 1)

    if total_ngrams == 0:
        return 0.0

    ratio = total_repeated / total_ngrams
    # ratio >= 0.10 → score 100
    if ratio >= 0.10:
        return 100.0
    return min(100.0, (ratio / 0.10) * 100.0)


def _word_length_variance_score(words: List[str]) -> float:
    """
    Measures variance in word lengths.

    AI tends to use consistently formal/long words with low variance.
    Humans mix short and long words naturally.

    Returns:
        Score 0-100 where 100 = very low variance (AI-like).
    """
    if len(words) < 10:
        return 50.0

    lengths = [len(w) for w in words]
    mean = sum(lengths) / len(lengths)
    if mean == 0:
        return 50.0

    variance = sum((x - mean) ** 2 for x in lengths) / len(lengths)
    cv = math.sqrt(variance) / mean

    # CV < 0.30 → very uniform → score 100
    # CV > 0.65 → high variance → score 0
    if cv <= 0.30:
        return 100.0
    elif cv >= 0.65:
        return 0.0
    else:
        return 100.0 * (1.0 - (cv - 0.30) / 0.35)


def _question_frequency_score(text: str, sentence_count: int) -> float:
    """
    Measures how often the text uses questions (including rhetorical ones).

    Humans naturally use more questions. AI-generated text rarely asks questions.

    Returns:
        Score 0-100 where 100 = no questions at all (AI-like).
    """
    if sentence_count == 0:
        return 50.0

    question_count = text.count("?")
    ratio = question_count / sentence_count

    # ratio >= 0.15 → score 0 (plenty of questions, human-like)
    # ratio == 0    → score 100 (no questions, AI-like)
    if ratio >= 0.15:
        return 0.0
    return 100.0 * (1.0 - ratio / 0.15)


def _first_person_score(words: List[str]) -> float:
    """
    Measures first-person pronoun usage.

    Humans use 'je', 'nous', 'on', etc. more frequently.
    AI-generated French text favours impersonal constructions.

    Returns:
        Score 0-100 where 100 = no first-person usage (AI-like).
    """
    if len(words) < 10:
        return 50.0

    fp_count = sum(1 for w in words if w in FIRST_PERSON_TOKENS)
    ratio = fp_count / len(words)

    # ratio >= 0.05 → score 0  (lots of first person, human)
    # ratio == 0    → score 100 (no first person, AI)
    if ratio >= 0.05:
        return 0.0
    return 100.0 * (1.0 - ratio / 0.05)


# ---------------------------------------------------------------------------
# Composite AI probability
# ---------------------------------------------------------------------------

# Weights summing to 1.0
_WEIGHTS = {
    "burstiness":       0.25,
    "transition":       0.20,
    "passive":          0.15,
    "mattr":            0.15,
    "repetition":       0.10,
    "word_len_var":     0.05,
    "question":         0.05,
    "first_person":     0.05,
}


def calculate_ai_probability(text: str, words: List[str], sentences: List[str]) -> float:
    """
    Estimates the probability that the French text was AI-generated (0-100).

    Uses an 8-factor weighted composite of linguistic signals, each
    independently normalised to 0-100 before weighting.

    Args:
        text: Raw input text.
        words: Tokenized words.
        sentences: Tokenized sentences.

    Returns:
        Composite AI probability percentage (0-100).
    """
    word_count = len(words)
    sentence_count = len(sentences)

    if word_count < 10:
        return 0.0

    signals = {
        "burstiness":   _burstiness_score(sentences),
        "transition":   _transition_density_score(text, word_count),
        "passive":      _passive_voice_score(text, sentence_count),
        "mattr":        _mattr_score(words),
        "repetition":   _repetition_score(words),
        "word_len_var": _word_length_variance_score(words),
        "question":     _question_frequency_score(text, sentence_count),
        "first_person": _first_person_score(words),
    }

    composite = sum(signals[k] * _WEIGHTS[k] for k in _WEIGHTS)
    return max(0.0, min(100.0, composite))


# ---------------------------------------------------------------------------
# Plagiarism risk scoring
# ---------------------------------------------------------------------------

def get_plagiarism_risk_score(text: str) -> float:
    """
    Estimates plagiarism risk (0-100) based on textual surface patterns.

    Three sub-signals are combined equally:
        1. **N-gram repetition density** – repeated 3-5 word sequences.
        2. **Formulaic phrase frequency** – density of cliché academic phrases.
        3. **Sentence template patterns** – matches of 'X permet de Y' style templates.

    This is a heuristic indicator, not a replacement for full corpus comparison.

    Args:
        text: The French text to analyse.

    Returns:
        Plagiarism risk score (0-100) where 100 = very high risk.
    """
    if not text or not text.strip():
        return 0.0

    words = tokenize_words(text)
    sentences = tokenize_sentences(text)
    word_count = len(words)
    sentence_count = len(sentences)

    if word_count < 10:
        return 0.0

    # 1. N-gram repetition (reuse existing helper)
    ngram_score = _repetition_score(words)

    # 2. Formulaic phrase frequency
    text_lower = text.lower()
    formulaic_count = 0
    for phrase in AI_TRANSITION_WORDS:
        pattern = r'\b' + re.escape(phrase) + r'\b'
        formulaic_count += len(re.findall(pattern, text_lower))

    formulaic_density = formulaic_count / word_count
    # 5% density → score 100
    formulaic_score = min(100.0, (formulaic_density / 0.05) * 100.0)

    # 3. Sentence template patterns
    if sentence_count == 0:
        template_score = 0.0
    else:
        template_hits = 0
        for pat in TEMPLATE_PATTERNS:
            template_hits += len(re.findall(pat, text_lower))
        template_ratio = template_hits / sentence_count
        # ratio >= 0.30 → score 100
        template_score = min(100.0, (template_ratio / 0.30) * 100.0)

    # Equal weighting across all three sub-signals
    risk = (ngram_score * 0.35) + (formulaic_score * 0.30) + (template_score * 0.35)
    return max(0.0, min(100.0, round(risk, 1)))


# ---------------------------------------------------------------------------
# MATTR helper (public, for use by get_text_metrics)
# ---------------------------------------------------------------------------

def _compute_mattr(words: List[str], window_size: int = 50) -> float:
    """
    Computes the Moving-Average Type-Token Ratio for vocabulary diversity.

    Args:
        words: List of word tokens.
        window_size: Size of the sliding window.

    Returns:
        MATTR value between 0 and 1.
    """
    n = len(words)
    if n == 0:
        return 0.0
    if n <= window_size:
        return len(set(words)) / n

    ttr_sum = 0.0
    count = 0
    for i in range(n - window_size + 1):
        window = words[i:i + window_size]
        ttr_sum += len(set(window)) / window_size
        count += 1
    return ttr_sum / count


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------

def get_text_metrics(text: str) -> Dict[str, Any]:
    """
    Computes comprehensive linguistic metrics for French text comparison.

    Returns a dictionary containing:
        - word_count, character_count, sentence_count, syllable_count
        - estimated_reading_time_minutes, estimated_reading_time_seconds
        - ai_probability_score (0-100, weighted composite)
        - readability_index (Kandel & Moles)
        - readability_grade
        - vocabulary_richness_ttr (simple TTR, preserved for backwards compat)
        - vocabulary_richness_mattr (MATTR, more accurate)
        - plagiarism_risk_score (0-100)

    Args:
        text: The French text to analyze.

    Returns:
        Dictionary of metrics, safe for JSON serialization.
    """
    if not text or not text.strip():
        return {
            "word_count": 0,
            "character_count": 0,
            "sentence_count": 0,
            "syllable_count": 0,
            "estimated_reading_time_minutes": 0.0,
            "estimated_reading_time_seconds": 0,
            "ai_probability_score": 0.0,
            "readability_index": 0.0,
            "readability_grade": "N/A",
            "vocabulary_richness_ttr": 0.0,
            "vocabulary_richness_mattr": 0.0,
            "plagiarism_risk_score": 0.0,
        }

    words = tokenize_words(text)
    sentences = tokenize_sentences(text)

    word_count = len(words)
    character_count = len(text)
    sentence_count = len(sentences)

    # Syllable counts
    total_syllables = sum(count_syllables_french(w) for w in words)

    # 1. Estimated Reading Time (200 wpm average)
    reading_speed_wpm = 200
    reading_time_minutes = word_count / reading_speed_wpm
    reading_time_seconds = int(round(reading_time_minutes * 60))

    # 2. AI Probability Score (weighted composite)
    ai_prob = calculate_ai_probability(text, words, sentences)

    # 3. Readability Index (Kandel & Moles)
    readability_score = calculate_readability(words, sentence_count, total_syllables)
    readability_grade = classify_readability(readability_score)

    # 4. Vocabulary Richness – simple TTR (backwards compatible)
    unique_words = set(words)
    ttr = len(unique_words) / word_count if word_count > 0 else 0.0

    # 5. Vocabulary Richness – MATTR (more accurate)
    mattr = _compute_mattr(words)

    # 6. Plagiarism risk score
    plagiarism_risk = get_plagiarism_risk_score(text)

    return {
        "word_count": word_count,
        "character_count": character_count,
        "sentence_count": sentence_count,
        "syllable_count": total_syllables,
        "estimated_reading_time_minutes": round(reading_time_minutes, 2),
        "estimated_reading_time_seconds": reading_time_seconds,
        "ai_probability_score": round(ai_prob, 1),
        "readability_index": round(readability_score, 1),
        "readability_grade": readability_grade,
        "vocabulary_richness_ttr": round(ttr, 3),
        "vocabulary_richness_mattr": round(mattr, 3),
        "plagiarism_risk_score": round(plagiarism_risk, 1),
    }
