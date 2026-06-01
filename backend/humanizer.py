"""
French Document Humanization Service using Gemini API — Multi-Pass Engine.

This module provides the `FrenchHumanizer` class, which humanizes French documents
through a 3-pass pipeline designed to defeat both AI detection and plagiarism checkers:
  - Pass 1: Deep structural rewriting (syntax, voice, clause reordering)
  - Pass 2: Vocabulary enrichment and rhythm variation (burstiness, colloquial markers)
  - Pass 3: Final naturalness polish (human imperfections, rhetorical texture)

It utilizes the Gemini API with Structured Output to guarantee paragraph alignment,
batching, and robust error handling across all passes.
"""

import json
import logging
import os
import random
import time
from typing import Dict, List, Optional

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("FrenchHumanizer")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class HumanizerError(Exception):
    """Base exception for the humanizer service."""
    pass


class GeminiAPIError(HumanizerError):
    """Raised when the Gemini API returns an error."""
    def __init__(self, status_code: int, message: str, response_body: str = ""):
        super().__init__(f"Gemini API Error (status {status_code}): {message}")
        self.status_code = status_code
        self.response_body = response_body


class RateLimitError(GeminiAPIError):
    """Raised when Gemini API returns a 429 rate limit error."""
    pass


# ---------------------------------------------------------------------------
# Pass-specific system prompts
# ---------------------------------------------------------------------------

PASS_1_SYSTEM_PROMPT = (
    "Vous êtes un chirurgien syntaxique du français. Votre UNIQUE mission est de "
    "DÉCONSTRUIRE et RECONSTRUIRE chaque phrase de zéro en changeant radicalement "
    "sa structure grammaticale, tout en gardant le sens intact.\n\n"

    "RÈGLES ABSOLUES — PASS 1 : RESTRUCTURATION SYNTAXIQUE RADICALE\n\n"

    "1. DÉCONSTRUCTION OBLIGATOIRE DE CHAQUE PHRASE :\n"
    "   - Prenez chaque phrase source. Identifiez sujet, verbe, compléments.\n"
    "   - Réassemblez-les dans un NOUVEL ORDRE. Si la phrase commence par le sujet, "
    "commencez par le complément circonstanciel ou par une subordonnée.\n"
    "   - Inversez systématiquement l'ordre des propositions. Si la cause précède "
    "la conséquence, mettez la conséquence d'abord.\n"
    "   - Transformez les constructions nominales en constructions verbales et "
    "vice-versa. Ex : 'L'amélioration des performances' → 'Les performances "
    "se sont nettement améliorées'.\n\n"

    "2. CHANGEMENT DE VOIX SYSTÉMATIQUE :\n"
    "   - Toute phrase passive → voix active avec un sujet vivant.\n"
    "   - 'Il a été décidé de' → 'Nous avons décidé de' / 'L'équipe a tranché'\n"
    "   - 'La mise en œuvre a été effectuée' → 'Nous avons déployé' / 'Le système fonctionne désormais'\n"
    "   - Les tournures impersonnelles ('il convient de', 'il est nécessaire de', "
    "'il s'avère que') → formes personnelles directes.\n\n"

    "3. SCISSION ET FUSION DE PHRASES :\n"
    "   - Les phrases de plus de 30 mots : COUPEZ-les en deux phrases distinctes.\n"
    "   - Deux phrases courtes consécutives traitant du même sujet : FUSIONNEZ-les "
    "avec une articulation naturelle.\n"
    "   - Objectif : aucune phrase ne doit garder la même longueur que l'originale.\n\n"

    "4. RÉAGENCEMENT DE L'INFORMATION :\n"
    "   - Si un paragraphe présente A puis B puis C, réorganisez en B-A-C ou C-A-B "
    "quand cela reste logique.\n"
    "   - Déplacez les compléments de fin de phrase vers le début.\n"
    "   - Intercalez des incises là où il n'y en avait pas.\n\n"

    "5. MOTS ET EXPRESSIONS FORMELLEMENT INTERDITS (ne les utilisez JAMAIS) :\n"
    "   'En conclusion', 'Tout d'abord', 'De plus', 'En effet', 'Il convient de noter', "
    "'Il est important de souligner', 'Ainsi', 'Par conséquent', 'Néanmoins', "
    "'Il est à noter que', 'En outre', 'Somme toute', 'D'une part / d'autre part', "
    "'Afin de', 'Force est de constater', 'Dans ce cadre', 'Partant de ce fait', "
    "'Notamment', 'Il s'agit de', 'À cet égard', 'Dans cette optique', "
    "'Au regard de', 'En ce qui concerne', 'Il apparaît que', 'On peut constater que', "
    "'Il va sans dire que', 'En définitive'.\n\n"

    "6. PRÉSERVATION STRICTE :\n"
    "   - NE modifiez JAMAIS les faits, chiffres, noms propres, acronymes, "
    "technologies (FastAPI, Vite, React, etc.).\n"
    "   - L'entrée est une liste de paragraphes. La sortie DOIT contenir EXACTEMENT "
    "le même nombre d'éléments réécrits dans le même ordre. Ne fusionnez et "
    "n'omettez AUCUN paragraphe."
)

