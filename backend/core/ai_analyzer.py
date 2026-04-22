"""
AI Log Analyzer
Uses OpenAI or Anthropic to perform intelligent analysis of log batches.
Identifies anomalies, security threats, root causes, and recommended actions.
Gracefully degrades when AI keys are missing or the feature is disabled.
"""

import json
import time
import threading
from datetime import datetime, timezone
from typing import Optional

from config import Config
from utils.logger import setup_logger

logger = setup_logger("ai_analyzer", "logs/ai_analyzer.log")


# ── System prompt for AI analysis ────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert DevOps and Security Engineer AI assistant.
You will receive a batch of structured log entries from a production application.

Analyze the logs and return a JSON response with the following structure:
{
  "summary": "Brief overall assessment of the system state",
  "risk_level": "LOW | MEDIUM | HIGH | CRITICAL",
  "anomalies": [
    {
      "type": "error_spike | security_threat | performance_degradation | resource_issue",
      "severity": "WARNING | ERROR | CRITICAL",
      "description": "What was detected",
      "affected_component": "Which part of the system is affected",
      "recommendation": "Specific actionable remediation step"
    }
  ],
  "security_threats": [
    {
      "threat_type": "brute_force | sql_injection | xss | port_scan | privilege_escalation | suspicious_activity",
      "severity": "WARNING | ERROR | CRITICAL",
      "source_ip": "IP address if identifiable",
      "description": "Details of the threat",
      "recommendation": "Specific mitigation action"
    }
  ],
  "performance_insights": {
    "slow_queries": true/false,
    "high_memory": true/false,
    "high_cpu": true/false,
    "api_latency_issues": true/false,
    "details": "Additional context if any issues found"
  },
  "recommended_actions": [
    "Ordered list of prioritized actions to take"
  ]
}

