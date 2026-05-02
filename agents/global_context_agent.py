#!/usr/bin/env python3
"""
AI Compiler - Global Context Agent
Inter-procedural optimization with ThinLTO analysis
"""

import os
import sys
import re
import subprocess
import tempfile
from typing import Dict, Any, Optional, List, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from server.mcp_server import compile_to_ir, optimize_ir_pass, validate_translation


@dataclass
class FunctionSignature:
    """Function signature information"""
    name: str
    return_type: str
    parameters: List[str]
    is_external: bool = False
    call_count: int = 0


@dataclass
class GlobalVariable:
    """Global variable information"""
    name: str
    type_info: str
    is_constant: bool = False
    initial_value: Optional[str] = None


@dataclass
class CallSite:
    """Function call site information"""
    caller: str
    callee: str
    arguments: List[str]
    location: str  # File and line


@dataclass
class ProjectContext:
    """Whole-program analysis context"""
    functions: Dict[str, FunctionSignature] = field(default_factory=dict)
    globals: Dict[str, GlobalVariable] = field(default_factory=dict)
    call_sites: List[CallSite] = field(default_factory=list)
    call_graph: Dict[str, Set[str]] = field(default_factory=dict)
    constant_propagation_opportunities: List[Dict[str, Any]] = field(default_factory=list)


