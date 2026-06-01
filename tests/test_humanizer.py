"""
Unit tests for the FrenchHumanizer service.
"""

import unittest
from unittest.mock import patch, MagicMock

# Import the humanizer classes
from backend.humanizer import (
    FrenchHumanizer,
    HumanizerError,
    GeminiAPIError,
    RateLimitError,
    PASS_CONFIGS,
)


class TestFrenchHumanizer(unittest.IsolatedAsyncioTestCase):
    """Test cases for the FrenchHumanizer class."""

    def setUp(self):
        """Set up standard test variables."""
        self.api_key = "test-gemini-api-key"
        self.humanizer = FrenchHumanizer(api_key=self.api_key, batch_size=2)

    def test_init_raises_value_error_without_key(self):
        """Ensure ValueError is raised if api_key is missing."""
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                FrenchHumanizer(api_key=None)

    def test_init_resolves_key_from_env(self):
        """Ensure constructor resolves key from environment variable."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": "env-key"}):
            humanizer = FrenchHumanizer()
            self.assertEqual(humanizer.api_key, "env-key")

    @patch("requests.post")
    async def test_successful_batch_humanization(self, mock_post):
        """Test successful batch rephrasing with matching paragraph count."""
        # Mock successful API response containing structured output
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": '{"paragraphs": ["Paragraphe un réécrit", "Paragraphe deux réécrit"]}'
                            }
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        input_paragraphs = ["Paragraphe un original", "Paragraphe deux original"]
        result = await self.humanizer.humanize_paragraphs(input_paragraphs)

        self.assertEqual(result, ["Paragraphe un réécrit", "Paragraphe deux réécrit"])
        mock_post.assert_called_once()

    @patch("requests.post")
    async def test_markdown_code_block_parsing(self, mock_post):
        """Test that json wrapped in markdown code blocks is correctly parsed."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": '```json\n{"paragraphs": ["Humanized"]}\n```'
                            }
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        result = await self.humanizer.humanize_paragraphs(["Original"])
        self.assertEqual(result, ["Humanized"])

    @patch("requests.post")
    async def test_batch_mismatch_fallback(self, mock_post):
        """Test sequential fallback if batch output length is mismatched."""
        # 1. First call returns mismatch (e.g. returns 1 paragraph instead of 2)
        mock_mismatch = MagicMock()
        mock_mismatch.status_code = 200
        mock_mismatch.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": '{"paragraphs": ["Seulement un"]}'
                            }
                        ]
                    }
                }
            ]
        }

        # 2. Sequential fallback calls (each with batch size 1)
        mock_single_1 = MagicMock()
        mock_single_1.status_code = 200
        mock_single_1.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": '{"paragraphs": ["Paragraphe un réécrit"]}'
                            }
                        ]
                    }
                }
            ]
        }

        mock_single_2 = MagicMock()
        mock_single_2.status_code = 200
        mock_single_2.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": '{"paragraphs": ["Paragraphe deux réécrit"]}'
                            }
                        ]
                    }
                }
            ]
        }

        # Side effect to handle the sequential requests
        mock_post.side_effect = [mock_mismatch, mock_single_1, mock_single_2]

        input_paragraphs = ["Original un", "Original deux"]
        result = await self.humanizer.humanize_paragraphs(input_paragraphs)

        self.assertEqual(result, ["Paragraphe un réécrit", "Paragraphe deux réécrit"])
        self.assertEqual(mock_post.call_count, 3)

    @patch("requests.post")
    async def test_rate_limit_retry_success(self, mock_post):
        """Test retrying upon receiving HTTP 429 and eventually succeeding."""
        # Mock 429 response
        mock_rate_limit = MagicMock()
        mock_rate_limit.status_code = 429
        mock_rate_limit.text = "Rate Limit Exceeded"

        # Mock successful response
        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": '{"paragraphs": ["Succès"]}'
                            }
                        ]
                    }
                }
            ]
        }

        mock_post.side_effect = [mock_rate_limit, mock_success]

        # Patch time.sleep to run instantly
        with patch("time.sleep") as mock_sleep:
            humanizer = FrenchHumanizer(api_key=self.api_key, batch_size=1, max_retries=2, backoff_factor=2)
            result = await humanizer.humanize_paragraphs(["Original"])

            self.assertEqual(result, ["Succès"])
            self.assertEqual(mock_post.call_count, 2)
            mock_sleep.assert_called_once()

    @patch("requests.post")
    def test_rate_limit_exhausted(self, mock_post):
        """Test that RateLimitError is raised when max retries are exceeded for HTTP 429."""
        mock_rate_limit = MagicMock()
        mock_rate_limit.status_code = 429
        mock_rate_limit.text = "Rate Limit Exceeded"
        mock_post.return_value = mock_rate_limit

        with patch("time.sleep"):
            humanizer = FrenchHumanizer(api_key=self.api_key, batch_size=1, max_retries=1)
            with self.assertRaises(RateLimitError):
                humanizer._humanize_chunk(["Original"], PASS_CONFIGS[0])

    @patch("requests.post")
    async def test_empty_paragraph_preservation(self, mock_post):
        """Test empty paragraphs are preserved and not sent to API."""
        input_paragraphs = ["Original un", "", "Original deux", "   ", "Original trois"]
        
        # We only mock response for 3 items (since empty paragraphs are filtered out)
        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": '{"paragraphs": ["Réécrit un", "Réécrit deux", "Réécrit trois"]}'
                            }
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_success

        humanizer = FrenchHumanizer(api_key=self.api_key, batch_size=5)
        result = await humanizer.humanize_paragraphs(input_paragraphs)
        
        # Mappings should align perfectly, preserving the index of empty paragraphs
        self.assertEqual(result, ["Réécrit un", "", "Réécrit deux", "   ", "Réécrit trois"])
        
        # The API call should have received only the 3 non-empty paragraphs
        mock_post.assert_called_once()
        called_args, called_kwargs = mock_post.call_args
        sent_payload = called_kwargs["json"]
        sent_prompt = sent_payload["contents"][0]["parts"][0]["text"]
        self.assertIn("Original un", sent_prompt)
        self.assertIn("Original deux", sent_prompt)
        self.assertIn("Original trois", sent_prompt)
        self.assertNotIn("   ", sent_prompt)


if __name__ == "__main__":
    unittest.main()
