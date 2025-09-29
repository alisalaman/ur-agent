# Phase 7: Testing and Validation

## Overview

This phase implements comprehensive testing and validation for the synthetic representative agent system. It includes unit tests, integration tests, performance tests, and end-to-end validation to ensure the system meets all requirements and performs reliably in production.

## Objectives

- Implement comprehensive test suite covering all components
- Validate end-to-end functionality and workflows
- Ensure performance meets requirements
- Verify evidence-based responses are accurate
- Create automated testing and validation pipeline

## Implementation Tasks

### 7.1 Unit Tests

**File**: `tests/unit/test_transcript_processing.py`

```python
import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
import asyncio

from ai_agent.infrastructure.knowledge.transcript_processor import TranscriptProcessor, ProcessingConfig
from ai_agent.domain.knowledge_models import StakeholderGroup, TranscriptSource

class TestTranscriptProcessor:
    """Test transcript processing functionality."""
    
    @pytest.fixture
    def processor(self):
        config = ProcessingConfig()
        return TranscriptProcessor(config)
    
    @pytest.fixture
    def sample_docx_content(self):
        return """
        Gary Aydon: Welcome to today's discussion about Open Banking governance.
        
        Interviewer: Thank you for joining us. Let's start with your views on commercial sustainability.
        
        Gary Aydon: The costs have been enormous - over £1.5 billion for Open Banking implementation.
        We need sustainable commercial models that provide clear ROI for all participants.
        
        Interviewer: What about governance frameworks?
        
        Gary Aydon: We need symmetrical governance where all parties have balanced rights and obligations.
        The current approach creates a lopsided market where data holders have all the obligations.
        """
    
    def test_speaker_identification(self, processor):
        """Test speaker identification from text."""
        text = "Gary Aydon: This is a test statement."
        speaker = processor._identify_speaker(text)
        assert speaker == "Gary Aydon"
    
    def test_segment_validation(self, processor):
        """Test segment validation logic."""
        # Valid segment
        valid_segment = Mock()
        valid_segment.content = "This is a valid segment with sufficient content length."
        valid_segment.speaker_name = "Gary Aydon"
        assert processor._is_valid_segment(valid_segment) == True
        
        # Invalid segment - too short
        invalid_segment = Mock()
        invalid_segment.content = "Too short"
        invalid_segment.speaker_name = "Gary Aydon"
        assert processor._is_valid_segment(invalid_segment) == False
    
    def test_topic_keyword_extraction(self, processor):
        """Test topic keyword extraction."""
        query = "What are the commercial sustainability concerns?"
        topics = processor._extract_topics_from_query(query)
        assert "commercial sustainability" in topics
    
    @pytest.mark.asyncio
    async def test_transcript_processing(self, processor, sample_docx_content):
        """Test full transcript processing."""
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp_file:
            # Create a mock DOCX file
            with patch('docx.Document') as mock_doc:
                mock_paragraphs = [
                    Mock(text="Gary Aydon: Welcome to today's discussion."),
                    Mock(text="Interviewer: Thank you for joining us."),
                    Mock(text="Gary Aydon: The costs have been enormous.")
                ]
                mock_doc.return_value.paragraphs = mock_paragraphs
                
                # Process transcript
                metadata, segments = await processor.process_transcript_file(
                    Path(tmp_file.name),
                    StakeholderGroup.BANK_REP,
                    TranscriptSource.SANTANDER
                )
                
                assert metadata.stakeholder_group == StakeholderGroup.BANK_REP
                assert len(segments) > 0
                assert all(segment.speaker_name for segment in segments)
```

**File**: `tests/unit/test_synthetic_agents.py`

