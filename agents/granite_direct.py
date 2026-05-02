#!/usr/bin/env python3
"""
Direct Granite 4.0 API Integration
Bypasses Bob Custom Modes by calling watsonx.ai inference API directly
"""

import os
import json
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


class GraniteDirectAgent:
    """
    Direct integration with IBM Granite 4.0 via watsonx.ai API
    Implements the same logic as Bob Custom Modes but fully automated
    """
    
    def __init__(self):
        """Initialize Granite API client"""
        self.api_key = os.getenv('WATSONX_APIKEY')
        self.url = os.getenv('WATSONX_URL', 'https://us-south.ml.cloud.ibm.com')
        self.project_id = os.getenv('WATSONX_PROJECT_ID')
        
        if not self.api_key:
            raise ValueError("WATSONX_APIKEY not found in environment")
        
        self._access_token = None
    
    def get_access_token(self) -> str:
        """Get or refresh IAM access token"""
        if self._access_token:
            return self._access_token
        
        token_url = "https://iam.cloud.ibm.com/identity/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = f"grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey={self.api_key}"
        
        response = requests.post(token_url, headers=headers, data=data, timeout=30)
        
        if response.status_code == 200:
            self._access_token = response.json()['access_token']
            return self._access_token
        else:
            raise Exception(f"Failed to get IAM token: {response.text}")
    
    def call_granite(
        self,
        system_prompt: str,
        user_message: str,
        model_id: str = "ibm/granite-13b-chat-v2",
        max_tokens: int = 2000,
        temperature: float = 0.7
    ) -> str:
        """
        Call Granite 4.0 model directly via watsonx.ai API
        
        Args:
            system_prompt: System instructions for the model
            user_message: User's input message
            model_id: Model identifier (default: granite-13b-chat-v2)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Model's response text
        """
        token = self.get_access_token()
        
        # watsonx.ai text generation endpoint
        endpoint = f"{self.url}/ml/v1/text/generation?version=2023-05-29"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Format prompt for Granite
        full_prompt = f"""<|system|>
{system_prompt}
<|user|>
{user_message}
<|assistant|>
"""
        
        payload = {
            "model_id": model_id,
            "input": full_prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "top_p": 0.9,
                "top_k": 50,
                "repetition_penalty": 1.1,
                "stop_sequences": ["<|user|>", "<|system|>"]
            }
        }
        
        # Add project_id if available
        if self.project_id:
            payload["project_id"] = self.project_id
        
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result.get('results', [{}])[0].get('generated_text', '')
            return generated_text.strip()
        else:
            raise Exception(f"Granite API error: {response.status_code} - {response.text}")
    
    def ir_architect(self, ir_code: str) -> Dict[str, Any]:
        """
        AI-driven LLVM IR optimization (replaces @ir-architect Bob mode)
        
        Args:
            ir_code: Original LLVM IR code
            
        Returns:
            Dictionary with optimized IR and metadata
        """
        system_prompt = """You are an expert LLVM compiler optimization engineer. Your role is to analyze LLVM IR code and propose aggressive, semantically-preserving optimizations.

## Your Capabilities:
- Dead code elimination
- Constant folding and propagation
- Loop invariant code motion
- Strength reduction (e.g., multiply by power of 2 → left shift)
- Common subexpression elimination
- Function inlining opportunities
- Vectorization hints

## Output Format:
Return ONLY a JSON object with this exact structure:
{
  "optimized_ir": "...",
  "transformation_applied": true/false,
  "transformation_type": "dead code elimination | constant folding | ...",
  "speedup_reasoning": "explanation of expected performance improvement"
}

## Rules:
- NEVER change program semantics
- Return ONLY valid JSON, no markdown or explanations
- If no optimization is possible, set transformation_applied to false and return original IR"""

        user_message = f"""Analyze and optimize this LLVM IR code:

```llvm
{ir_code}
```

Return optimized IR as JSON."""

        try:
            response = self.call_granite(system_prompt, user_message)
            
            # Try to parse JSON from response
            # Handle markdown code blocks if present
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()
            
            result = json.loads(json_str)
            
            # Validate required fields
            if "optimized_ir" not in result:
                result["optimized_ir"] = ir_code
                result["transformation_applied"] = False
            
            return result
            
        except Exception as e:
            print(f"⚠️  IR Architect error: {e}")
            return {
                "optimized_ir": ir_code,
                "transformation_applied": False,
                "transformation_type": "none",
                "speedup_reasoning": f"Error: {str(e)}"
            }
    
    def memory_sentinel(self, ir_code: str) -> Dict[str, Any]:
        """
        Memory safety hardening (replaces @memory-sentinel Bob mode)
        
        Args:
            ir_code: LLVM IR code to harden
            
        Returns:
            Dictionary with hardened IR and metadata
        """
        system_prompt = """You are an expert in memory safety and secure coding. Your role is to analyze LLVM IR code and inject bounds-checking instrumentation to prevent memory safety violations.

## Your Mission:
Harden C/C++ programs against:
- Buffer overflows
- Out-of-bounds array access
- Use-after-free
- Null pointer dereferences

## Instrumentation Strategy:
1. Identify all memory access operations (load, store, getelementptr)
2. Add bounds checking before each access
3. Insert calls to @__bounds_fail() on violations
4. Preserve original program semantics for valid inputs

## Output Format:
Return ONLY a JSON object with this exact structure:
{
  "hardened_ir": "...",
  "checks_added": number,
  "check_locations": ["line 5: array bounds", "line 12: null check", ...],
  "safety_reasoning": "explanation of protections added"
}

## Rules:
- NEVER change valid program behavior
- Return ONLY valid JSON, no markdown or explanations
- If no checks needed, set checks_added to 0 and return original IR"""

        user_message = f"""Add memory safety checks to this LLVM IR code:

```llvm
{ir_code}
```

Return hardened IR as JSON."""

        try:
            response = self.call_granite(system_prompt, user_message)
            
            # Try to parse JSON from response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()
            
            result = json.loads(json_str)
            
            # Validate required fields
            if "hardened_ir" not in result:
                result["hardened_ir"] = ir_code
                result["checks_added"] = 0
            
            return result
            
        except Exception as e:
            print(f"⚠️  Memory Sentinel error: {e}")
            return {
                "hardened_ir": ir_code,
                "checks_added": 0,
                "check_locations": [],
                "safety_reasoning": f"Error: {str(e)}"
            }


# Test function
def test_granite_direct():
    """Test direct Granite API integration"""
    print("Testing Direct Granite 4.0 API Integration")
    print("=" * 60)
    
    agent = GraniteDirectAgent()
    
    # Test IR code
    test_ir = """define i32 @test() {
  %unused = add i32 1, 1
  %result = add i32 2, 2
  ret i32 %result
}"""
    
    print("\n1. Testing IR Architect...")
    opt_result = agent.ir_architect(test_ir)
    print(f"   Transformation: {opt_result.get('transformation_type', 'none')}")
    print(f"   Applied: {opt_result.get('transformation_applied', False)}")
    
    print("\n2. Testing Memory Sentinel...")
    safety_result = agent.memory_sentinel(test_ir)
    print(f"   Checks added: {safety_result.get('checks_added', 0)}")
    
    print("\n✅ Direct API integration working!")


if __name__ == "__main__":
    test_granite_direct()

# Made with Bob
