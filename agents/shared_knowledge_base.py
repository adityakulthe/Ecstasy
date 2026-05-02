#!/usr/bin/env python3
"""
Shared Knowledge Base for Agent Coordination
Enables all 9 agents to share insights, avoid conflicts, and coordinate work
"""

import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


class ConflictType(Enum):
    """Types of conflicts between agents"""
    SAFETY_VIOLATION = "safety_violation"
    DUPLICATE_WORK = "duplicate_work"
    INCOMPATIBLE_TRANSFORMS = "incompatible_transforms"
    OPTIMIZATION_CONFLICT = "optimization_conflict"


class ResolutionStrategy(Enum):
    """Conflict resolution strategies"""
    PRIORITIZE_SAFETY = "prioritize_safety"
    SKIP_DUPLICATE = "skip_duplicate"
    MERGE_TRANSFORMS = "merge_transforms"
    APPLY_LATER = "apply_later"
    MANUAL_REVIEW = "manual_review"


@dataclass
class IRVersion:
    """Tracks evolution of IR through pipeline"""
    version: int
    agent: str
    timestamp: str
    ir_code: str
    changes: List[str]
    hash: str
    
    @staticmethod
    def compute_hash(ir_code: str) -> str:
        return hashlib.sha256(ir_code.encode()).hexdigest()[:16]


@dataclass
class AgentInsight:
    """Insights discovered by an agent"""
    agent_id: str
    timestamp: str
    optimizations_applied: List[str] = field(default_factory=list)
    opportunities_found: List[str] = field(default_factory=list)
    vulnerabilities_found: List[str] = field(default_factory=list)
    constraints_added: List[str] = field(default_factory=list)
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Transformation:
    """Record of a transformation applied"""
    id: str
    agent: str
    type: str
    description: str
    from_pattern: Optional[str] = None
    to_pattern: Optional[str] = None
    verified: bool = False
    conflicts_with: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)


@dataclass
class Conflict:
    """Detected conflict between agents"""
    id: str
    agents: List[str]
    type: ConflictType
    description: str
    resolution: Optional[ResolutionStrategy] = None
    resolved: bool = False
    resolution_details: Optional[str] = None


