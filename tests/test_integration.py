import asyncio
import json
import os
import subprocess
import sys
import unittest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class IntegrationTests(unittest.TestCase):
    def test_cli_finds_current_process(self):
        output = subprocess.check_output([sys.executable, '-m', 'findher.cli', 'processes', '--pid', str(os.getpid())], text=True)
        self.assertEqual(json.loads(output)[0]['pid'], os.getpid())

    def test_mcp_lists_and_calls_tools(self):
        async def check():
            params = StdioServerParameters(command=sys.executable, args=['-m', 'findher.cli', 'mcp'])
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    self.assertEqual({t.name for t in tools.tools}, {'find_processes', 'find_windows', 'launch_application'})
                    result = await session.call_tool('find_processes', {'pid': os.getpid()})
                    self.assertFalse(result.isError)
                    self.assertIn(str(os.getpid()), str(result.content))
        asyncio.run(check())