```python
import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from ai_agent.core.agents.synthetic_representative import SyntheticRepresentativeAgent, PersonaType
from ai_agent.core.agents.personas.bank_rep import BankRepAgent
from ai_agent.core.agents.persona_factory import PersonaAgentFactory

class TestSyntheticAgents:
    """Test synthetic agent functionality."""
    
    @pytest.fixture
    def mock_llm_provider(self):
        provider = Mock()
        provider.generate_response = AsyncMock(return_value=Mock(content="Test response"))
        return provider
    
    @pytest.fixture
    def mock_tool_registry(self):
        registry = Mock()
        registry.execute_tool = AsyncMock(return_value=Mock(
            success=True,
            result={"results": [{"content": "Test evidence", "relevance_score": 0.8}]}
        ))
        return registry
    
    @pytest.fixture
    def bank_rep_agent(self, mock_llm_provider, mock_tool_registry):
        return BankRepAgent(uuid4(), mock_llm_provider, mock_tool_registry)
    
    def test_agent_creation(self, bank_rep_agent):
        """Test agent creation and configuration."""
        assert bank_rep_agent.persona_config.persona_type == PersonaType.BANK_REP
        assert "BankRep" in bank_rep_agent.persona_config.system_prompt
        assert "cost-consciousness" in bank_rep_agent.persona_config.core_perspectives
    
    def test_evidence_query_identification(self, bank_rep_agent):
        """Test evidence query identification."""
        query = "What are the commercial sustainability concerns?"
        evidence_queries = asyncio.run(bank_rep_agent._identify_evidence_queries(query))
        
        assert len(evidence_queries) > 0
        assert any("commercial" in eq.topic for eq in evidence_queries)
    
    @pytest.mark.asyncio
    async def test_query_processing(self, bank_rep_agent):
        """Test query processing with evidence gathering."""
        query = "What are the cost concerns with Open Banking?"
        
        response = await bank_rep_agent.process_query(query)
        
        assert response is not None
        assert len(response) > 0
        # Verify tool was called for evidence gathering
        bank_rep_agent.tool_registry.execute_tool.assert_called()
    
    def test_persona_specific_insights(self, bank_rep_agent):
        """Test persona-specific insight generation."""
        evidence = [
            {"content": "The costs have been enormous - over £1.5 billion"},
            {"content": "We need sustainable commercial models"}
        ]
        
        insights = bank_rep_agent.get_persona_specific_insights(evidence)
        
        assert "cost" in insights.lower()
        assert "commercial" in insights.lower()
    
    @pytest.mark.asyncio
    async def test_agent_factory(self, mock_tool_registry):
        """Test agent factory functionality."""
        factory = PersonaAgentFactory(mock_tool_registry)
        await factory.initialize("anthropic")
        
        # Create all personas
        agents = await factory.create_all_personas()
        
        assert len(agents) == 3
        assert PersonaType.BANK_REP in agents
        assert PersonaType.TRADE_BODY_REP in agents
        assert PersonaType.PAYMENTS_ECOSYSTEM_REP in agents
```

### 7.2 Integration Tests

**File**: `tests/integration/test_end_to_end_workflow.py`

```python
import pytest
import asyncio
from unittest.mock import Mock, patch
from pathlib import Path

from ai_agent.core.agents.persona_service import PersonaAgentService
from ai_agent.core.evaluation.governance_evaluator import GovernanceEvaluator, GovernanceModel
from ai_agent.infrastructure.knowledge.transcript_store import TranscriptStore

class TestEndToEndWorkflow:
    """Test end-to-end workflow functionality."""
    
    @pytest.fixture
    async def setup_system(self):
        """Set up the complete system for testing."""
        # Mock dependencies
        mock_tool_registry = Mock()
        mock_tool_registry.execute_tool = AsyncMock(return_value=Mock(
            success=True,
            result={
                "results": [
                    {
                        "content": "The costs have been enormous - over £1.5 billion",
                        "relevance_score": 0.9,
                        "speaker_name": "Gary Aydon"
                    }
                ],
                "results_count": 1
            }
        ))
        
        # Initialize persona service
        persona_service = PersonaAgentService(mock_tool_registry)
        await persona_service.initialize("anthropic")
        
        # Initialize evaluator
        evaluator = GovernanceEvaluator(persona_service)
        
        return persona_service, evaluator, mock_tool_registry
    
    @pytest.mark.asyncio
    async def test_agent_query_workflow(self, setup_system):
        """Test complete agent query workflow."""
        persona_service, evaluator, mock_tool_registry = await setup_system
        
        # Test single agent query
        response = await persona_service.process_query(
            persona_type=PersonaType.BANK_REP,
            query="What are the cost concerns with Open Banking?",
            context={}
        )
        
        assert response is not None
        assert len(response) > 0
        mock_tool_registry.execute_tool.assert_called()
    
    @pytest.mark.asyncio
    async def test_multi_agent_query_workflow(self, setup_system):
        """Test multi-agent query workflow."""
        persona_service, evaluator, mock_tool_registry = await setup_system
        
        # Test multi-agent query
        responses = await persona_service.process_query_all_personas(
            query="What are the governance concerns with new Smart Data schemes?",
            context={}
        )
        
        assert len(responses) == 3
        assert PersonaType.BANK_REP in responses
        assert PersonaType.TRADE_BODY_REP in responses
        assert PersonaType.PAYMENTS_ECOSYSTEM_REP in responses
        
        # Verify all responses are evidence-based
        for persona_type, response in responses.items():
            assert response is not None
            assert len(response) > 0
    
    @pytest.mark.asyncio
    async def test_governance_evaluation_workflow(self, setup_system):
        """Test complete governance evaluation workflow."""
        persona_service, evaluator, mock_tool_registry = await setup_system
        
        # Create test governance model
        model = GovernanceModel(
            name="Test Governance Model",
            description="A test governance model for evaluation",
            model_type="Centralized",
            key_features=["Centralized decision making", "Single authority"],
            proposed_by="Test Organization"
        )
        
        # Evaluate model
        evaluation = await evaluator.evaluate_governance_model(model)
        
        assert evaluation is not None
        assert evaluation.overall_score > 0
        assert len(evaluation.factor_scores) == 6
        assert evaluation.evaluation_status == "completed"
        
        # Verify all factors were evaluated
        for factor in CriticalSuccessFactor:
            assert factor in evaluation.factor_scores
            assert evaluation.factor_scores[factor].score >= 1
            assert evaluation.factor_scores[factor].score <= 5
    
    @pytest.mark.asyncio
    async def test_evidence_based_responses(self, setup_system):
        """Test that responses are evidence-based."""
        persona_service, evaluator, mock_tool_registry = await setup_system
        
        # Query that should trigger evidence gathering
        response = await persona_service.process_query(
            persona_type=PersonaType.BANK_REP,
            query="What specific costs were mentioned in the transcripts?",
            context={}
        )
        
        # Verify tool was called for evidence
        mock_tool_registry.execute_tool.assert_called_with(
            tool_name="get_stakeholder_views",
            arguments={
                "topic": "cost",
                "stakeholder_group": "BankRep",
                "limit": 10,
                "min_relevance_score": 0.3
            }
        )
        
        # Verify response contains evidence references
        assert "evidence" in response.lower() or "transcript" in response.lower()
```

