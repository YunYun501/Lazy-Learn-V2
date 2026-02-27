import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.deepseek_provider import DeepSeekProvider
from app.models.ai_models import ConceptExtraction, ClassifiedMatch, PracticeProblems

API_KEY = "test-key"


def make_mock_response(content: str):
    """Create a mock httpx response with the given content."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    return mock_response


@pytest.mark.asyncio
async def test_concept_extraction():
    """Test that concept extraction parses AI response correctly."""
    provider = DeepSeekProvider(api_key=API_KEY)
    mock_content = json.dumps({
        "concepts": ["Z-transform", "discrete transfer function"],
        "equations": ["Y(z) = az/(z-b)"]
    })

    with patch.object(provider, "_call_with_retry", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = {"choices": [{"message": {"content": mock_content}}]}
        result = await provider.extract_concepts("Explain how Y(z) = 0.5z/(z-0.8) works")

    assert isinstance(result, ConceptExtraction)
    assert "Z-transform" in result.concepts
    assert "discrete transfer function" in result.concepts
    assert len(result.equations) > 0


@pytest.mark.asyncio
async def test_classification():
    """Test that classification returns EXPLAINS/USES correctly."""
    provider = DeepSeekProvider(api_key=API_KEY)
    mock_content = json.dumps({
        "classification": "EXPLAINS",
        "confidence": 0.9,
        "reason": "Chapter derives and defines the Z-transform"
    })

    descriptions = [{"source": "textbook.pdf", "chapter": "Chapter 3", "content": "This chapter explains Z-transform..."}]

    with patch.object(provider, "_call_with_retry", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = {"choices": [{"message": {"content": mock_content}}]}
        results = await provider.classify_matches(descriptions, "Z-transform")

    assert len(results) == 1
    assert results[0].classification == "EXPLAINS"
    assert results[0].confidence == 0.9
    assert results[0].source == "textbook.pdf"


@pytest.mark.asyncio
async def test_retry_on_empty_response():
    """Test that retry logic triggers when API returns empty content."""
    provider = DeepSeekProvider(api_key=API_KEY)

    call_count = 0
    async def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        if call_count == 1:
            # First call returns empty content
            mock_resp.json.return_value = {"choices": [{"message": {"content": ""}}]}
        else:
            # Second call returns valid content
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": json.dumps({"concepts": ["Z-transform"], "equations": []})}}]
            }
        return mock_resp

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = mock_post
        mock_client_class.return_value = mock_client

        # Patch asyncio.sleep to avoid actual delays in tests
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await provider.extract_concepts("test query")

    assert call_count == 2  # Retried once
    assert "Z-transform" in result.concepts


@pytest.mark.asyncio
async def test_practice_problems_always_have_disclaimer():
    """Test that all practice problems include the warning disclaimer."""
    provider = DeepSeekProvider(api_key=API_KEY)
    mock_content = json.dumps({
        "problems": [
            {"question": "Find the Z-transform of x[n] = a^n u[n]", "solution": "X(z) = z/(z-a)"},
            {"question": "Determine stability of H(z) = 1/(z-0.5)", "solution": "Stable, pole inside unit circle"},
        ]
    })

    with patch.object(provider, "_call_with_retry", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = {"choices": [{"message": {"content": mock_content}}]}
        result = await provider.generate_practice_problems("Z-transform content", "Z-transform", count=2)

    assert isinstance(result, PracticeProblems)
    assert len(result.problems) == 2
    for problem in result.problems:
        assert problem.warning_disclaimer == "AI-generated solutions may contain errors. Verify independently."
        assert problem.question
        assert problem.solution
