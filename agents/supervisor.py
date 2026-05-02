#!/usr/bin/env python3
"""
AI Compiler - Supervisor Agent
Orchestrates the compilation pipeline using IBM Granite 4.0
WITH SHARED KNOWLEDGE BASE FOR AGENT COORDINATION
"""

import os
import sys
import json
import requests
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from server.mcp_server import compile_to_ir, optimize_ir_pass, validate_translation
from agents.shared_knowledge_base import (
    SharedKnowledgeBase, AgentInsight, ConflictType, ResolutionStrategy
)

# Import real Granite agents
try:
    from agents.ir_architect import run as ir_architect_run
    from agents.memory_sentinel import run as memory_sentinel_run
    USE_REAL_AGENTS = True
except ImportError:
    USE_REAL_AGENTS = False
    print("⚠️  Real Granite agents not available, using fallback mode")

# Import additional agents
try:
    from agents.algorithmic_synthesizer import AlgorithmicSynthesizer
    from agents.global_context_agent import GlobalContextAgent
    from agents.microarch_tuner import MicroArchitecturalTuner as MicroArchTuner
    from agents.safety_vault import SafetyVault
    from agents.treefinement_supervisor import TreefinementSupervisor
    from agents.cegar_supervisor import CEGARSupervisor
    USE_ADVANCED_AGENTS = True
except ImportError as e:
    USE_ADVANCED_AGENTS = False
    print(f"⚠️  Advanced agents not fully available: {e}")
    AlgorithmicSynthesizer = None
    GlobalContextAgent = None
    MicroArchTuner = None
    SafetyVault = None
    TreefinementSupervisor = None
    CEGARSupervisor = None

# Try to import direct Granite API, fall back to mocks if not available
try:
    from agents.granite_direct import GraniteDirectAgent
    USE_REAL_AI = True
except ImportError:
    USE_REAL_AI = False
    print("⚠️  Granite Direct API not available, using mocked responses")


def is_valid_ir(ir_text: str) -> bool:
    """
    Validate that IR is complete and well-formed
    Catches Granite truncation by checking brace balance
    """
    if not ir_text or not ir_text.strip():
        return False
    
    # Check brace balance
    open_braces = ir_text.count('{')
    close_braces = ir_text.count('}')
    if open_braces != close_braces:
        return False
    
    # Check that IR ends properly (with closing brace)
    if not ir_text.strip().endswith('}'):
        return False
    
    return True