### 7.3 Performance Tests

**File**: `tests/performance/test_system_performance.py`

```python
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
import psutil
import os

from ai_agent.core.agents.persona_service import PersonaAgentService
from ai_agent.core.evaluation.governance_evaluator import GovernanceEvaluator

class TestSystemPerformance:
    """Test system performance and scalability."""
    
    @pytest.fixture
    async def performance_setup(self):
        """Set up system for performance testing."""
        # Mock tool registry with realistic response times
        mock_tool_registry = Mock()
        mock_tool_registry.execute_tool = AsyncMock(return_value=Mock(
            success=True,
            result={
                "results": [{"content": "Test evidence", "relevance_score": 0.8}],
                "results_count": 1
            }
        ))
        
        persona_service = PersonaAgentService(mock_tool_registry)
        await persona_service.initialize("anthropic")
        
        evaluator = GovernanceEvaluator(persona_service)
        
        return persona_service, evaluator
    
    @pytest.mark.asyncio
    async def test_query_response_time(self, performance_setup):
        """Test query response time meets requirements."""
        persona_service, evaluator = performance_setup
        
        query = "What are the commercial sustainability concerns?"
        
        start_time = time.time()
        response = await persona_service.process_query(
            persona_type=PersonaType.BANK_REP,
            query=query
        )
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # Should respond within 2 seconds
        assert response_time < 2.0
        assert response is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_queries(self, performance_setup):
        """Test system handles concurrent queries."""
        persona_service, evaluator = performance_setup
        
        queries = [
            "What are the cost concerns?",
            "What about governance frameworks?",
            "How about interoperability?",
            "What are the technical challenges?",
            "What about commercial viability?"
        ]
        
        start_time = time.time()
        
        # Execute queries concurrently
        tasks = []
        for query in queries:
            task = persona_service.process_query(
                persona_type=PersonaType.BANK_REP,
                query=query
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All queries should complete
        assert len(responses) == len(queries)
        assert all(response is not None for response in responses)
        
        # Should handle concurrent queries efficiently
        assert total_time < 5.0  # 5 queries in under 5 seconds
    
    @pytest.mark.asyncio
    async def test_evaluation_performance(self, performance_setup):
        """Test governance evaluation performance."""
        persona_service, evaluator = performance_setup
        
        model = GovernanceModel(
            name="Performance Test Model",
            description="A model for performance testing",
            model_type="Test",
            key_features=["Feature 1", "Feature 2"],
            proposed_by="Test Org"
        )
        
        start_time = time.time()
        evaluation = await evaluator.evaluate_governance_model(model)
        end_time = time.time()
        
        evaluation_time = end_time - start_time
        
        # Should complete evaluation within 30 seconds
        assert evaluation_time < 30.0
        assert evaluation.overall_score > 0
        assert evaluation.evaluation_status == "completed"
    
    @pytest.mark.asyncio
    async def test_memory_usage(self, performance_setup):
        """Test memory usage during operation."""
        persona_service, evaluator = performance_setup
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform multiple operations
        for i in range(10):
            await persona_service.process_query(
                persona_type=PersonaType.BANK_REP,
                query=f"Test query {i}"
            )
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 100MB)
        assert memory_increase < 100
    
    @pytest.mark.asyncio
    async def test_evidence_cache_performance(self, performance_setup):
        """Test evidence caching performance."""
        persona_service, evaluator = performance_setup
        
        query = "What are the cost concerns?"
        
        # First query (cache miss)
        start_time = time.time()
        response1 = await persona_service.process_query(
            persona_type=PersonaType.BANK_REP,
            query=query
        )
        first_query_time = time.time() - start_time
        
        # Second query (cache hit)
        start_time = time.time()
        response2 = await persona_service.process_query(
            persona_type=PersonaType.BANK_REP,
            query=query
        )
        second_query_time = time.time() - start_time
        
        # Second query should be faster due to caching
        assert second_query_time < first_query_time
        assert response1 == response2
```