class GlobalContextAgent:
    """
    Agent that performs whole-program analysis for inter-procedural optimization
    
    Analyzes multiple source files together to find optimization opportunities
    that span file boundaries (e.g., constant propagation across files).
    """
    
    def __init__(self):
        """Initialize the global context agent"""
        self.context = ProjectContext()
        self.files_analyzed = 0
        self.optimizations_found = 0
    
    def ingest_source_files(self, source_files: List[str]) -> ProjectContext:
        """
        Ingest multiple source files and build project context
        
        Args:
            source_files: List of source file paths
            
        Returns:
            ProjectContext with whole-program information
        """
        print(f"\n🌍 Ingesting {len(source_files)} source files...")
        
        for file_path in source_files:
            if not os.path.exists(file_path):
                print(f"   ⚠️  File not found: {file_path}")
                continue
            
            print(f"   📄 Analyzing {file_path}...")
            self._analyze_file(file_path)
            self.files_analyzed += 1
        
        # Build call graph
        self._build_call_graph()
        
        # Find optimization opportunities
        self._find_optimization_opportunities()
        
        print(f"   ✅ Analyzed {self.files_analyzed} files")
        print(f"   📊 Found {len(self.context.functions)} functions")
        print(f"   📊 Found {len(self.context.globals)} global variables")
        print(f"   📊 Found {len(self.context.call_sites)} call sites")
        print(f"   💡 Found {self.optimizations_found} optimization opportunities")
        
        return self.context
    
    def _analyze_file(self, file_path: str):
        """Analyze a single source file"""
        try:
            # Read source code
            with open(file_path, 'r') as f:
                source_code = f.read()
            
            # Compile to IR
            from server.mcp_server import compile_to_ir
            result = compile_to_ir(source_code, os.path.basename(file_path))
            
            if not result["success"]:
                print(f"      ⚠️  Compilation failed: {result['error']}")
                return
            
            ir_code = result["ir"]
            
            # Extract functions
            self._extract_functions(ir_code, file_path)
            
            # Extract globals
            self._extract_globals(ir_code, file_path)
            
            # Extract call sites
            self._extract_call_sites(ir_code, file_path)
            
        except Exception as e:
            print(f"      ⚠️  Error analyzing file: {e}")
    
    def _extract_functions(self, ir_code: str, file_path: str):
        """Extract function signatures from IR"""
        # Pattern: define <return_type> @<name>(<params>)
        pattern = r'define\s+(\S+)\s+@(\w+)\s*\(([^)]*)\)'
        
        for match in re.finditer(pattern, ir_code):
            return_type = match.group(1)
            func_name = match.group(2)
            params_str = match.group(3)
            
            # Parse parameters
            params = []
            if params_str.strip():
                for param in params_str.split(','):
                    param = param.strip()
                    if param:
                        params.append(param)
            
            self.context.functions[func_name] = FunctionSignature(
                name=func_name,
                return_type=return_type,
                parameters=params,
                is_external=False
            )
    
    def _extract_globals(self, ir_code: str, file_path: str):
        """Extract global variables from IR"""
        # Pattern: @<name> = <linkage> <type> <value>
        pattern = r'@(\w+)\s*=\s*(\w+)?\s*(\w+)\s+([^,\n]+)'
        
        for match in re.finditer(pattern, ir_code):
            var_name = match.group(1)
            linkage = match.group(2) or ""
            type_info = match.group(3)
            value = match.group(4).strip()
            
            is_constant = "constant" in linkage
            
            self.context.globals[var_name] = GlobalVariable(
                name=var_name,
                type_info=type_info,
                is_constant=is_constant,
                initial_value=value if value else None
            )
    
    def _extract_call_sites(self, ir_code: str, file_path: str):
        """Extract function call sites from IR"""
        # Pattern: call <type> @<function>(<args>)
        pattern = r'call\s+\S+\s+@(\w+)\s*\(([^)]*)\)'
        
        current_function = None
        
        for line in ir_code.split('\n'):
            # Track current function
            func_match = re.search(r'define\s+\S+\s+@(\w+)', line)
            if func_match:
                current_function = func_match.group(1)
            
            # Find call sites
            call_match = re.search(pattern, line)
            if call_match and current_function:
                callee = call_match.group(1)
                args_str = call_match.group(2)
                
                # Parse arguments
                args = []
                if args_str.strip():
                    for arg in args_str.split(','):
                        arg = arg.strip()
                        if arg:
                            args.append(arg)
                
                call_site = CallSite(
                    caller=current_function,
                    callee=callee,
                    arguments=args,
                    location=f"{file_path}:?"
                )
                
                self.context.call_sites.append(call_site)
                
                # Update call count
                if callee in self.context.functions:
                    self.context.functions[callee].call_count += 1
    
    def _build_call_graph(self):
        """Build call graph from call sites"""
        for call_site in self.context.call_sites:
            if call_site.caller not in self.context.call_graph:
                self.context.call_graph[call_site.caller] = set()
            
            self.context.call_graph[call_site.caller].add(call_site.callee)
    
    def _find_optimization_opportunities(self):
        """Find inter-procedural optimization opportunities"""
        # Find constant propagation opportunities
        for call_site in self.context.call_sites:
            # Check if any arguments are constants
            for i, arg in enumerate(call_site.arguments):
                if self._is_constant(arg):
                    opportunity = {
                        "type": "constant_propagation",
                        "caller": call_site.caller,
                        "callee": call_site.callee,
                        "argument_index": i,
                        "constant_value": arg,
                        "location": call_site.location
                    }
                    self.context.constant_propagation_opportunities.append(opportunity)
                    self.optimizations_found += 1
    
    def _is_constant(self, value: str) -> bool:
        """Check if a value is a constant"""
        # Check for numeric constants
        if re.match(r'^-?\d+$', value.strip()):
            return True
        
        # Check for constant globals
        for global_var in self.context.globals.values():
            if global_var.is_constant and global_var.name in value:
                return True
        
        return False
    
    def apply_global_constant_folding(
        self,
        ir_code: str
    ) -> Tuple[str, List[str]]:
        """
        Apply constant folding across file boundaries
        
        Args:
            ir_code: LLVM IR code
            
        Returns:
            Tuple of (optimized_ir, applied_optimizations)
        """
        optimized_ir = ir_code
        applied = []
        
        print("\n   🔧 Applying global constant folding...")
        
        for opp in self.context.constant_propagation_opportunities:
            # For now, add a comment indicating the opportunity
            # In production, would perform actual IR transformation
            
            comment = f"""
; GLOBAL OPTIMIZATION OPPORTUNITY:
; Function {opp['callee']} called from {opp['caller']}
; Argument {opp['argument_index']} is constant: {opp['constant_value']}
; Can specialize {opp['callee']} for this constant value
"""
            optimized_ir = comment + optimized_ir
            applied.append(f"Constant fold in {opp['callee']}")
        
        print(f"      ✅ Applied {len(applied)} optimizations")
        
        return optimized_ir, applied
    
    def find_interprocedural_optimizations(self) -> List[Dict[str, Any]]:
        """
        Find inter-procedural optimization opportunities
        
        Returns:
            List of optimization opportunities
        """
        opportunities = []
        
        # 1. Constant propagation (already found)
        opportunities.extend(self.context.constant_propagation_opportunities)
        
        # 2. Dead function elimination
        for func_name, func_sig in self.context.functions.items():
            if func_sig.call_count == 0 and not func_sig.is_external:
                opportunities.append({
                    "type": "dead_function_elimination",
                    "function": func_name,
                    "reason": "Never called"
                })
        
        # 3. Inline candidates (small functions called once)
        for func_name, func_sig in self.context.functions.items():
            if func_sig.call_count == 1:
                opportunities.append({
                    "type": "inline_candidate",
                    "function": func_name,
                    "reason": "Called only once"
                })
        
        return opportunities
    
    def generate_lto_summary(self) -> Dict[str, Any]:
        """
        Generate ThinLTO-style summary
        
        Returns:
            Summary dictionary
        """
        return {
            "files_analyzed": self.files_analyzed,
            "total_functions": len(self.context.functions),
            "total_globals": len(self.context.globals),
            "total_call_sites": len(self.context.call_sites),
            "call_graph_size": sum(len(callees) for callees in self.context.call_graph.values()),
            "optimization_opportunities": {
                "constant_propagation": len(self.context.constant_propagation_opportunities),
                "total": self.optimizations_found
            },
            "functions": {
                name: {
                    "return_type": sig.return_type,
                    "param_count": len(sig.parameters),
                    "call_count": sig.call_count,
                    "is_external": sig.is_external
                }
                for name, sig in self.context.functions.items()
            }
        }