PASS_2_SYSTEM_PROMPT = (
    "Vous êtes un styliste linguistique français spécialisé dans le RYTHME et la "
    "TEXTURE du langage. Votre mission : transformer un texte déjà restructuré pour "
    "lui donner un rythme humain vivant, imprévisible, impossible à détecter par l'IA.\n\n"

    "RÈGLES ABSOLUES — PASS 2 : VOCABULAIRE ET RYTHME\n\n"

    "1. INJECTION DE BURSTINESS (variation extrême de longueur) :\n"
    "   - C'est la signature #1 de l'écriture humaine : des phrases TRÈS courtes "
    "suivies de phrases TRÈS longues.\n"
    "   - Visez ce schéma dans chaque paragraphe :\n"
    "     • Au moins 1 phrase de 3 à 7 mots (percutante, directe)\n"
    "     • Au moins 1 phrase de 28 à 40 mots (développée, fluide, avec incises)\n"
    "     • Le reste : phrases moyennes de 12 à 22 mots\n"
    "   - INTERDICTION d'avoir 3 phrases consécutives de longueur similaire (±5 mots).\n\n"

    "2. REMPLACEMENT DU VOCABULAIRE ACADÉMIQUE LOURD :\n"
    "   - 'mettre en œuvre' → 'lancer', 'déployer', 'mettre en place'\n"
    "   - 'optimiser' → 'améliorer', 'affiner', 'rendre plus efficace'\n"
    "   - 'problématique' → 'question', 'enjeu', 'défi'\n"
    "   - 'paradigme' → 'approche', 'modèle', 'vision'\n"
    "   - 'substantiel' → 'important', 'conséquent', 'significatif'\n"
    "   - 'faciliter' → 'simplifier', 'accélérer', 'fluidifier'\n"
    "   - 'constituant' → 'qui forme', 'au cœur de'\n"
    "   - Remplacez tout mot qui sonne 'académique lourd' par son équivalent naturel.\n\n"

    "3. MARQUEURS CONVERSATIONNELS ET TRANSITIONS NATURELLES :\n"
    "   - Utilisez des connecteurs qui sonnent humain :\n"
    "     'Concrètement', 'Dans la pratique', 'Pour aller plus loin', "
    "'C'est pourquoi', 'Mais en réalité', 'Résultat :', 'Le constat est clair', "
    "'D'où l'idée de', 'Ce qui change la donne', 'Autrement dit', "
    "'Le point clé ici', 'En clair', 'La nuance importante'\n"
    "   - Variez les attaques de phrases : commencez parfois par un complément, "
    "parfois par un verbe, parfois par une question, parfois par un constat bref.\n\n"

    "4. RYTHME DE PONCTUATION :\n"
    "   - Utilisez les deux-points (:) pour introduire des explications directes.\n"
    "   - Utilisez le tiret cadratin (—) pour des incises naturelles.\n"
    "   - Évitez les points-virgules excessifs (max 1 par paragraphe).\n"
    "   - Un paragraphe peut finir par un constat court sans verbe. Effet punch.\n\n"

    "5. MOTS ET EXPRESSIONS FORMELLEMENT INTERDITS (ne les utilisez JAMAIS) :\n"
    "   'En conclusion', 'Tout d'abord', 'De plus', 'En effet', 'Il convient de noter', "
    "'Il est important de souligner', 'Ainsi', 'Par conséquent', 'Néanmoins', "
    "'Il est à noter que', 'En outre', 'Somme toute', 'D'une part / d'autre part', "
    "'Afin de', 'Force est de constater', 'Dans ce cadre', 'Partant de ce fait', "
    "'Notamment', 'Il s'agit de', 'À cet égard', 'Dans cette optique', "
    "'Au regard de', 'En ce qui concerne', 'Il apparaît que', 'On peut constater que', "
    "'Il va sans dire que', 'En définitive'.\n\n"

    "6. PRÉSERVATION STRICTE :\n"
    "   - NE modifiez JAMAIS les faits, chiffres, noms propres, acronymes, technologies.\n"
    "   - L'entrée est une liste de paragraphes. La sortie DOIT contenir EXACTEMENT "
    "le même nombre d'éléments réécrits dans le même ordre. Ne fusionnez et "
    "n'omettez AUCUN paragraphe."
)

