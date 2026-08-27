import json

import pytest

from app.ai.tools import TOOL_DEFINITIONS, execute_tool, search_knowledge_base
from app.services.knowledge import create_knowledge_base, ingest_document


@pytest.fixture
def knowledge_base(db_session, test_agent):
    return create_knowledge_base(
        db=db_session,
        agent_id=test_agent.id,
        name="Acme Clinic Knowledge",
    )


@pytest.fixture
def pricing_document(db_session, knowledge_base):
    return ingest_document(
        db=db_session,
        knowledge_base=knowledge_base,
        filename="pricing.txt",
        content=(
            b"consultation cost fifty dollars per session "
            b"dental cleaning eighty dollars"
        ),
    )


class TestToolDefinition:
    def test_tool_is_registered(self):
        names = [
            tool["function"]["name"]
            for tool in TOOL_DEFINITIONS
        ]

        assert "search_knowledge_base" in names

    def test_tool_defines_query_parameter(self):
        tool = next(
            tool
            for tool in TOOL_DEFINITIONS
            if tool["function"]["name"] == "search_knowledge_base"
        )

        parameters = tool["function"]["parameters"]
        assert "query" in parameters["properties"]
        assert parameters["required"] == ["query"]


@pytest.mark.asyncio
class TestSearchKnowledgeBaseTool:
    async def test_returns_relevant_documents(
        self, db_session, test_agent, pricing_document
    ):
        result = await search_knowledge_base(
            db=db_session,
            agent_id=test_agent.id,
            query="consultation cost",
        )

        assert result["found"] is True
        assert "fifty dollars" in result["results"][0]["content"]
        assert result["results"][0]["score"] > 0

    async def test_guards_against_hallucination(
        self, db_session, test_agent, pricing_document
    ):
        result = await search_knowledge_base(
            db=db_session,
            agent_id=test_agent.id,
            query="violet walrus kangaroo parade",
        )

        assert result["found"] is False
        assert "do not guess or invent" in result["message"].lower()

    async def test_handles_agent_without_knowledge_base(self, db_session, test_agent):
        result = await search_knowledge_base(
            db=db_session,
            agent_id=test_agent.id,
            query="consultation cost",
        )

        assert result["found"] is False
        assert "no knowledge base" in result["message"].lower()


@pytest.mark.asyncio
class TestExecuteSearchTool:
    async def test_executes_search_tool(
        self, db_session, test_agent, pricing_document
    ):
        result = await execute_tool(
            db=db_session,
            agent_id=test_agent.id,
            call_id=None,
            tool_name="search_knowledge_base",
            arguments=json.dumps({"query": "consultation cost"}),
        )

        data = json.loads(result)
        assert data["found"] is True
        assert data["results"][0]["score"] > 0

    async def test_executes_search_tool_and_finds_nothing(
        self, db_session, test_agent, pricing_document
    ):
        result = await execute_tool(
            db=db_session,
            agent_id=test_agent.id,
            call_id=None,
            tool_name="search_knowledge_base",
            arguments=json.dumps({"query": "walrus kangaroo"}),
        )

        data = json.loads(result)
        assert data["found"] is False
        assert "do not guess or invent" in data["message"].lower()

    async def test_returns_error_for_missing_query(
        self, db_session, test_agent
    ):
        result = await execute_tool(
            db=db_session,
            agent_id=test_agent.id,
            call_id=None,
            tool_name="search_knowledge_base",
            arguments=json.dumps({}),
        )

        data = json.loads(result)
        assert "error" in data