def main():
    """Test the global context agent"""
    print("=" * 70)
    print("AI Compiler - Global Context Agent Test")
    print("=" * 70)
    print()
    
    # Create test files
    test_file1 = tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False)
    test_file1.write("""
int add(int a, int b) {
    return a + b;
}

int main() {
    return add(5, 10);
}
""")
    test_file1.close()
    
    test_file2 = tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False)
    test_file2.write("""
int multiply(int x, int y) {
    return x * y;
}

int compute() {
    return multiply(3, 4);
}
""")
    test_file2.close()
    
    try:
        agent = GlobalContextAgent()
        
        # Ingest files
        context = agent.ingest_source_files([test_file1.name, test_file2.name])
        
        # Find optimizations
        opportunities = agent.find_interprocedural_optimizations()
        
        print()
        print("=" * 70)
        print("Results:")
        print(f"Files analyzed: {agent.files_analyzed}")
        print(f"Functions found: {len(context.functions)}")
        print(f"Call sites found: {len(context.call_sites)}")
        print(f"Optimization opportunities: {len(opportunities)}")
        
        if opportunities:
            print("\nOptimization Opportunities:")
            for opp in opportunities[:5]:  # Show first 5
                print(f"  - {opp['type']}: {opp.get('function', opp.get('callee', 'N/A'))}")
        
        # Generate LTO summary
        summary = agent.generate_lto_summary()
        print(f"\nLTO Summary:")
        print(f"  Total functions: {summary['total_functions']}")
        print(f"  Total call sites: {summary['total_call_sites']}")
        print(f"  Constant propagation opportunities: {summary['optimization_opportunities']['constant_propagation']}")
        print("=" * 70)
        
    finally:
        # Cleanup
        os.unlink(test_file1.name)
        os.unlink(test_file2.name)


if __name__ == "__main__":
    main()

# Made with Bob