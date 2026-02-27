import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.openai_provider import OpenAIProvider
from app.services.ai_router import AIRouter

def test_openai_provider_unavailable_without_key():
    """Test that OpenAI provider is marked unavailable without API key."""
    provider = OpenAIProvider(api_key="")
    assert provider.available == False

def test_openai_provider_available_with_key():
    """Test that OpenAI provider is marked available with API key."""
    provider = OpenAIProvider(api_key="sk-test-key-123")
    assert provider.available == True

@pytest.mark.asyncio
async def test_analyze_image_returns_fallback_without_key():
    """Test that image analysis returns fallback message without API key."""
    provider = OpenAIProvider(api_key="")
    result = await provider.analyze_image("/fake/path.png", "Describe this image")
    assert "not available" in result.lower()
    assert "OPENAI_API_KEY" in result

def test_ai_router_vision_not_available_without_openai():
    """Test that AIRouter reports vision unavailable without OpenAI key."""
    router = AIRouter(deepseek_api_key="sk-deepseek-key", openai_api_key="")
    assert router.vision_available == False

def test_ai_router_vision_available_with_openai():
    """Test that AIRouter reports vision available with OpenAI key."""
    router = AIRouter(deepseek_api_key="sk-deepseek-key", openai_api_key="sk-openai-key")
    assert router.vision_available == True

@pytest.mark.asyncio
async def test_ai_router_uses_deepseek_for_text():
    """Test that AIRouter uses DeepSeek for concept extraction."""
    router = AIRouter(deepseek_api_key="sk-deepseek-key")

    from app.models.ai_models import ConceptExtraction
    mock_result = ConceptExtraction(concepts=["Z-transform"], equations=[])

    with patch.object(router.deepseek, "extract_concepts", new_callable=AsyncMock) as mock:
        mock.return_value = mock_result
        result = await router.extract_concepts("Explain Z-transform")

    mock.assert_called_once()
    assert result.concepts == ["Z-transform"]