### 7.4 Validation Tests

**File**: `tests/validation/test_evidence_accuracy.py`

```python
import pytest
from unittest.mock import Mock, AsyncMock

from ai_agent.core.agents.persona_service import PersonaAgentService
from ai_agent.domain.knowledge_models import StakeholderGroup

class TestEvidenceAccuracy:
    """Test evidence accuracy and validation."""
    
    @pytest.fixture
    async def validation_setup(self):
        """Set up system for validation testing."""
        # Mock tool registry with realistic evidence
        mock_tool_registry = Mock()
        mock_tool_registry.execute_tool = AsyncMock(return_value=Mock(
            success=True,
            result={
                "results": [
                    {
                        "content": "The costs have been enormous - over £1.5 billion for Open Banking implementation",
                        "relevance_score": 0.9,
                        "speaker_name": "Gary Aydon",
                        "stakeholder_group": "BankRep"
                    },
                    {
                        "content": "We need sustainable commercial models that provide clear ROI",
                        "relevance_score": 0.8,
                        "speaker_name": "Gary Aydon",
                        "stakeholder_group": "BankRep"
                    }
                ],
                "results_count": 2
            }
        ))
        
        persona_service = PersonaAgentService(mock_tool_registry)
        await persona_service.initialize("anthropic")
        
        return persona_service, mock_tool_registry
    
    @pytest.mark.asyncio
    async def test_evidence_citation_accuracy(self, validation_setup):
        """Test that evidence citations are accurate."""
        persona_service, mock_tool_registry = validation_setup
        
        response = await persona_service.process_query(
            persona_type=PersonaType.BANK_REP,
            query="What specific costs were mentioned?",
            context={}
        )
        
        # Verify tool was called with correct parameters
        mock_tool_registry.execute_tool.assert_called_with(
            tool_name="get_stakeholder_views",
            arguments={
                "topic": "cost",
                "stakeholder_group": "BankRep",
                "limit": 10,
                "min_relevance_score": 0.3
            }
        )
        
        # Verify response contains evidence references
        assert "£1.5 billion" in response or "cost" in response.lower()
    
    @pytest.mark.asyncio
    async def test_persona_perspective_consistency(self, validation_setup):
        """Test that persona perspectives are consistent."""
        persona_service, mock_tool_registry = validation_setup
        
        # Test BankRep perspective
        bank_response = await persona_service.process_query(
            persona_type=PersonaType.BANK_REP,
            query="What are your views on governance?",
            context={}
        )
        
        # Test TradeBodyRep perspective
        trade_response = await persona_service.process_query(
            persona_type=PersonaType.TRADE_BODY_REP,
            query="What are your views on governance?",
            context={}
        )
        
        # Responses should be different (different personas)
        assert bank_response != trade_response
        
        # BankRep should focus on cost and liability
        assert "cost" in bank_response.lower() or "liability" in bank_response.lower()
        
        # TradeBodyRep should focus on business case
        assert "business" in trade_response.lower() or "commercial" in trade_response.lower()
    
    @pytest.mark.asyncio
    async def test_evidence_relevance_scoring(self, validation_setup):
        """Test evidence relevance scoring."""
        persona_service, mock_tool_registry = validation_setup
        
        # Mock different relevance scores
        mock_tool_registry.execute_tool.return_value = Mock(
            success=True,
            result={
                "results": [
                    {
                        "content": "Highly relevant content about costs",
                        "relevance_score": 0.9,
                        "speaker_name": "Gary Aydon"
                    },
                    {
                        "content": "Less relevant content",
                        "relevance_score": 0.3,
                        "speaker_name": "Unknown"
                    }
                ],
                "results_count": 2
            }
        )
        
        response = await persona_service.process_query(
            persona_type=PersonaType.BANK_REP,
            query="What are the cost concerns?",
            context={}
        )
        
        # Response should prioritize high-relevance evidence
        assert "costs" in response.lower()
    
    @pytest.mark.asyncio
    async def test_evidence_source_tracking(self, validation_setup):
        """Test that evidence sources are properly tracked."""
        persona_service, mock_tool_registry = validation_setup
        
        response = await persona_service.process_query(
            persona_type=PersonaType.BANK_REP,
            query="What evidence supports your views?",
            context={}
        )
        
        # Verify tool was called to gather evidence
        assert mock_tool_registry.execute_tool.called
        
        # Response should reference evidence sources
        assert "evidence" in response.lower() or "transcript" in response.lower()
```