PASS_3_SYSTEM_PROMPT = (
    "Vous êtes un relecteur humain natif français effectuant une dernière passe de "
    "polissage. Le texte a déjà été restructuré et rythmé. Votre mission : lui donner "
    "le dernier souffle d'authenticité humaine pour qu'il soit IMPOSSIBLE à détecter "
    "comme généré par une IA.\n\n"

    "RÈGLES ABSOLUES — PASS 3 : NATURALITÉ ET IMPERFECTIONS HUMAINES\n\n"

    "1. AJOUT D'IMPERFECTIONS SUBTILES ET AUTHENTIQUES :\n"
    "   - Les humains ne sont pas parfaits dans leur écriture. Ajoutez :\n"
    "     • Des reformulations légères en cours de phrase ('c'est-à-dire', "
    "'ou plutôt', 'pour être plus précis')\n"
    "     • Des apartés entre parenthèses ou entre tirets qui ajoutent une touche "
    "personnelle ('— et c'est un point souvent négligé —')\n"
    "     • Des expressions qui trahissent une réflexion en cours ('on pourrait se "
    "demander si', 'la question mérite d'être posée')\n"
    "   - NE PAS en abuser : 1 à 2 par paragraphe maximum, pas plus.\n\n"

    "2. QUESTIONS RHÉTORIQUES (avec parcimonie) :\n"
    "   - Insérez UNE question rhétorique tous les 3 à 5 paragraphes.\n"
    "   - Elle doit sonner naturelle : 'Mais est-ce vraiment suffisant ?', "
    "'Pourquoi ce choix ?' , 'Et si on regardait les choses autrement ?'\n"
    "   - PAS de questions artificielles. Si ça sonne forcé, ne mettez rien.\n\n"

    "3. NETTOYAGE DES PATTERNS IA RÉSIDUELS :\n"
    "   - Relisez chaque paragraphe et vérifiez qu'aucun pattern IA ne subsiste :\n"
    "     • Pas de listes parallèles avec la même structure grammaticale répétée 3+ fois\n"
    "     • Pas de conclusions qui commencent par un connecteur logique lourd\n"
    "     • Pas de phrases qui commencent toutes par le même type de mot\n"
    "     • Pas de vocabulaire trop poli ou trop lissé ('il est fondamental', "
    "'il est crucial', 'il est essentiel')\n"
    "   - Si vous trouvez un pattern : cassez-le en reformulant cette phrase.\n\n"

    "4. FLUIDITÉ ET TON FINAL :\n"
    "   - Le texte doit se lire comme un rapport de stage écrit par un étudiant "
    "francophone compétent : professionnel, mais avec une voix propre.\n"
    "   - Utilisez 'nous' et 'notre' naturellement.\n"
    "   - Le ton reste rigoureux et universitaire, mais PAS robotique.\n"
    "   - Chaque paragraphe doit pouvoir être lu à voix haute sans sonner artificiel.\n\n"

    "5. VÉRIFICATION FINALE DE BURSTINESS :\n"
    "   - Comptez mentalement la longueur des phrases. Si 3 phrases consécutives "
    "ont une longueur similaire, modifiez-en une (raccourcissez ou allongez).\n"
    "   - Le ratio idéal par paragraphe : 20% phrases courtes, 50% moyennes, "
    "30% longues.\n\n"

    "6. MOTS ET EXPRESSIONS FORMELLEMENT INTERDITS (ne les utilisez JAMAIS) :\n"
    "   'En conclusion', 'Tout d'abord', 'De plus', 'En effet', 'Il convient de noter', "
    "'Il est important de souligner', 'Ainsi', 'Par conséquent', 'Néanmoins', "
    "'Il est à noter que', 'En outre', 'Somme toute', 'D'une part / d'autre part', "
    "'Afin de', 'Force est de constater', 'Dans ce cadre', 'Partant de ce fait', "
    "'Notamment', 'Il s'agit de', 'À cet égard', 'Dans cette optique', "
    "'Au regard de', 'En ce qui concerne', 'Il apparaît que', 'On peut constater que', "
    "'Il va sans dire que', 'En définitive'.\n\n"

    "7. PRÉSERVATION STRICTE :\n"
    "   - NE modifiez JAMAIS les faits, chiffres, noms propres, acronymes, technologies.\n"
    "   - L'entrée est une liste de paragraphes. La sortie DOIT contenir EXACTEMENT "
    "le même nombre d'éléments réécrits dans le même ordre. Ne fusionnez et "
    "n'omettez AUCUN paragraphe."
)


