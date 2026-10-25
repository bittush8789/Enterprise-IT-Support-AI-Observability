from unittest.mock import MagicMock, patch
import pytest
from langchain_core.documents import Document

from app.rag.state import AgentState, RouteDecision, EvidenceGrade
from app.rag.workflow import (
    add_trace,
    route_after_router,
    after_kb,
    after_web,
    insufficient,
    direct_answer,
    route_question,
    retrieve_kb,
    grade_kb,
    rewrite_query,
)


class TestWorkflowDecisionUnits:
    """
    Unit tests for isolated LangGraph workflow nodes and conditional branches.
    All external LLM calls and retrievers are mocked.
    """

    def test_add_trace_appends_messages(self):
        state: AgentState = {"trace": ["Step 1"]}
        new_trace = add_trace(state, "Step 2")
        assert new_trace == ["Step 1", "Step 2"]

    def test_route_after_router_branching(self):
        assert route_after_router({"source_used": "kb"}) == "retrieve_kb"
        assert route_after_router({"source_used": "direct"}) == "direct_answer"

    def test_after_kb_branching(self):
        assert after_kb({"kb_grade": "good"}) == "generate_from_kb"
        assert after_kb({"kb_grade": "weak"}) == "search_web"

    def test_after_web_branching_and_retry_guard(self):
        # Good web evidence -> generate
        assert after_web({"web_grade": "good", "retry_count": 0}) == "generate_from_web"

        # Weak web evidence, retry available -> rewrite query
        assert after_web({"web_grade": "weak", "retry_count": 0}) == "rewrite_query"

        # Weak web evidence, max retries reached (retry guard) -> insufficient
        assert after_web({"web_grade": "weak", "retry_count": 1}) == "insufficient"

    def test_insufficient_returns_standard_message(self):
        state: AgentState = {"trace": []}
        res = insufficient(state)
        assert "couldn't find enough reliable evidence" in res["answer"].lower()
        assert res["source_used"] == "insufficient_evidence"
        assert len(res["trace"]) == 1

    @patch("app.rag.workflow.llm")
    def test_route_question_kb(self, mock_llm_fn):
        mock_router = MagicMock()
        mock_router.invoke.return_value = RouteDecision(route="kb")
        mock_llm_fn.return_value.with_structured_output.return_value = mock_router

        state: AgentState = {"question": "How do I reset password?", "trace": []}
        result = route_question(state)

        assert result["source_used"] == "kb"
        assert any("Router → KB" in t for t in result["trace"])

    @patch("app.rag.workflow.llm")
    def test_route_question_direct(self, mock_llm_fn):
        mock_router = MagicMock()
        mock_router.invoke.return_value = RouteDecision(route="direct")
        mock_llm_fn.return_value.with_structured_output.return_value = mock_router

        state: AgentState = {"question": "Hello good morning!", "trace": []}
        result = route_question(state)

        assert result["source_used"] == "direct"
        assert any("Router → DIRECT" in t for t in result["trace"])


    @patch("app.rag.workflow.get_retriever")
    def test_retrieve_kb(self, mock_retriever_fn):
        mock_retriever = MagicMock()
        mock_docs = [Document(page_content="VPN info", metadata={"source": "handbook.md"})]
        mock_retriever.invoke.return_value = mock_docs
        mock_retriever_fn.return_value = mock_retriever

        state: AgentState = {"current_query": "VPN access", "trace": []}
        result = retrieve_kb(state)

        assert result["kb_docs"] == mock_docs
        assert any("1 chunks" in t for t in result["trace"])

    @patch("app.rag.workflow.llm")
    def test_grade_kb(self, mock_llm_fn):
        mock_grader = MagicMock()
        mock_grader.invoke.return_value = EvidenceGrade(grade="good")
        mock_llm_fn.return_value.with_structured_output.return_value = mock_grader

        state: AgentState = {
            "question": "How to connect VPN?",
            "kb_docs": [Document(page_content="Use NovaSecure client", metadata={"source": "vpn.md"})],
            "trace": [],
        }
        result = grade_kb(state)

        assert result["kb_grade"] == "good"
        assert any("GOOD" in t for t in result["trace"])

    @patch("app.rag.workflow.llm")
    def test_rewrite_query(self, mock_llm_fn):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "NovaRetail VPN troubleshooting gateway connection error"
        mock_llm_fn.return_value = mock_llm

        state: AgentState = {
            "question": "my vpn is broken",
            "retry_count": 0,
            "trace": [],
        }
        result = rewrite_query(state)

        assert result["current_query"] == "NovaRetail VPN troubleshooting gateway connection error"
        assert result["retry_count"] == 1
        assert any("Query rewrite" in t for t in result["trace"])
