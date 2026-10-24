#!/usr/bin/env python3
"""
Provider-Agnostic Direct LLM Agent Integration
Calls any configured OpenAI-compatible endpoint via UniversalLLMClient.
"""

import json
from typing import Dict, Any
from agents.llm_client import UniversalLLMClient, is_llm_configured


class DirectLLMAgent:
    """
    Provider-agnostic LLM agent for @ir-architect and @memory-sentinel passes.
    """

    def __init__(self) -> None:
        if not is_llm_configured():
            raise ValueError("LLM_API_KEY not found in environment")
        self.client = UniversalLLMClient()

    def call_llm(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 2000,
        temperature: float = 0.1,
    ) -> str:
        """Call configured LLM endpoint and return assistant text."""
        response = self.client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            params={"max_new_tokens": max_tokens, "temperature": temperature},
        )
        return response["choices"][0]["message"]["content"].strip()

    def ir_architect(self, ir_code: str) -> Dict[str, Any]:
        """AI-driven LLVM IR optimization (@ir-architect)."""
        system_prompt = """You are an expert LLVM compiler optimization engineer. Return ONLY valid JSON:
{
  "optimized_ir": "...",
  "transformation_applied": true,
  "transformation_type": "dead code elimination | constant folding | mem2reg",
  "speedup_reasoning": "explanation"
}"""
        user_message = f"Analyze and optimize this LLVM IR code:\n\n```llvm\n{ir_code}\n```"
        try:
            response = self.call_llm(system_prompt, user_message)
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()
            result = json.loads(json_str)
            if "optimized_ir" not in result:
                result["optimized_ir"] = ir_code
                result["transformation_applied"] = False
            return result
        except Exception as e:
            return {
                "optimized_ir": ir_code,
                "transformation_applied": False,
                "transformation_type": "none",
                "speedup_reasoning": f"Error: {str(e)}",
            }

    def memory_sentinel(self, ir_code: str) -> Dict[str, Any]:
        """Memory safety hardening (@memory-sentinel)."""
        system_prompt = """You are an expert in memory safety and secure coding. Return ONLY valid JSON:
{
  "hardened_ir": "...",
  "checks_added": 0,
  "check_locations": [],
  "safety_reasoning": "explanation"
}"""
        user_message = f"Add memory safety checks to this LLVM IR code:\n\n```llvm\n{ir_code}\n```"
        try:
            response = self.call_llm(system_prompt, user_message)
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()
            result = json.loads(json_str)
            if "hardened_ir" not in result:
                result["hardened_ir"] = ir_code
                result["checks_added"] = 0
            return result
        except Exception as e:
            return {
                "hardened_ir": ir_code,
                "checks_added": 0,
                "check_locations": [],
                "safety_reasoning": f"Error: {str(e)}",
            }


# Backward-compatible alias
GraniteDirectAgent = DirectLLMAgent