# ---------------------------------------------------------------------------
# Pass configuration
# ---------------------------------------------------------------------------

PASS_CONFIGS = [
    {
        "name": "Pass 1 — Structural Rewriting",
        "system_prompt": PASS_1_SYSTEM_PROMPT,
        "temperature": 1.1,
        "user_prompt_prefix": (
            "INSTRUCTION : Déconstruisez et restructurez radicalement chaque paragraphe. "
            "Changez l'ordre des propositions, la voix, la longueur des phrases. "
            "Le sens doit rester identique mais la structure syntaxique doit être "
            "méconnaissable par rapport à l'original.\n\n"
        ),
    },
    {
        "name": "Pass 2 — Vocabulary & Rhythm",
        "system_prompt": PASS_2_SYSTEM_PROMPT,
        "temperature": 1.0,
        "user_prompt_prefix": (
            "INSTRUCTION : Le texte ci-dessous a déjà été restructuré syntaxiquement. "
            "Maintenant, travaillez sur le RYTHME et le VOCABULAIRE. Créez une variation "
            "extrême de longueur de phrases (burstiness). Remplacez le vocabulaire "
            "académique lourd par des mots naturels. Ajoutez des marqueurs conversationnels.\n\n"
        ),
    },
    {
        "name": "Pass 3 — Naturalness Polish",
        "system_prompt": PASS_3_SYSTEM_PROMPT,
        "temperature": 0.85,
        "user_prompt_prefix": (
            "INSTRUCTION : Le texte ci-dessous a déjà été restructuré et rythmé. "
            "Effectuez un polissage final. Ajoutez de subtiles imperfections humaines "
            "(reformulations, apartés, questions rhétoriques avec parcimonie). "
            "Éliminez tout pattern IA résiduel. Le texte doit sonner parfaitement humain.\n\n"
        ),
    },
]


# ---------------------------------------------------------------------------
# Main Humanizer Class
# ---------------------------------------------------------------------------