### 7.5 Test Configuration

**File**: `pytest.ini`

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --cov=src/ai_agent
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance tests
    validation: Validation tests
    slow: Slow running tests
asyncio_mode = auto
```

**File**: `tests/conftest.py`

```python
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from ai_agent.core.agents.synthetic_representative import PersonaType

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider for testing."""
    provider = Mock()
    provider.generate_response = AsyncMock(return_value=Mock(content="Test response"))
    return provider

@pytest.fixture
def mock_tool_registry():
    """Mock tool registry for testing."""
    registry = Mock()
    registry.execute_tool = AsyncMock(return_value=Mock(
        success=True,
        result={"results": [], "results_count": 0}
    ))
    return registry

@pytest.fixture
def sample_evidence():
    """Sample evidence data for testing."""
    return [
        {
            "content": "The costs have been enormous - over £1.5 billion",
            "relevance_score": 0.9,
            "speaker_name": "Gary Aydon",
            "stakeholder_group": "BankRep"
        },
        {
            "content": "We need sustainable commercial models",
            "relevance_score": 0.8,
            "speaker_name": "Gary Aydon",
            "stakeholder_group": "BankRep"
        }
    ]
```

## Testing Strategy

### Test Categories

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test component interactions
3. **Performance Tests**: Test system performance and scalability
4. **Validation Tests**: Test accuracy and evidence-based responses
5. **End-to-End Tests**: Test complete workflows

### Test Coverage Requirements

- **Code Coverage**: Minimum 80% line coverage
- **Branch Coverage**: Minimum 70% branch coverage
- **Function Coverage**: 100% function coverage
- **Critical Path Coverage**: 100% coverage of critical paths

### Performance Requirements

- **Query Response Time**: <2 seconds for typical queries
- **Evaluation Time**: <30 seconds for complete evaluations
- **Concurrent Queries**: Support 10+ concurrent queries
- **Memory Usage**: <100MB increase during operation
- **Cache Performance**: 50%+ improvement with caching

### Validation Requirements

- **Evidence Accuracy**: 95%+ accuracy in evidence citations
- **Persona Consistency**: Consistent persona perspectives
- **Response Quality**: Evidence-based responses with proper citations
- **Tool Integration**: Proper MCP tool usage

## Success Criteria

1. **Test Coverage**: 80%+ code coverage achieved
2. **Performance**: All performance requirements met
3. **Accuracy**: Evidence accuracy requirements met
4. **Reliability**: 99%+ test pass rate
5. **Automation**: Full CI/CD pipeline with automated testing

## Dependencies

This phase depends on:
- All previous phases (1-6)
- pytest and testing frameworks
- Performance monitoring tools
- Mock and test data

## Next Steps

After completing testing and validation:
- Deploy to production
- Monitor system performance
- Gather user feedback
- Iterate and improve

The testing and validation phase ensures the system is production-ready and meets all requirements before deployment.