Rules:
- Only return valid JSON, no markdown fences or extra text.
- Be specific and actionable in recommendations.
- If logs are routine with no issues, set risk_level to LOW with an appropriate summary.
- Correlate events: e.g., multiple failed logins from one IP = brute force.
- Consider temporal patterns: error spikes, repeated warnings, etc.
"""


# ── Provider Clients ──────────────────────────────────────────────────────────

class _OpenAIClient:
    """Wrapper for OpenAI chat completion API."""

    def __init__(self):
        self._client = None
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=Config.OPENAI_API_KEY)
            logger.info("OpenAI client initialized — model: %s", Config.OPENAI_MODEL)
        except ImportError:
            logger.error("openai package not installed — run: pip install openai")
        except Exception as exc:
            logger.error("OpenAI client init failed: %s", exc)

    @property
    def available(self) -> bool:
        return self._client is not None and bool(Config.OPENAI_API_KEY)

    def analyze(self, log_text: str) -> Optional[dict]:
        if not self.available:
            return None
        try:
            response = self._client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Analyze these logs:\n\n{log_text}"},
                ],
                temperature=0.2,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            return json.loads(raw)
        except Exception as exc:
            logger.error("OpenAI analysis failed: %s", exc)
            return None


class _AnthropicClient:
    """Wrapper for Anthropic messages API."""

    def __init__(self):
        self._client = None
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
            logger.info("Anthropic client initialized — model: %s", Config.ANTHROPIC_MODEL)
        except ImportError:
            logger.error("anthropic package not installed — run: pip install anthropic")
        except Exception as exc:
            logger.error("Anthropic client init failed: %s", exc)

    @property
    def available(self) -> bool:
        return self._client is not None and bool(Config.ANTHROPIC_API_KEY)

    def analyze(self, log_text: str) -> Optional[dict]:
        if not self.available:
            return None
        try:
            response = self._client.messages.create(
                model=Config.ANTHROPIC_MODEL,
                max_tokens=2000,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": f"Analyze these logs:\n\n{log_text}"},
                ],
            )
            raw = response.content[0].text
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(raw)
        except Exception as exc:
            logger.error("Anthropic analysis failed: %s", exc)
            return None


# ── Fallback rule-based analyzer ──────────────────────────────────────────────

class _RuleBasedAnalyzer:
    """
    Lightweight fallback when no AI provider is available.
    Uses keyword pattern matching to detect obvious anomalies.
    """

    _THREAT_KEYWORDS = {
        "brute_force": ["BRUTE FORCE", "brute force"],
        "sql_injection": ["SQL injection", "sql injection", "OR 1=1", "DROP TABLE", "UNION SELECT"],
        "xss": ["XSS", "xss", "<script>", "onerror="],
        "port_scan": ["port scan", "PORT_SCAN"],
        "privilege_escalation": ["privilege escalation", "PRIVILEGE_ESCALATION"],
    }

    _ERROR_KEYWORDS = ["exception", "failed", "error", "timeout", "unavailable", "out-of-memory"]

    def analyze(self, log_text: str) -> dict:
        lines = log_text.strip().splitlines()
        total = len(lines)

        # Count severities
        errors = sum(1 for l in lines if '"ERROR"' in l or '"CRITICAL"' in l)
        warnings = sum(1 for l in lines if '"WARNING"' in l)

        # Detect threats
        threats = []
        for threat_type, keywords in self._THREAT_KEYWORDS.items():
            for kw in keywords:
                if kw in log_text:
                    threats.append({
                        "threat_type": threat_type,
                        "severity": "CRITICAL",
                        "source_ip": "see logs",
                        "description": f"Detected {threat_type.replace('_', ' ')} pattern in logs",
                        "recommendation": f"Investigate and block offending IPs; review {threat_type} defenses",
                    })
                    break  # one entry per threat type

        # Determine risk level
        if threats or errors >= 5:
            risk = "CRITICAL" if threats else "HIGH"
        elif errors >= 2 or warnings >= 5:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        # Error-based anomalies
        anomalies = []
        if errors > 0:
            anomalies.append({
                "type": "error_spike",
                "severity": "ERROR" if errors >= 3 else "WARNING",
                "description": f"{errors}/{total} log entries are errors",
                "affected_component": "application",
                "recommendation": "Review error logs and identify root cause",
            })

        return {
            "summary": f"Analyzed {total} log entries: {errors} errors, {warnings} warnings, {len(threats)} security threats.",
            "risk_level": risk,
            "anomalies": anomalies,
            "security_threats": threats,
            "performance_insights": {
                "slow_queries": "slow" in log_text.lower() or "query" in log_text.lower(),
                "high_memory": "memory" in log_text.lower(),
                "high_cpu": "cpu" in log_text.lower(),
                "api_latency_issues": "latency" in log_text.lower() or "P99" in log_text,
                "details": "Rule-based analysis (AI provider unavailable)",
            },
            "recommended_actions": [
                "Review error logs for root cause analysis",
                "Block IPs associated with security threats",
                "Monitor resource utilization trends",
            ],
            "_analysis_mode": "rule_based",
        }


# ── Public AI Analyzer ───────────────────────────────────────────────────────

class AIAnalyzer:
    """
    Unified AI analysis interface.

    • Selects the configured AI provider (OpenAI / Anthropic)
    • Falls back to rule-based analysis when AI is unavailable
    • Maintains an in-memory history of recent analyses for the dashboard
    • Thread-safe
    """

    _MAX_HISTORY = 100

    def __init__(self):
        self._lock = threading.Lock()
        self._history: list[dict] = []
        self._provider = None
        self._fallback = _RuleBasedAnalyzer()

        if Config.ENABLE_AI_ANALYSIS:
            if Config.AI_PROVIDER == "openai":
                self._provider = _OpenAIClient()
            elif Config.AI_PROVIDER == "anthropic":
                self._provider = _AnthropicClient()
            else:
                logger.warning("Unknown AI_PROVIDER '%s' — using rule-based fallback", Config.AI_PROVIDER)

            if self._provider and not self._provider.available:
                logger.warning("AI provider '%s' not available — using rule-based fallback", Config.AI_PROVIDER)
                self._provider = None
        else:
            logger.info("AI analysis is disabled via config")

    def analyze(self, log_lines: list[str]) -> dict:
        """
        Analyze a batch of log lines.

        Returns a structured analysis result dict.
        """
        log_text = "\n".join(log_lines)
        start = time.time()

        result = None
        if self._provider:
            result = self._provider.analyze(log_text)

        # Fallback to rule-based if AI failed or is unavailable
        if result is None:
            result = self._fallback.analyze(log_text)

        elapsed = round(time.time() - start, 2)

        # Enrich result with metadata
        result["analyzed_at"] = datetime.now(timezone.utc).isoformat()
        result["log_lines_count"] = len(log_lines)
        result["analysis_time_seconds"] = elapsed
        result["provider"] = (
            Config.AI_PROVIDER if self._provider else "rule_based"
        )

        # Store in history
        with self._lock:
            self._history.append(result)
            if len(self._history) > self._MAX_HISTORY:
                self._history = self._history[-self._MAX_HISTORY:]

        logger.info(
            "Analysis complete: risk=%s, anomalies=%d, threats=%d (%.2fs)",
            result.get("risk_level", "?"),
            len(result.get("anomalies", [])),
            len(result.get("security_threats", [])),
            elapsed,
        )

        return result

    def get_history(self, limit: int = 20) -> list[dict]:
        """Return recent analysis results, most recent first."""
        with self._lock:
            return list(reversed(self._history))[:limit]

    def get_latest(self) -> Optional[dict]:
        """Return the most recent analysis or None."""
        with self._lock:
            return self._history[-1] if self._history else None
