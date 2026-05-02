# File Cleanup Analysis

## Files to KEEP (Essential)

### Core Agents (9 files) - ALL KEEP
- ✅ `agents/supervisor.py` - Main orchestrator
- ✅ `agents/ir_architect.py` - Granite optimization (REAL)
- ✅ `agents/memory_sentinel.py` - Granite safety (REAL)
- ✅ `agents/cegar_supervisor.py` - CEGAR loop (REAL)
- ✅ `agents/treefinement_supervisor.py` - Tree search
- ✅ `agents/algorithmic_synthesizer.py` - Algorithm replacement
- ✅ `agents/global_context_agent.py` - Inter-procedural
- ✅ `agents/microarch_tuner.py` - Hardware tuning
- ✅ `agents/safety_vault.py` - Certificates (REAL)
- ✅ `agents/shared_knowledge_base.py` - Coordination
- ✅ `agents/granite_direct.py` - Granite API
- ✅ `agents/bob_modes.md` - Documentation

### Server (2 files) - KEEP
- ✅ `server/mcp_server.py` - MCP tools
- ✅ `server/README.md` - Documentation

### Frontend (3 files) - KEEP
- ✅ `frontend/app.py` - Streamlit UI
- ✅ `frontend/README.md` - Documentation
- ✅ `frontend/test_ui.py` - UI tests

### Tests (4 files) - KEEP
- ✅ `tests/test_mcp_server.py` - MCP tests
- ✅ `tests/test_bob_agents.py` - Agent tests
- ✅ `tests/test_integration.py` - Integration tests
- ✅ `tests/test_all_agents_integration.py` - Full pipeline tests

### Main Demos (2 files) - KEEP
- ✅ `demo/demo.py` - **PRIMARY DEMO** (memory safety)
- ✅ `demo/ipcp_complete_demo.py` - **SECONDARY DEMO** (IPCP)

### Documentation - KEEP
- ✅ `README.md` - Main documentation
- ✅ `demo/VIDEO_SCRIPT.md` - Video guide
- ✅ `demo/IPCP_DEMO_SUMMARY.md` - IPCP explanation
- ✅ All other .md files in root

---

## Files to REMOVE (Unused/Redundant)

### Redundant Demo Files (5 files) - REMOVE
- ❌ `demo/fail_catch_prove.py` - Redundant (covered by demo.py)
- ❌ `demo/full_pipeline_demo.py` - Redundant (covered by demo.py)
- ❌ `demo/granite_cegar_demo.py` - Redundant (covered by demo.py)
- ❌ `demo/ipcp_demo.py` - Redundant (superseded by ipcp_complete_demo.py)
- ❌ `demo/retry_demo.py` - Redundant (covered by demo.py)
- ❌ `demo/test_ai_agents.py` - Test file, not a demo

### Redundant Test Files (2 files) - REMOVE
- ❌ `test_ipcp.py` - Root level test (should be in tests/)
- ❌ `test_supervisor_integration.py` - Root level test (should be in tests/)

### Intermediate/Generated IR Files (12 files) - REMOVE
These are generated during testing and can be recreated:
- ❌ `tests/fixtures/combined_optimized.ll`
- ❌ `tests/fixtures/combined.ll`
- ❌ `tests/fixtures/file1.ll`
- ❌ `tests/fixtures/file2.ll`
- ❌ `tests/fixtures/ipcp_combined.ll`
- ❌ `tests/fixtures/ipcp_example.ll`
- ❌ `tests/fixtures/ipcp_file1.ll`
- ❌ `tests/fixtures/ipcp_file2.ll`
- ❌ `tests/fixtures/safe_ipcp_optimized_v2.ll`
- ❌ `tests/fixtures/safe_ipcp_optimized.ll`
- ❌ `tests/fixtures/safe_ipcp.ll`
- ❌ `tests/fixtures/simple_O0.ll`
- ❌ `tests/fixtures/simple_O3.ll`

### Keep Source Files (7 files) - KEEP
These are source files that generate the .ll files:
- ✅ `tests/fixtures/simple.c`
- ✅ `tests/fixtures/loop.c`
- ✅ `tests/fixtures/unsafe.c`
- ✅ `tests/fixtures/file1.c`
- ✅ `tests/fixtures/file2.c`
- ✅ `tests/fixtures/ipcp_file1.c`
- ✅ `tests/fixtures/ipcp_file2.c`
- ✅ `tests/fixtures/ipcp_example.c`

### Demo Corpus - KEEP ALL
All 9 files in `demo_corpus/` are examples for the UI:
- ✅ Keep all files in `demo_corpus/algorithms/`
- ✅ Keep all files in `demo_corpus/math/`
- ✅ Keep all files in `demo_corpus/physics/`
- ✅ Keep all files in `demo_corpus/signal/`
- ✅ Keep all files in `demo_corpus/unsafe/`

---

## Summary

### Files to Delete: 19 total
- 6 redundant demo scripts
- 2 misplaced test files  
- 11 generated .ll files (can be regenerated)

### Files to Keep: Everything else
- All 12 agent files
- All 4 test suites
- 2 main demos (demo.py, ipcp_complete_demo.py)
- All source .c files
- All documentation
- All demo corpus examples
- Frontend and server code

### Cleanup Commands
```bash
# Remove redundant demos
rm demo/fail_catch_prove.py
rm demo/full_pipeline_demo.py
rm demo/granite_cegar_demo.py
rm demo/ipcp_demo.py
rm demo/retry_demo.py
rm demo/test_ai_agents.py

# Remove misplaced tests
rm test_ipcp.py
rm test_supervisor_integration.py

# Remove generated IR files
rm tests/fixtures/*.ll

# Commit cleanup
git add -A
git commit -m "chore: Remove redundant and generated files"
git push
```

### Impact
- **Before:** 60+ files
- **After:** ~40 essential files
- **Benefit:** Cleaner repository, easier to navigate, faster cloning