class FrenchHumanizer:
    """
    A multi-pass humanization engine that rewrites AI-like French text into
    natural, human-written French using 3 specialized Gemini API passes.

    Each pass targets a different dimension of AI detectability:
      1. Syntactic structure (anti-plagiarism)
      2. Vocabulary and rhythm (anti-AI-detection / burstiness)
      3. Naturalness and human imperfections (final polish)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-3.5-flash",
        batch_size: int = 2,
        max_retries: int = 5,
        backoff_factor: float = 2.0,
        progress_callback=None,
    ):
        """
        Initializes the FrenchHumanizer service.

        Args:
            api_key: The Gemini API key. Falls back to GEMINI_API_KEY env var.
            model: The Gemini model name (e.g. 'gemini-3.5-flash').
            batch_size: Number of paragraphs per API request (default 2 for
                        more focused per-paragraph attention).
            max_retries: Maximum retry attempts for transient API failures.
            backoff_factor: Exponential growth factor for retry backoff.
            progress_callback: Optional callable(dict) invoked with progress
                updates during multi-pass processing.
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Gemini API key is required. Please provide it in the constructor or "
                "set the GEMINI_API_KEY environment variable."
            )

        self.model = model
        self.batch_size = max(1, batch_size)
        self.max_retries = max(0, max_retries)
        self.backoff_factor = backoff_factor
        self.progress_callback = progress_callback

    # ------------------------------------------------------------------
    # Low-level API helpers
    # ------------------------------------------------------------------

    def _call_gemini_api_with_retry(self, payload: dict) -> dict:
        """Executes the Gemini API call with robust exponential backoff retry."""
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        params = {"key": self.api_key}
        headers = {"Content-Type": "application/json"}

        retries = 0
        current_backoff = 1.0  # Start with 1 second backoff

        while True:
            try:
                logger.debug(
                    f"Calling Gemini API (attempt {retries + 1}/{self.max_retries + 1})..."
                )
                response = requests.post(
                    url, json=payload, headers=headers, params=params, timeout=120
                )

                if response.status_code == 200:
                    return response.json()

                # Handle rate limit (429) or transient server errors (5xx)
                if response.status_code == 429:
                    logger.warning(
                        f"Rate limit exceeded (429). Retrying in {current_backoff:.2f}s..."
                    )
                    if retries >= self.max_retries:
                        raise RateLimitError(
                            response.status_code,
                            "Rate limit exceeded. Max retries reached.",
                            response.text,
                        )
                elif response.status_code >= 500:
                    logger.warning(
                        f"Gemini server error ({response.status_code}). "
                        f"Retrying in {current_backoff:.2f}s..."
                    )
                    if retries >= self.max_retries:
                        raise GeminiAPIError(
                            response.status_code,
                            f"Server error: {response.reason}",
                            response.text,
                        )
                else:
                    # Non-retryable client errors (400, 403, 404, etc.)
                    raise GeminiAPIError(
                        response.status_code,
                        f"Client error: {response.reason}",
                        response.text,
                    )

            except requests.RequestException as e:
                logger.warning(
                    f"Network error: {e}. Retrying in {current_backoff:.2f}s..."
                )
                if retries >= self.max_retries:
                    raise HumanizerError(
                        f"Network error after max retries: {e}"
                    ) from e

            # Wait with exponential backoff + jitter
            sleep_time = current_backoff + random.uniform(0.0, 0.5)
            time.sleep(sleep_time)

            retries += 1
            current_backoff *= self.backoff_factor

    def _extract_json(self, response_data: dict) -> dict:
        """Extracts and parses JSON from the structured Gemini API response."""
        text = ""
        try:
            candidates = response_data.get("candidates", [])
            if not candidates:
                raise HumanizerError("No candidates returned from the Gemini API.")

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if not parts:
                raise HumanizerError("No parts found in the model response content.")

            text = parts[0].get("text", "").strip()
            if not text:
                raise HumanizerError("Empty text found in the model response.")

            # Clean markdown code block wraps if present
            if text.startswith("```"):
                lines = text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                text = "\n".join(lines).strip()

            return json.loads(text)
        except (KeyError, IndexError) as e:
            raise HumanizerError(
                f"Failed to parse the response format: {e}"
            ) from e
        except json.JSONDecodeError as e:
            raise HumanizerError(
                f"Failed to decode JSON from response: {e}. Raw text: {text[:500]}"
            ) from e

    # ------------------------------------------------------------------
    # Single-pass chunk processing
    # ------------------------------------------------------------------

    def _humanize_chunk(
        self,
        chunk: List[str],
        pass_config: Dict,
    ) -> List[str]:
        """
        Humanizes a single batch of paragraphs for ONE pass using
        the given pass configuration (system prompt, temperature, user prefix).
        """
        user_prompt = (
            pass_config["user_prompt_prefix"]
            + "Voici la liste des paragraphes à traiter. "
            "Renvoyez un objet JSON avec la clé 'paragraphs' contenant un tableau "
            "de chaînes — EXACTEMENT le même nombre d'éléments réécrits, même ordre.\n\n"
            f"INPUT PARAGRAPHS:\n{json.dumps(chunk, ensure_ascii=False, indent=2)}"
        )

        generation_config = {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "object",
                "properties": {
                    "paragraphs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Les paragraphes réécrits dans le même ordre "
                            "et le même nombre."
                        ),
                    }
                },
                "required": ["paragraphs"],
            },
            "temperature": pass_config["temperature"],
        }

        payload = {
            "contents": [
                {"parts": [{"text": user_prompt}]}
            ],
            "system_instruction": {
                "parts": [{"text": pass_config["system_prompt"]}]
            },
            "generationConfig": generation_config,
        }

        response_data = self._call_gemini_api_with_retry(payload)
        parsed = self._extract_json(response_data)

        paragraphs = parsed.get("paragraphs", [])
        if not isinstance(paragraphs, list):
            raise HumanizerError(
                f"Response 'paragraphs' is not a list. Got type: {type(paragraphs)}"
            )

        return [str(p) for p in paragraphs]

    def _humanize_single_paragraph(
        self,
        paragraph: str,
        pass_config: Dict,
    ) -> str:
        """Fallback: process a single paragraph independently for one pass."""
        results = self._humanize_chunk([paragraph], pass_config)
        if results:
            return results[0]
        return paragraph

    # ------------------------------------------------------------------
    # Single full pass over all paragraphs
    # ------------------------------------------------------------------

    def _run_single_pass(
        self,
        paragraphs: List[str],
        pass_config: Dict,
        pass_number: int,
    ) -> List[str]:
        """
        Runs one complete pass over all paragraphs using the given configuration.
        Handles batching, fallback, and error propagation.
        """
        pass_name = pass_config["name"]
        total = len(paragraphs)
        logger.info(
            f"[{pass_name}] Starting pass {pass_number}/3 — "
            f"{total} paragraph(s), batch_size={self.batch_size}, "
            f"temperature={pass_config['temperature']}"
        )

        # Separate empty from non-empty
        cleaned = [p.strip() for p in paragraphs]
        non_empty_indices = [i for i, p in enumerate(cleaned) if p]
        non_empty_paragraphs = [cleaned[i] for i in non_empty_indices]

        if not non_empty_paragraphs:
            logger.info(f"[{pass_name}] All paragraphs empty, skipping pass.")
            return cleaned

        results = [""] * len(cleaned)

        # Process in batches
        num_batches = (len(non_empty_paragraphs) + self.batch_size - 1) // self.batch_size
        for batch_idx, i in enumerate(
            range(0, len(non_empty_paragraphs), self.batch_size)
        ):
            chunk = non_empty_paragraphs[i : i + self.batch_size]
            chunk_indices = non_empty_indices[i : i + self.batch_size]

            logger.info(
                f"[{pass_name}] Processing batch {batch_idx + 1}/{num_batches} "
                f"({len(chunk)} paragraph(s))..."
            )

            # Emit progress callback so the SSE stream can update the frontend
            if self.progress_callback:
                self.progress_callback({
                    "pass_number": pass_number,
                    "pass_name": pass_name,
                    "batch": batch_idx + 1,
                    "total_batches": num_batches,
                    "message": f"{pass_name} — batch {batch_idx + 1}/{num_batches}"
                })

            try:
                humanized_chunk = self._humanize_chunk(chunk, pass_config)

                if len(humanized_chunk) == len(chunk):
                    for idx, humanized_p in zip(chunk_indices, humanized_chunk):
                        results[idx] = humanized_p
                else:
                    logger.warning(
                        f"[{pass_name}] Count mismatch (expected {len(chunk)}, "
                        f"got {len(humanized_chunk)}). Falling back to sequential."
                    )
                    for idx, p in zip(chunk_indices, chunk):
                        results[idx] = self._humanize_single_paragraph(
                            p, pass_config
                        )

            except (RateLimitError, GeminiAPIError) as e:
                logger.error(
                    f"[{pass_name}] Fatal Gemini error at batch {batch_idx + 1}: {e}. "
                    "Propagating."
                )
                raise
            except Exception as e:
                logger.error(
                    f"[{pass_name}] Error at batch {batch_idx + 1}: {e}. "
                    "Attempting paragraph-by-paragraph fallback."
                )
                for idx, p in zip(chunk_indices, chunk):
                    try:
                        results[idx] = self._humanize_single_paragraph(
                            p, pass_config
                        )
                    except (RateLimitError, GeminiAPIError) as inner_e:
                        logger.error(
                            f"[{pass_name}] Fatal Gemini error in fallback "
                            f"at paragraph {idx}: {inner_e}"
                        )
                        raise
                    except Exception as inner_e:
                        logger.error(
                            f"[{pass_name}] Fallback failed for paragraph {idx}: "
                            f"{inner_e}. Preserving text from previous pass."
                        )
                        results[idx] = p

        # Restore blank paragraphs
        for i, p in enumerate(cleaned):
            if not p:
                results[i] = paragraphs[i]

        logger.info(f"[{pass_name}] Pass {pass_number}/3 complete.")
        return results

    # ------------------------------------------------------------------
    # Multi-pass pipeline
    # ------------------------------------------------------------------

    def humanize_paragraphs(self, paragraphs: List[str]) -> List[str]:
        """
        Humanizes a list of French paragraphs through 3 specialized passes.

        Args:
            paragraphs: List of paragraphs in French to humanize.

        Returns:
            A list of deeply humanized paragraphs matching the exact size
            and order of the input.
        """
        if not paragraphs:
            return []

        current_paragraphs = list(paragraphs)

        for pass_number, pass_config in enumerate(PASS_CONFIGS, start=1):
            current_paragraphs = self._run_single_pass(
                current_paragraphs, pass_config, pass_number
            )
            # Small delay between passes to avoid rate-limiting bursts
            if pass_number < len(PASS_CONFIGS):
                delay = random.uniform(1.0, 2.0)
                logger.debug(
                    f"Inter-pass delay: {delay:.1f}s before pass {pass_number + 1}"
                )
                time.sleep(delay)

        logger.info("All 3 humanization passes complete.")
        return current_paragraphs

    def humanize_text(self, text: str) -> str:
        """
        Splits a text document by double-newlines into paragraphs,
        humanizes each through the 3-pass pipeline, and reconstructs.

        Args:
            text: Full text document in French.

        Returns:
            Reconstructed humanized document text.
        """
        if not text.strip():
            return text

        paragraphs = text.split("\n\n")

        logger.info(
            f"Starting multi-pass humanization: {len(paragraphs)} paragraph(s) "
            f"across 3 passes."
        )

        humanized_paragraphs = self.humanize_paragraphs(paragraphs)
        return "\n\n".join(humanized_paragraphs)


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    print("=== French Document Humanizer — Multi-Pass Engine Demo ===")

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("\n[WARNING] GEMINI_API_KEY environment variable is not set.")
        print("Please set your GEMINI_API_KEY to run the demo.")
        print('Example: $env:GEMINI_API_KEY="your-key" or export GEMINI_API_KEY="your-key"\n')
        sys.exit(1)

    # Robot-like AI-written French text sample
    sample_text = (
        "En conclusion, il convient de noter que l'adoption de l'intelligence artificielle "
        "au sein des entreprises est devenue une nécessité de premier ordre. En effet, tout d'abord, "
        "cette transition permet d'améliorer la productivité de manière significative. De plus, il est "
        "important de souligner que les gains de temps générés sont considérables.\n\n"
        "Par conséquent, il est recommandé de mettre en place une stratégie claire et structurée afin de "
        "faciliter la transition numérique. Néanmoins, il convient de rappeler que la formation continue "
        "des collaborateurs reste un facteur clé de réussite absolue."
    )

    print("\n--- ORIGINAL AI FRENCH TEXT ---")
    print(sample_text)
    print("--------------------------------")

    try:
        humanizer = FrenchHumanizer(api_key=key)

        print("\nRunning 3-pass humanization pipeline...")
        humanized_text = humanizer.humanize_text(sample_text)

        print("\n--- HUMANIZED FRENCH TEXT (3 passes) ---")
        print(humanized_text)
        print("-----------------------------------------")

    except Exception as err:
        print(f"\n[ERROR] An error occurred while running the demo: {err}")
        sys.exit(1)
