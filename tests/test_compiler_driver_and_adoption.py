"""
Tests for Ecstasy Drop-in Compiler Driver (ecstasy-cc / ecstasy-c++),
GitHub Action CI runner, and 1-click AI Agent (Cursor/Claude) Integrations.
"""

import sys
import os
import json
import subprocess
import tempfile
from pathlib import Path
import pytest

from engine.compiler_driver import EcstasyCompilerDriver
from server.agent_integrator import AgentIntegrator, configure_agent_mcp
from scripts.github_action_runner import discover_targets, run_action_audit


class TestEcstasyCompilerDriver:
    """Test suite for ecstasy-cc / ecstasy-c++ transparent compiler driver."""

    def test_argument_parsing(self):
        driver = EcstasyCompilerDriver(is_cxx=False)
        argv = [
            "-O2", "-Wall", "-I/usr/include",
            "--ecstasy-verbose", "--ecstasy-strict",
            "test.c", "-o", "test.o", "-c"
        ]
        filtered_args, opts, sources = driver.parse_arguments(argv)
        assert opts["verbose"] is True
        assert opts["strict"] is True
        assert opts["disable"] is False
        assert "--ecstasy-verbose" not in filtered_args
        assert "--ecstasy-strict" not in filtered_args
        assert "-O2" in filtered_args

    def test_version_query_passthrough(self):
        driver = EcstasyCompilerDriver(is_cxx=False)
        # Should succeed and return code 0
        rc = driver.run(["--version"])
        assert rc == 0

    def test_single_file_c_compilation_and_execution(self, tmp_path):
        c_file = tmp_path / "hello.c"
        out_bin = tmp_path / "hello"
        c_file.write_text("""
        #include <stdio.h>
        int main() {
            printf("Ecstasy Driver Test Passed!\\n");
            return 0;
        }
        """, encoding="utf-8")

        driver = EcstasyCompilerDriver(is_cxx=False)
        rc = driver.run([str(c_file), "-o", str(out_bin)])
        assert rc == 0
        assert out_bin.exists()

        # Execute compiled binary
        res = subprocess.run([str(out_bin)], capture_output=True, text=True)
        assert res.returncode == 0
        assert "Ecstasy Driver Test Passed!" in res.stdout

    def test_multifile_object_compilation_and_link(self, tmp_path):
        m1 = tmp_path / "m1.c"
        m2 = tmp_path / "m2.c"
        obj1 = tmp_path / "m1.o"
        obj2 = tmp_path / "m2.o"
        app = tmp_path / "app"

        m1.write_text("int get_factor() { return 7; }\n", encoding="utf-8")
        m2.write_text("""
        int get_factor();
        int main() {
            return get_factor() == 7 ? 0 : 1;
        }
        """, encoding="utf-8")

        driver = EcstasyCompilerDriver(is_cxx=False)
        # 1. Compile objects with -c
        assert driver.run(["-c", str(m1), "-o", str(obj1)]) == 0
        assert driver.run(["-c", str(m2), "-o", str(obj2)]) == 0
        assert obj1.exists()
        assert obj2.exists()

        # 2. Link objects
        assert driver.run([str(obj1), str(obj2), "-o", str(app)]) == 0
        assert app.exists()

        # 3. Execute
        exec_res = subprocess.run([str(app)])
        assert exec_res.returncode == 0


class TestAgentIntegrator:
    """Test suite for 1-click Cursor and Claude Desktop MCP configurations."""

    def test_generate_server_config(self, tmp_path):
        integrator = AgentIntegrator(project_root=tmp_path)
        cfg = integrator.generate_server_config()
        assert "command" in cfg
        assert "args" in cfg
        assert "mcp_server.py" in cfg["args"][0]
        assert "PYTHONPATH" in cfg["env"]

    def test_install_cursor_config(self, tmp_path):
        integrator = AgentIntegrator(project_root=tmp_path)
        path = integrator.install_cursor(global_install=False)
        assert Path(path).exists()
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        assert "mcpServers" in data
        assert "ecstasy" in data["mcpServers"]
        assert "mcp_server.py" in data["mcpServers"]["ecstasy"]["args"][0]

    def test_configure_agent_mcp_helper(self, tmp_path, monkeypatch):
        monkeypatch.setattr("server.agent_integrator.AgentIntegrator.install_cursor", lambda self, global_install: str(tmp_path / "mcp.json"))
        res = configure_agent_mcp(target="cursor")
        assert res["status"] == "SUCCESS"
        assert res["target"] == "cursor"

    def test_print_only_config(self):
        res = configure_agent_mcp(print_only=True)
        assert res["status"] == "SUCCESS"
        assert "config" in res


class TestGitHubActionRunner:
    """Test suite for GitHub Action CI runner."""

    def test_discover_targets(self, tmp_path):
        (tmp_path / "test1.c").write_text("int f() { return 0; }")
        (tmp_path / "test2.ll").write_text("define i32 @f() { ret i32 0 }")
        (tmp_path / "ignored.txt").write_text("not source")

        targets = discover_targets(tmp_path)
        assert len(targets) == 2
        names = [t.name for t in targets]
        assert "test1.c" in names
        assert "test2.ll" in names

    def test_run_action_audit(self, tmp_path):
        # Create safe C file
        safe_c = tmp_path / "safe.c"
        safe_c.write_text("""
        int add(int a, int b) {
            return a + b;
        }
        """)

        sarif_out = tmp_path / "audit.sarif"
        cbom_out = tmp_path / "cbom.json"
        summary_out = tmp_path / "summary.md"

        rc = run_action_audit(
            target_str=str(tmp_path),
            sarif_output=str(sarif_out),
            cbom_output=str(cbom_out),
            fail_on_exploit=True,
            pr_comment=True,
            step_summary_path=str(summary_out)
        )

        assert rc == 0
        assert sarif_out.exists()
        assert cbom_out.exists()
        assert summary_out.exists()

        summary_content = summary_out.read_text(encoding="utf-8")
        assert "Ecstasy Provable Cyber Defense Report" in summary_content
        assert "PASSED" in summary_content