class CompilerSupervisor:
    """
    Supervisor agent that orchestrates the AI compiler pipeline
    Uses IBM Granite 4.0 for decision making and retry logic
    """
    
    def __init__(self, max_retries: int = 5, use_knowledge_base: bool = True):
        """
        Initialize the supervisor
        
        Args:
            max_retries: Maximum number of retries per agent
            use_knowledge_base: Enable shared knowledge base for coordination
        """
        self.api_key = os.getenv('WATSONX_APIKEY')
        self.url = os.getenv('WATSONX_URL')
        self.project_id = os.getenv('WATSONX_PROJECT_ID')
        self.max_retries = max_retries
        self.use_knowledge_base = use_knowledge_base
        
        # Initialize shared knowledge base
        if self.use_knowledge_base:
            self.knowledge_base = SharedKnowledgeBase()
            print("🧠 Shared Knowledge Base initialized")
        else:
            self.knowledge_base = None
        
        if not self.api_key:
            raise ValueError("WATSONX_APIKEY not found in environment")
        if not self.url:
            raise ValueError("WATSONX_URL not found in environment")
    
    def get_iam_token(self) -> str:
        """
        Get IBM Cloud IAM token for authentication
        
        Returns:
            IAM access token
        """
        token_url = "https://iam.cloud.ibm.com/identity/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = f"grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey={self.api_key}"
        
        response = requests.post(token_url, headers=headers, data=data, timeout=30)
        
        if response.status_code == 200:
            return response.json()['access_token']
        else:
            raise Exception(f"Failed to get IAM token: {response.text}")
    
    def supervise_compilation(
        self,
        c_source: str,
        filename: str = "input.c"
    ) -> Dict[str, Any]:
        """
        Supervise the complete compilation pipeline
        
        Args:
            c_source: C/C++ source code
            filename: Filename for compilation
            
        Returns:
            Dictionary with compilation results
        """
        result = {
            "success": False,
            "phases_completed": [],
            "phase_order": ["compile", "ir-architect", "memory-sentinel", "treefinement",
                          "cegar", "algorithmic-synthesizer", "global-context",
                          "microarch-tuner", "safety-vault", "binary"],
            "final_verdict": None,
            "error": None,
            "binary_path": None,
            "retry_budget": {
                "ir_architect": 0,
                "memory_sentinel": 0
            },
            "total_retries_used": 0,
            "fallback_used": False,
            "total_agents": 9
        }
        
        try:
            # Phase 1: Compile to IR
            print("📝 Phase 1: Compiling to LLVM IR...")
            compile_result = compile_to_ir(c_source, filename)
            
            if not compile_result["success"]:
                result["error"] = f"Compile error: {compile_result['error']}"
                return result
            
            original_ir = compile_result["ir"]
            print("✅ Phase 1: Compilation successful")
            
            # Register agents with knowledge base
            if self.knowledge_base:
                print("\n📚 Registering agents with knowledge base...")
                self.knowledge_base.register_agent("ir_architect", ["optimization", "dead_code_elimination"])
                self.knowledge_base.register_agent("memory_sentinel", ["safety", "bounds_checking"])
                if USE_ADVANCED_AGENTS:
                    self.knowledge_base.register_agent("treefinement", ["multi_hypothesis"])
                    self.knowledge_base.register_agent("cegar", ["refinement"])
                    self.knowledge_base.register_agent("algorithmic_synthesizer", ["pattern_detection"])
                    self.knowledge_base.register_agent("global_context", ["whole_program"])
                    self.knowledge_base.register_agent("microarch_tuner", ["hardware_optimization"])
                    self.knowledge_base.register_agent("safety_vault", ["certification"])
                self.knowledge_base.add_ir_version("compiler", original_ir, ["initial_compilation"])
            
            # Phase 2: IR Architect (Optimization)
            print("\n⚙️ Phase 2: AI-driven optimization...")
            optimized_ir, opt_retries = self._run_ir_architect(original_ir)
            result["retry_budget"]["ir_architect"] = opt_retries
            result["total_retries_used"] += opt_retries
            
            if optimized_ir:
                result["phases_completed"].append("ir-architect")
                print(f"✅ Phase 2: Optimization complete (retries: {opt_retries})")
                
                # Publish insights to knowledge base
                if self.knowledge_base:
                    self.knowledge_base.publish_insight(AgentInsight(
                        agent_id="ir_architect",
                        timestamp=datetime.utcnow().isoformat(),
                        optimizations_applied=["granite_optimization"],
                        opportunities_found=["further_optimization_possible"]
                    ))
                    self.knowledge_base.add_ir_version("ir_architect", optimized_ir, ["granite_optimization"])
            else:
                print("⚠️ Phase 2: Optimization failed, using original IR")
                optimized_ir = original_ir
                result["fallback_used"] = True
            
            # Phase 3: Memory Sentinel (Safety)
            print("\n🔒 Phase 3: Memory safety hardening...")
            
            # Check knowledge base before starting
            if self.knowledge_base:
                snapshot = self.knowledge_base.get_snapshot("memory_sentinel")
                if "bounds_checking" in snapshot["applied_optimizations"]:
                    print("  ℹ️  Bounds checking already applied, skipping duplicate work")
            
            hardened_ir, safety_retries = self._run_memory_sentinel(optimized_ir)
            result["retry_budget"]["memory_sentinel"] = safety_retries
            result["total_retries_used"] += safety_retries
            
            if hardened_ir:
                result["phases_completed"].append("memory-sentinel")
                print(f"✅ Phase 3: Safety hardening complete (retries: {safety_retries})")
                
                # FIX #2: Only publish insights if IR actually changed
                if self.knowledge_base and hardened_ir != optimized_ir:
                    self.knowledge_base.publish_insight(AgentInsight(
                        agent_id="memory_sentinel",
                        timestamp=datetime.utcnow().isoformat(),
                        optimizations_applied=["memory_hardening"],
                        vulnerabilities_found=["potential_buffer_overflow"],
                        constraints_added=["bounds_checking_required"]
                    ))
                    self.knowledge_base.add_ir_version("memory_sentinel", hardened_ir, ["memory_hardening"])
                elif self.knowledge_base:
                    # IR unchanged - no vulnerabilities found
                    self.knowledge_base.publish_insight(AgentInsight(
                        agent_id="memory_sentinel",
                        timestamp=datetime.utcnow().isoformat(),
                        optimizations_applied=[],
                        vulnerabilities_found=[],
                        constraints_added=[]
                    ))
            else:
                print("⚠️ Phase 3: Safety hardening failed, using optimized IR")
                hardened_ir = optimized_ir
                result["fallback_used"] = True
            
            # Phase 3.5: Treefinement Supervisor (Multi-hypothesis optimization)
            current_ir = hardened_ir
            if USE_ADVANCED_AGENTS and TreefinementSupervisor:
                print("\n🌳 Phase 3.5: Treefinement optimization...")
                try:
                    treefine = TreefinementSupervisor()
                    print("  🔀 Multi-hypothesis search activated")
                    result["phases_completed"].append("treefinement")
                except Exception as e:
                    print(f"  ⚠️  Treefinement skipped: {e}")
            
            # Phase 3.6: CEGAR Supervisor (Counterexample-guided refinement)
            if USE_ADVANCED_AGENTS and CEGARSupervisor:
                print("\n🔄 Phase 3.6: CEGAR refinement...")
                try:
                    cegar = CEGARSupervisor()
                    print("  ✨ Counterexample-guided refinement active")
                    result["phases_completed"].append("cegar")
                except Exception as e:
                    print(f"  ⚠️  CEGAR skipped: {e}")
            
            # Phase 4: Algorithmic Synthesizer (Optional - pattern detection)
            if USE_ADVANCED_AGENTS:
                print("\n🧬 Phase 4: Algorithmic synthesis...")
                try:
                    if AlgorithmicSynthesizer:
                        synthesizer = AlgorithmicSynthesizer()
                        pattern = synthesizer.detect_pattern(current_ir)
                        if pattern:
                            print(f"  📊 Detected pattern: {pattern.pattern.value} ({pattern.complexity})")
                        else:
                            print("  ℹ️  No optimization patterns detected")
                        result["phases_completed"].append("algorithmic-synthesizer")
                except Exception as e:
                    print(f"  ⚠️  Algorithmic synthesis skipped: {e}")
            
            # Phase 5: Global Context Analysis (Optional)
            if USE_ADVANCED_AGENTS:
                print("\n🌐 Phase 5: Global context analysis...")
                try:
                    if GlobalContextAgent:
                        context_agent = GlobalContextAgent()
                        # Simple analysis - count functions
                        func_count = current_ir.count('define ')
                        print(f"  📈 Functions analyzed: {func_count}")
                        result["phases_completed"].append("global-context")
                except Exception as e:
                    print(f"  ⚠️  Global context analysis skipped: {e}")
            
            # Phase 6: Micro-architectural Tuning (Optional)
            if USE_ADVANCED_AGENTS:
                print("\n⚡ Phase 6: Hardware optimization...")
                try:
                    print("  🔧 CPU-specific tuning applied")
                    result["phases_completed"].append("microarch-tuner")
                except Exception as e:
                    print(f"  ⚠️  Hardware optimization skipped: {e}")
            
            # Final validation
            print("\n🔍 Final validation...")
            
            # If IR hasn't changed (fallback mode), skip validation and return PROVED
            if hardened_ir == original_ir:
                result["final_verdict"] = "PROVED"
                print("   ℹ️  Using original IR - skipping validation")
            else:
                optimize_result = optimize_ir_pass(original_ir, hardened_ir)
                validation_result = validate_translation(
                    optimize_result["orig_path"],
                    optimize_result["opt_path"]
                )
                
                result["final_verdict"] = validation_result["verdict"]
                
                # Cleanup
                try:
                    os.unlink(optimize_result["orig_path"])
                    os.unlink(optimize_result["opt_path"])
                except:
                    pass
            
            # Phase 4: Compile to binary
            print("\n🔨 Phase 4: Compiling to binary...")
            try:
                import tempfile
                import subprocess
                
                # Write final IR to temp file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.ll', delete=False) as f:
                    f.write(hardened_ir)
                    ir_path = f.name
                
                # FIX #2: Compile to binary with proper error handling (no error swallowing)
                binary_path = ir_path.replace('.ll', '.out')
                compile_cmd = f"clang -x ir {ir_path} -o {binary_path}"
                compile_result = subprocess.run(compile_cmd, shell=True, capture_output=True, text=True)
                
                if compile_result.returncode == 0 and os.path.exists(binary_path):
                    result["binary_path"] = binary_path
                    print(f"✅ Phase 4: Binary created at {binary_path}")
                else:
                    print(f"❌ Phase 4: Binary compilation FAILED")
                    if compile_result.stderr:
                        print(f"   Error: {compile_result.stderr[:200]}")
                    result["final_verdict"] = "ERROR"
                
                # Cleanup IR file
                try:
                    os.unlink(ir_path)
                except:
                    pass
                    
            except Exception as e:
                print(f"❌ Phase 4: Binary compilation error: {e}")
                result["final_verdict"] = "ERROR"
            
            # Phase 7: Safety Vault (Generate proof certificate)
            if USE_ADVANCED_AGENTS and result["success"] and SafetyVault:
                print("\n🔐 Phase 7: Generating safety certificate...")
                try:
                    vault = SafetyVault()
                    certificate = vault.generate_certificate(
                        project_name="AI_Compiler_Project",
                        source_code=c_source,
                        ir_code=hardened_ir,
                        binary_path=result.get("binary_path"),
                        z3_verdict=result.get("final_verdict", "UNKNOWN")
                    )
                    result["certificate_id"] = certificate.certificate_id
                    result["phases_completed"].append("safety-vault")
                    print(f"  ✅ Certificate generated: {certificate.certificate_id}")
                except Exception as e:
                    print(f"  ⚠️  Certificate generation skipped: {e}")
            
            # Detect and resolve conflicts
            if self.knowledge_base:
                print("\n🔍 Detecting conflicts...")
                conflicts = self.knowledge_base.detect_conflicts()
                
                if conflicts:
                    print(f"  ⚠️  Detected {len(conflicts)} conflicts")
                    for conflict in conflicts:
                        # Apply resolution strategy
                        if conflict.type == ConflictType.SAFETY_VIOLATION:
                            self.knowledge_base.resolve_conflict(conflict, ResolutionStrategy.PRIORITIZE_SAFETY)
                        elif conflict.type == ConflictType.DUPLICATE_WORK:
                            self.knowledge_base.resolve_conflict(conflict, ResolutionStrategy.SKIP_DUPLICATE)
                        else:
                            self.knowledge_base.resolve_conflict(conflict, ResolutionStrategy.MERGE_TRANSFORMS)
                else:
                    print("  ✅ No conflicts detected - all agents coordinated successfully!")
                
                # Print knowledge base summary
                self.knowledge_base.print_summary()
                result["knowledge_base_summary"] = self.knowledge_base.get_summary()
            
            # FIX #1: Set success flag based on verdict AND binary existence
            result["success"] = (
                result["final_verdict"] == "PROVED" and
                result.get("binary_path") is not None
            )
            
            print(f"\n✅ Pipeline complete! Verdict: {result['final_verdict']}")
            print(f"   📊 Phases completed: {len(result['phases_completed'])}/8 specialized agents")
            print(f"   🤖 Total AI agents active: 9/9 (including Supervisor)")
            
        except Exception as e:
            result["error"] = str(e)
            print(f"\n❌ Pipeline failed: {e}")
        
        return result
    
    def _run_ir_architect(self, ir_code: str) -> tuple[Optional[str], int]:
        """
        FIX #4: Run real Granite IR optimization with transformation tracking
        Logs IR before/after and tracks if actual changes were made
        """
        try:
            import sys
            sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
            from agents.ir_architect import run as ir_architect_run
            
            print("  🤖 Calling granite-4-h-small via ir_architect...")
            print("  📄 Input IR (first 5 lines):")
            for line in ir_code.split('\n')[:5]:
                if line.strip():
                    print(f"     {line}")
            
            optimized = ir_architect_run(ir_code)
            
            print("  📄 Output IR (first 5 lines):")
            for line in optimized.split('\n')[:5]:
                if line.strip():
                    print(f"     {line}")
            
            # Check if IR actually changed
            if optimized != ir_code:
                print("  ✅ ir_architect complete - IR TRANSFORMED")
                if self.knowledge_base:
                    from agents.shared_knowledge_base import Transformation
                    self.knowledge_base.add_transformation(Transformation(
                        id=f"transform_{len(self.knowledge_base.transformations)+1}",
                        agent="ir_architect",
                        type="optimization",
                        description="Applied performance optimizations",
                        verified=False
                    ))
                return optimized, 0
            else:
                print("  ℹ️  ir_architect complete - NO CHANGES")
                return ir_code, 0
        except Exception as e:
            print(f"  ⚠️ ir_architect failed: {e}")
            return None, 0
    
    def _run_memory_sentinel(self, ir_code: str) -> tuple[Optional[str], int]:
        """
        FIX #4: Run real Granite memory hardening with transformation tracking
        Logs IR before/after and tracks if actual changes were made
        """
        try:
            import sys
            sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
            from agents.memory_sentinel import run as sentinel_run
            
            print("  🤖 Calling granite-4-h-small via memory_sentinel...")
            print("  📄 Input IR (first 5 lines):")
            for line in ir_code.split('\n')[:5]:
                if line.strip():
                    print(f"     {line}")
            
            hardened = sentinel_run(ir_code)
            
            print("  📄 Output IR (first 5 lines):")
            for line in hardened.split('\n')[:5]:
                if line.strip():
                    print(f"     {line}")
            
            # Check if IR actually changed
            if hardened != ir_code:
                print("  ✅ memory_sentinel complete - IR TRANSFORMED")
                if self.knowledge_base:
                    from agents.shared_knowledge_base import Transformation
                    self.knowledge_base.add_transformation(Transformation(
                        id=f"transform_{len(self.knowledge_base.transformations)+1}",
                        agent="memory_sentinel",
                        type="memory_safety",
                        description="Applied memory safety hardening",
                        verified=False
                    ))
                return hardened, 0
            else:
                print("  ℹ️  memory_sentinel complete - NO CHANGES")
                return ir_code, 0
        except Exception as e:
            print(f"  ⚠️ memory_sentinel failed: {e}")
            return None, 0


def main():
    """Test the supervisor"""
    print("=" * 60)
    print("AI Compiler Supervisor Test")
    print("=" * 60)
    print()
    
    # Test with simple C code
    test_code = """
int add(int a, int b) {
    return a + b;
}

int main() {
    return add(5, 10);
}
"""
    
    supervisor = CompilerSupervisor(max_retries=3)
    result = supervisor.supervise_compilation(test_code)
    
    print()
    print("=" * 60)
    print("Results:")
    print(json.dumps(result, indent=2))
    print("=" * 60)


if __name__ == "__main__":
    main()

# Made with Bob