class SharedKnowledgeBase:
    """
    Centralized knowledge repository for all agents
    Enables coordination, conflict detection, and knowledge sharing
    """
    
    def __init__(self):
        """Initialize empty knowledge base"""
        self.ir_versions: List[IRVersion] = []
        self.agent_insights: Dict[str, AgentInsight] = {}
        self.transformations: List[Transformation] = []
        self.conflicts: List[Conflict] = []
        self.optimization_targets: Dict[str, List[str]] = {}
        self.safety_issues: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, Any] = {}
        self.verification_results: Dict[str, Any] = {}
        self.registered_agents: Set[str] = set()
        self._transformation_counter = 0
        self._conflict_counter = 0
    
    def register_agent(self, agent_id: str, capabilities: List[str]) -> None:
        """Register an agent with the knowledge base"""
        self.registered_agents.add(agent_id)
        print(f"  📝 Agent '{agent_id}' registered with KB")
        print(f"     Capabilities: {', '.join(capabilities)}")
    
    def add_ir_version(self, agent: str, ir_code: str, changes: List[str]) -> IRVersion:
        """Add a new IR version to the history"""
        version = IRVersion(
            version=len(self.ir_versions) + 1,
            agent=agent,
            timestamp=datetime.utcnow().isoformat(),
            ir_code=ir_code,
            changes=changes,
            hash=IRVersion.compute_hash(ir_code)
        )
        self.ir_versions.append(version)
        return version
    
    def publish_insight(self, insight: AgentInsight) -> None:
        """Agent publishes its findings to the knowledge base"""
        self.agent_insights[insight.agent_id] = insight
        print(f"  💡 {insight.agent_id} published insights:")
        if insight.optimizations_applied:
            print(f"     ✓ Applied: {', '.join(insight.optimizations_applied)}")
        if insight.opportunities_found:
            print(f"     🎯 Found: {', '.join(insight.opportunities_found)}")
        if insight.vulnerabilities_found:
            print(f"     ⚠️  Vulnerabilities: {', '.join(insight.vulnerabilities_found)}")
    
    def add_transformation(self, transformation: Transformation) -> None:
        """Record a transformation"""
        self.transformations.append(transformation)
    
    def has_optimization(self, optimization_type: str) -> bool:
        """Check if an optimization has already been applied"""
        for insight in self.agent_insights.values():
            if optimization_type in insight.optimizations_applied:
                return True
        return False
    
    def get_constraints(self, category: str) -> List[str]:
        """Get all constraints in a category"""
        constraints = []
        for insight in self.agent_insights.values():
            constraints.extend(insight.constraints_added)
        return constraints
    
    def detect_conflicts(self) -> List[Conflict]:
        """Detect conflicts between agent outputs"""
        new_conflicts = []
        
        # Check for safety violations
        safety_constraints = self.get_constraints("memory_safety")
        for insight in self.agent_insights.values():
            for opt in insight.optimizations_applied:
                if "remove_bounds_check" in opt and safety_constraints:
                    conflict = self._create_conflict(
                        agents=[insight.agent_id, "memory_sentinel"],
                        type=ConflictType.SAFETY_VIOLATION,
                        description=f"{opt} violates safety constraints"
                    )
                    new_conflicts.append(conflict)
        
        # Check for duplicate work
        seen_optimizations = {}
        for agent_id, insight in self.agent_insights.items():
            for opt in insight.optimizations_applied:
                if opt in seen_optimizations:
                    conflict = self._create_conflict(
                        agents=[agent_id, seen_optimizations[opt]],
                        type=ConflictType.DUPLICATE_WORK,
                        description=f"Both agents applied {opt}"
                    )
                    new_conflicts.append(conflict)
                else:
                    seen_optimizations[opt] = agent_id
        
        self.conflicts.extend(new_conflicts)
        return new_conflicts
    
    def _create_conflict(self, agents: List[str], type: ConflictType, description: str) -> Conflict:
        """Create a new conflict record"""
        self._conflict_counter += 1
        return Conflict(
            id=f"conflict_{self._conflict_counter:03d}",
            agents=agents,
            type=type,
            description=description
        )
    
    def resolve_conflict(self, conflict: Conflict, strategy: ResolutionStrategy) -> None:
        """Apply resolution strategy to a conflict"""
        conflict.resolution = strategy
        conflict.resolved = True
        
        if strategy == ResolutionStrategy.PRIORITIZE_SAFETY:
            conflict.resolution_details = "Safety constraints take precedence"
        elif strategy == ResolutionStrategy.SKIP_DUPLICATE:
            conflict.resolution_details = "Duplicate work skipped"
        elif strategy == ResolutionStrategy.MERGE_TRANSFORMS:
            conflict.resolution_details = "Transformations merged"
        
        print(f"  ✅ Resolved {conflict.id}: {strategy.value}")
    
    def get_snapshot(self, agent_id: str) -> Dict[str, Any]:
        """Get current knowledge base snapshot for an agent"""
        return {
            "ir_versions": len(self.ir_versions),
            "latest_ir": self.ir_versions[-1] if self.ir_versions else None,
            "other_agents": [a for a in self.registered_agents if a != agent_id],
            "applied_optimizations": [
                opt for insight in self.agent_insights.values()
                for opt in insight.optimizations_applied
            ],
            "safety_constraints": self.get_constraints("memory_safety"),
            "opportunities": [
                opp for insight in self.agent_insights.values()
                for opp in insight.opportunities_found
            ]
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of knowledge base state"""
        return {
            "registered_agents": len(self.registered_agents),
            "ir_versions": len(self.ir_versions),
            "insights_published": len(self.agent_insights),
            "transformations": len(self.transformations),
            "conflicts_detected": len(self.conflicts),
            "conflicts_resolved": sum(1 for c in self.conflicts if c.resolved),
            "agents": list(self.registered_agents)
        }
    
    def print_summary(self) -> None:
        """Print knowledge base summary"""
        summary = self.get_summary()
        print("\n" + "=" * 60)
        print("📚 SHARED KNOWLEDGE BASE SUMMARY")
        print("=" * 60)
        print(f"Registered Agents: {summary['registered_agents']}")
        print(f"IR Versions: {summary['ir_versions']}")
        print(f"Insights Published: {summary['insights_published']}")
        print(f"Transformations: {summary['transformations']}")
        print(f"Conflicts Detected: {summary['conflicts_detected']}")
        print(f"Conflicts Resolved: {summary['conflicts_resolved']}")
        print(f"Active Agents: {', '.join(summary['agents'])}")
        print("=" * 60)


if __name__ == "__main__":
    # Test the knowledge base
    print("Testing Shared Knowledge Base...")
    
    kb = SharedKnowledgeBase()
    
    # Register agents
    kb.register_agent("ir_architect", ["optimization", "dead_code_elimination"])
    kb.register_agent("memory_sentinel", ["safety", "bounds_checking"])
    
    # Publish insights
    kb.publish_insight(AgentInsight(
        agent_id="ir_architect",
        timestamp=datetime.utcnow().isoformat(),
        optimizations_applied=["loop_unrolling", "constant_folding"],
        opportunities_found=["vectorization_candidate"]
    ))
    
    kb.publish_insight(AgentInsight(
        agent_id="memory_sentinel",
        timestamp=datetime.utcnow().isoformat(),
        vulnerabilities_found=["unchecked_array_access"],
        constraints_added=["bounds_checking_required"]
    ))
    
    # Detect conflicts
    conflicts = kb.detect_conflicts()
    print(f"\n✅ Detected {len(conflicts)} conflicts")
    
    # Print summary
    kb.print_summary()

# Made with Bob
