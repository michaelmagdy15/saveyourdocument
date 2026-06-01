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

import asyncio
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

UNIFIED_HUMANIZATION_SYSTEM_PROMPT = (
    "Vous êtes un rédacteur humain natif français et un expert de la restructuration linguistique. "
    "Votre mission absolue est de réécrire le texte d'entrée pour le rendre indétectable comme généré par une IA, "
    "libre de plagiat, extrêmement naturel et vivant. Vous devez fusionner de manière cohérente les dimensions suivantes de l'écriture humaine :\n\n"
    
    "RÈGLES ABSOLUES — RESTRUCTURATION, STYLE, RYTHME ET NATURALITÉ\n\n"
    
    "1. RESTRUCTURATION SYNTAXIQUE RADICALE :\n"
    "   - DÉCONSTRUISEZ et RECONSTRUISEZ chaque phrase de zéro. Ne conservez pas la même structure grammaticale.\n"
    "   - Inversez systématiquement l'ordre des propositions. Par exemple, si la cause est présentée en premier, placez la conséquence d'abord, reliée naturellement.\n"
    "   - Si le sujet commence la phrase originale, commencez par un complément circonstanciel ou une subordonnée.\n"
    "   - Passez systématiquement les constructions passives ou impersonnelles ('il convient de', 'il est nécessaire de') à la voix active personnelle directe ('nous avons', 'notre équipe').\n"
    "   - Coupez en deux les phrases de plus de 30 mots, et fusionnez les phrases courtes connexes.\n\n"
    
    "2. VARIATION RYTHMIQUE (BURSTINESS VIVANTE) :\n"
    "   - Les humains écrivent avec une variation extrême de longueur de phrase. Recréez ce rythme unique :\n"
    "     • Visez au moins 1 phrase très courte et percutante (3 à 7 mots).\n"
    "     • Visez au moins 1 phrase longue et fluide avec incises (28 à 40 mots).\n"
    "     • Le reste doit être composé de phrases de longueur moyenne (12 à 22 mots).\n"
    "   - Interdiction formelle d'enchaîner 3 phrases de longueur similaire (±5 mots).\n"
    "   - Utilisez une ponctuation humaine expressive : les deux-points (:) pour introduire directement une explication, ou le tiret cadratin (—) pour des incises naturelles.\n\n"
    
    "3. VOCABULAIRE NATUREL ET VIVANT (ANTI-AI PATTERNS) :\n"
    "   - Remplacer systématiquement les verbes et termes trop académiques ou polis ('mettre en œuvre', 'optimiser', 'problématique', 'essentiel', 'fondamental', 'crucial').\n"
    "   - Utilisez des connecteurs conversationnels fluides et humains : 'Concrètement', 'Dans la pratique', 'Résultat :', 'Le constat est clair', 'En clair', 'La nuance importante'.\n\n"
    
    "4. IMPERFECTIONS ET AUTHENTICITÉ HUMAINE :\n"
    "   - Ajoutez 1 ou 2 imperfections authentiques par paragraphe (légère reformulation comme 'ou plutôt', 'pour être plus précis', ou un aparté naturel entre parenthèses ou tirets).\n"
    "   - Insérez environ une question rhétorique tous les 4 ou 5 paragraphes (ex: 'Mais est-ce suffisant ?', 'Pourquoi ce choix ?').\n\n"
    
    "5. MOTS ET CONNECTEURS FORMELLEMENT INTERDITS (ne les utilisez JAMAIS) :\n"
    "   'En conclusion', 'Tout d'abord', 'De plus', 'En effet', 'Il convient de noter', "
    "   'Il est important de souligner', 'Ainsi', 'Par conséquent', 'Néanmoins', "
    "   'Il est à noter que', 'En outre', 'Somme toute', 'D'une part / d'autre part', "
    "   'Afin de', 'Force est de constater', 'Dans ce cadre', 'Partant de ce fait', "
    "   'Notamment', 'Il s'agit de', 'À cet égard', 'Dans cette optique', "
    "   'Au regard de', 'En ce qui concerne', 'Il apparaît que', 'On peut constater que', "
    "   'Il va sans dire que', 'En définitive'.\n\n"
    
    "6. PRÉSERVATION STRICTE :\n"
    "   - NE modifiez JAMAIS les faits, chiffres, noms propres, acronymes, technologies (FastAPI, React, etc.).\n"
    "   - L'entrée est une liste de paragraphes. La sortie DOIT contenir EXACTEMENT le même nombre d'éléments réécrits dans le même ordre. Ne fusionnez et n'omettez AUCUN paragraphe."
)

