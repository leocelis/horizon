"""End-to-end integration tests for Horizon across real agent frameworks.

Every file here runs against a mocked (or minimal in-process) SDK so the suite
stays network-free (satisfies ``no_external_calls_default``) while still
exercising the exact integration adapters that ship with ``horizon-monitor``:

    - ``openai`` client wrap                    → test_openai_wrap_e2e.py
    - ``anthropic`` client wrap                 → test_anthropic_wrap_e2e.py
    - LangChain ``HorizonCallback``             → test_langchain_callback_e2e.py
    - OpenAI Agents SDK hook                    → test_openai_agents_sdk_e2e.py
    - Raw framework-agnostic string API         → test_raw_strings_e2e.py
    - MCP server (Cursor / Claude Desktop)      → test_mcp_server_e2e.py

Real-SDK equivalents that DO hit the network live under
``horizon/examples/`` and are intentionally excluded from CI.
"""
