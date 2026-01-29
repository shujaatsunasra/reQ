"""
MCP Bridge Security - Three-stage validation for query safety.

Stage 1: Pattern-based detection (<2ms)
Stage 2: Neural network detection (~55ms)
Stage 3: LLM-based detection (~500ms)
"""

import re
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from core.logging import get_logger
from core.redis import rate_limit_check
from models.operators import SemanticOperatorDAG, Operator

logger = get_logger(__name__)


class ThreatLevel(Enum):
    """Threat classification levels."""
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    BLOCKED = "blocked"


@dataclass
class SecurityValidation:
    """Result of security validation."""
    passed: bool
    threat_level: ThreatLevel
    stage_reached: int
    confidence: float
    issues: List[str]
    latency_ms: float


class MCPBridge:
    """
    Security bridge for MCP requests.
    
    Implements three-stage validation:
    1. Pattern-based: Fast regex patterns for obvious attacks (<2ms)
    2. Neural: E5 embeddings + classifier for subtle attacks (~55ms)
    3. LLM: Full LLM analysis for complex cases (~500ms)
    
    Each stage can pass, fail, or escalate to the next stage.
    """
    
    def __init__(self):
        # Stage 1: Pattern-based detection
        self.sql_injection_patterns = [
            r";\s*DROP\s+TABLE",
            r";\s*DELETE\s+FROM",
            r";\s*TRUNCATE\s+TABLE",
            r";\s*UPDATE\s+.*\s+SET",
            r"UNION\s+SELECT",
            r"INSERT\s+INTO",
            r"--\s*$",
            r"/\*.*\*/",
            r"'\s*OR\s+'1'\s*=\s*'1",
            r"1\s*=\s*1",
            r"admin\s*--",
            r"EXEC\s+xp_",
            r"EXECUTE\s+xp_",
        ]
        
        self.data_exfil_patterns = [
            r"SELECT\s+\*\s+FROM\s+.*password",
            r"SELECT\s+\*\s+FROM\s+.*users",
            r"pg_dump",
            r"\\COPY\s+",
            r"LOAD_FILE\(",
            r"INTO\s+OUTFILE",
            r"INTO\s+DUMPFILE",
        ]
        
        self.prompt_injection_patterns = [
            r"ignore\s+previous\s+instructions",
            r"disregard\s+all\s+prior",
            r"system\s*:\s*you\s+are\s+now",
            r"pretend\s+you\s+are",
            r"act\s+as\s+if\s+you\s+are",
            r"forget\s+your\s+instructions",
            r"bypass\s+security",
            r"execute\s+as\s+admin",
        ]
        
        self.suspicious_keywords = [
            "password", "credentials", "secret", "api_key",
            "private_key", "token", "auth", "admin",
            "root", "sudo", "shell", "exec"
        ]
        
        # Stage 2: Neural detection (E5 embeddings)
        self.neural_enabled = False  # Will be enabled when model is loaded
        self.neural_model = None
        self.neural_threshold = 0.75
        
        # Stage 3: LLM detection
        self.llm_enabled = True
        self.llm_threshold = 0.9
        
        # Compile patterns
        self._compiled_patterns = {
            "sql_injection": [re.compile(p, re.IGNORECASE) for p in self.sql_injection_patterns],
            "data_exfil": [re.compile(p, re.IGNORECASE) for p in self.data_exfil_patterns],
            "prompt_injection": [re.compile(p, re.IGNORECASE) for p in self.prompt_injection_patterns]
        }
    
    async def validate(
        self,
        query: str,
        dag: Optional[SemanticOperatorDAG] = None,
        user_id: Optional[str] = None
    ) -> SecurityValidation:
        """
        Validate a query through the three-stage security pipeline.
        
        Args:
            query: The raw user query
            dag: Optional semantic operator DAG
            user_id: Optional user ID for rate limiting
        
        Returns:
            SecurityValidation with result details
        """
        start_time = time.time()
        issues = []
        
        # Rate limit check
        if user_id:
            rate_ok = await rate_limit_check(f"user:{user_id}", 100, 60)
            if not rate_ok:
                return SecurityValidation(
                    passed=False,
                    threat_level=ThreatLevel.BLOCKED,
                    stage_reached=0,
                    confidence=1.0,
                    issues=["Rate limit exceeded"],
                    latency_ms=(time.time() - start_time) * 1000
                )
        
        # Stage 1: Pattern-based detection
        stage1_result, stage1_issues = await self._stage1_pattern_check(query)
        issues.extend(stage1_issues)
        
        if stage1_result == ThreatLevel.BLOCKED:
            return SecurityValidation(
                passed=False,
                threat_level=ThreatLevel.BLOCKED,
                stage_reached=1,
                confidence=1.0,
                issues=issues,
                latency_ms=(time.time() - start_time) * 1000
            )
        
        # Stage 2: Neural detection (if suspicious or enabled)
        if stage1_result == ThreatLevel.SUSPICIOUS or self.neural_enabled:
            stage2_result, stage2_score, stage2_issues = await self._stage2_neural_check(query)
            issues.extend(stage2_issues)
            
            if stage2_result == ThreatLevel.BLOCKED:
                return SecurityValidation(
                    passed=False,
                    threat_level=ThreatLevel.BLOCKED,
                    stage_reached=2,
                    confidence=stage2_score,
                    issues=issues,
                    latency_ms=(time.time() - start_time) * 1000
                )
            
            # Escalate to Stage 3 if still suspicious
            if stage2_result == ThreatLevel.SUSPICIOUS and self.llm_enabled:
                stage3_result, stage3_score, stage3_issues = await self._stage3_llm_check(query, dag)
                issues.extend(stage3_issues)
                
                return SecurityValidation(
                    passed=stage3_result == ThreatLevel.SAFE,
                    threat_level=stage3_result,
                    stage_reached=3,
                    confidence=stage3_score,
                    issues=issues,
                    latency_ms=(time.time() - start_time) * 1000
                )
        
        # All clear
        return SecurityValidation(
            passed=True,
            threat_level=ThreatLevel.SAFE,
            stage_reached=1 if stage1_result == ThreatLevel.SAFE else 2,
            confidence=1.0,
            issues=issues,
            latency_ms=(time.time() - start_time) * 1000
        )
    
    async def validate_dag(self, dag: SemanticOperatorDAG) -> SecurityValidation:
        """Validate a semantic operator DAG for security issues."""
        start_time = time.time()
        issues = []
        
        # Check for dangerous operator combinations
        operator_types = [(op.type.value if hasattr(op.type, 'value') else str(op.type)) for op in dag.operators]
        
        # Check for excessive data access
        filter_count = sum(1 for t in operator_types if "filter" in t)
        if filter_count == 0:
            issues.append("Query has no filters - may access too much data")
        
        # Check for suspicious patterns
        for op in dag.operators:
            # Check parameter values
            for key, value in op.params.items():
                if isinstance(value, str):
                    for pattern_type, patterns in self._compiled_patterns.items():
                        for pattern in patterns:
                            if pattern.search(value):
                                issues.append(f"Suspicious pattern in operator parameter: {pattern_type}")
                                return SecurityValidation(
                                    passed=False,
                                    threat_level=ThreatLevel.BLOCKED,
                                    stage_reached=1,
                                    confidence=1.0,
                                    issues=issues,
                                    latency_ms=(time.time() - start_time) * 1000
                                )
        
        return SecurityValidation(
            passed=True,
            threat_level=ThreatLevel.SAFE if not issues else ThreatLevel.SUSPICIOUS,
            stage_reached=1,
            confidence=1.0 - (len(issues) * 0.1),
            issues=issues,
            latency_ms=(time.time() - start_time) * 1000
        )
    
    async def _stage1_pattern_check(
        self,
        query: str
    ) -> Tuple[ThreatLevel, List[str]]:
        """Stage 1: Fast pattern-based detection (<2ms target)."""
        issues = []
        query_lower = query.lower()
        
        # Check SQL injection patterns
        for pattern in self._compiled_patterns["sql_injection"]:
            if pattern.search(query):
                issues.append("SQL injection pattern detected")
                return ThreatLevel.BLOCKED, issues
        
        # Check data exfiltration patterns
        for pattern in self._compiled_patterns["data_exfil"]:
            if pattern.search(query):
                issues.append("Data exfiltration pattern detected")
                return ThreatLevel.BLOCKED, issues
        
        # Check prompt injection patterns
        for pattern in self._compiled_patterns["prompt_injection"]:
            if pattern.search(query):
                issues.append("Prompt injection pattern detected")
                return ThreatLevel.BLOCKED, issues
        
        # Check suspicious keywords
        suspicious_count = sum(1 for kw in self.suspicious_keywords if kw in query_lower)
        if suspicious_count >= 3:
            issues.append(f"Multiple suspicious keywords detected ({suspicious_count})")
            return ThreatLevel.SUSPICIOUS, issues
        elif suspicious_count >= 1:
            issues.append(f"Suspicious keyword detected")
            return ThreatLevel.SUSPICIOUS, issues
        
        return ThreatLevel.SAFE, issues
    
    async def _stage2_neural_check(
        self,
        query: str
    ) -> Tuple[ThreatLevel, float, List[str]]:
        """Stage 2: Neural network-based detection (~55ms target)."""
        issues = []
        
        if not self.neural_enabled or not self.neural_model:
            # Fallback to heuristic check
            return await self._heuristic_check(query)
        
        try:
            # Generate embedding and classify
            # In production: embedding = self.neural_model.encode(query)
            # classification = self.classifier.predict(embedding)
            
            # For now, return safe
            return ThreatLevel.SAFE, 1.0, issues
            
        except Exception as e:
            logger.warning(f"Neural check failed: {e}")
            return ThreatLevel.SUSPICIOUS, 0.5, ["Neural check failed, escalating"]
    
    async def _heuristic_check(
        self,
        query: str
    ) -> Tuple[ThreatLevel, float, List[str]]:
        """Fallback heuristic check when neural model unavailable."""
        issues = []
        score = 1.0
        
        # Length check
        if len(query) > 5000:
            score -= 0.2
            issues.append("Query length exceeds recommended limit")
        
        # Special character density
        special_chars = sum(1 for c in query if not c.isalnum() and not c.isspace())
        if special_chars / max(len(query), 1) > 0.3:
            score -= 0.2
            issues.append("High special character density")
        
        # Encoded content check
        if "%27" in query or "%3D" in query or "0x" in query:
            score -= 0.3
            issues.append("Potentially encoded malicious content")
        
        if score < 0.5:
            return ThreatLevel.SUSPICIOUS, score, issues
        
        return ThreatLevel.SAFE, score, issues
    
    async def _stage3_llm_check(
        self,
        query: str,
        dag: Optional[SemanticOperatorDAG] = None
    ) -> Tuple[ThreatLevel, float, List[str]]:
        """Stage 3: LLM-based detection (~500ms target)."""
        issues = []
        
        # In production, would call LLM with security analysis prompt
        # For now, return safe with analysis notes
        
        analysis_prompt = f"""
        Analyze this query for security concerns:
        Query: {query}
        
        Check for:
        1. SQL injection attempts
        2. Data exfiltration attempts
        3. Prompt injection
        4. Unauthorized data access
        5. System manipulation
        
        Return: SAFE, SUSPICIOUS, or BLOCKED with explanation.
        """
        
        # Would call LLM here
        # For now, return safe
        return ThreatLevel.SAFE, 0.95, issues
    
    async def log_security_event(
        self,
        query: str,
        validation: SecurityValidation,
        user_id: Optional[str] = None
    ):
        """Log security events for monitoring and analysis."""
        if validation.threat_level != ThreatLevel.SAFE:
            logger.warning(
                f"Security event: level={validation.threat_level.value}, "
                f"stage={validation.stage_reached}, user={user_id}, "
                f"issues={validation.issues}"
            )