PASS_CONFIGS = [
    {
        "name": "Unified Humanization Pass",
        "system_prompt": UNIFIED_HUMANIZATION_SYSTEM_PROMPT,
        "temperature": 1.0,
        "user_prompt_prefix": (
            "INSTRUCTION : Réécrivez, restructurez et humanisez en profondeur les paragraphes suivants. "
            "Appliquez toutes les règles de restructuration syntaxique, de burstiness, de vocabulaire fluide "
            "et d'imperfections authentiques.\n\n"
        ),
    }
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

    async def _run_single_pass(
        self,
        paragraphs: List[str],
        pass_config: Dict,
        pass_number: int,
    ) -> List[str]:
        """
        Runs one complete pass over all paragraphs using the given configuration.
        Processes paragraph batches concurrently using asyncio.gather and thread-pool execution.
        """
        pass_name = pass_config["name"]
        total = len(paragraphs)
        logger.info(
            f"[{pass_name}] Starting pass {pass_number}/1 — "
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

        # Process in batches concurrently
        num_batches = (len(non_empty_paragraphs) + self.batch_size - 1) // self.batch_size

        async def process_batch_task(batch_idx: int, start_idx: int):
            chunk = non_empty_paragraphs[start_idx : start_idx + self.batch_size]
            chunk_indices = non_empty_indices[start_idx : start_idx + self.batch_size]

            logger.info(
                f"[{pass_name}] Processing batch {batch_idx + 1}/{num_batches} "
                f"({len(chunk)} paragraph(s))..."
            )

            # Emit progress callback so the SSE stream can update the frontend
            if self.progress_callback:
                prog_data = {
                    "pass_number": pass_number,
                    "pass_name": pass_name,
                    "batch": batch_idx + 1,
                    "total_batches": num_batches,
                    "message": f"{pass_name} — batch {batch_idx + 1}/{num_batches}"
                }
                try:
                    if asyncio.iscoroutinefunction(self.progress_callback):
                        await self.progress_callback(prog_data)
                    else:
                        self.progress_callback(prog_data)
                except Exception as cb_err:
                    logger.error(f"Error in progress callback: {cb_err}")

            try:
                # Call blocking humanize_chunk inside a thread
                humanized_chunk = await asyncio.to_thread(self._humanize_chunk, chunk, pass_config)

                if len(humanized_chunk) == len(chunk):
                    for idx, humanized_p in zip(chunk_indices, humanized_chunk):
                        results[idx] = humanized_p
                else:
                    logger.warning(
                        f"[{pass_name}] Count mismatch (expected {len(chunk)}, "
                        f"got {len(humanized_chunk)}). Falling back to sequential."
                    )
                    for idx, p in zip(chunk_indices, chunk):
                        results[idx] = await asyncio.to_thread(self._humanize_single_paragraph, p, pass_config)

            except (RateLimitError, GeminiAPIError) as e:
                logger.error(
                    f"[{pass_name}] Fatal Gemini error at batch {batch_idx + 1}: {e}."
                )
                raise
            except Exception as e:
                logger.error(
                    f"[{pass_name}] Error at batch {batch_idx + 1}: {e}. "
                    "Attempting paragraph-by-paragraph fallback."
                )
                for idx, p in zip(chunk_indices, chunk):
                    try:
                        results[idx] = await asyncio.to_thread(self._humanize_single_paragraph, p, pass_config)
                    except (RateLimitError, GeminiAPIError) as inner_e:
                        logger.error(
                            f"[{pass_name}] Fatal Gemini error in fallback at paragraph {idx}: {inner_e}"
                        )
                        raise
                    except Exception as inner_e:
                        logger.error(
                            f"[{pass_name}] Fallback failed for paragraph {idx}: {inner_e}. "
                            "Preserving text from previous pass."
                        )
                        results[idx] = p

        # Spawn all batch tasks concurrently
        tasks = [
            process_batch_task(batch_idx, i)
            for batch_idx, i in enumerate(range(0, len(non_empty_paragraphs), self.batch_size))
        ]
        await asyncio.gather(*tasks)

        # Restore blank paragraphs
        for i, p in enumerate(cleaned):
            if not p:
                results[i] = paragraphs[i]

        logger.info(f"[{pass_name}] Pass {pass_number}/1 complete.")
        return results

    # ------------------------------------------------------------------
    # Multi-pass pipeline
    # ------------------------------------------------------------------

    async def humanize_paragraphs(self, paragraphs: List[str]) -> List[str]:
        """
        Humanizes a list of French paragraphs through the single unified pass.

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
            current_paragraphs = await self._run_single_pass(
                current_paragraphs, pass_config, pass_number
            )
            # Small delay between passes if there were multiple passes
            if pass_number < len(PASS_CONFIGS):
                delay = random.uniform(1.0, 2.0)
                logger.debug(
                    f"Inter-pass delay: {delay:.1f}s before pass {pass_number + 1}"
                )
                await asyncio.sleep(delay)

        logger.info("All humanization passes complete.")
        return current_paragraphs

    async def humanize_text(self, text: str) -> str:
        """
        Splits a text document by double-newlines into paragraphs,
        humanizes each through the pipeline, and reconstructs.

        Args:
            text: Full text document in French.

        Returns:
            Reconstructed humanized document text.
        """
        if not text.strip():
            return text

        paragraphs = text.split("\n\n")

        logger.info(
            f"Starting unified humanization: {len(paragraphs)} paragraph(s)."
        )

        humanized_paragraphs = await self.humanize_paragraphs(paragraphs)
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

        print("\nRunning unified humanization pipeline...")
        humanized_text = asyncio.run(humanizer.humanize_text(sample_text))

        print("\n--- HUMANIZED FRENCH TEXT (Unified) ---")
        print(humanized_text)
        print("-----------------------------------------")

    except Exception as err:
        print(f"\n[ERROR] An error occurred while running the demo: {err}")
        sys.exit(1)
