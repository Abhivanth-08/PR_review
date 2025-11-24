"""
Multi-Agent PR Review System
Each agent specializes in a specific aspect of code review
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnablePassthrough
from custom_wrapper import OpenRouterChat
from models import (
    LogicAnalysisOutput, SecurityAnalysisOutput,
    PerformanceAnalysisOutput, ReadabilityAnalysisOutput,
    TestingAnalysisOutput, ReviewIssue, IssueCategory, Severity
)
from typing import Dict, Any
import os


class BaseAgent:
    """Base class for review agents"""

    def __init__(self, api_key: str, model: str = "openai/gpt-4o-mini"):
        self.llm = OpenRouterChat(
            api_key=api_key,
            model=model,
            temperature=0.3,
            max_tokens=2048
        )

    def analyze(self, context: Dict[str, Any]) -> Any:
        """Override in subclasses"""
        raise NotImplementedError


class LogicAnalysisAgent(BaseAgent):
    """Analyzes code logic, potential bugs, and edge cases"""

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.parser = PydanticOutputParser(pydantic_object=LogicAnalysisOutput)

        self.prompt = ChatPromptTemplate.from_template("""
You are an expert code logic analyzer. Review the following code changes for logical errors and bugs.

File: {filename}
Language: {language}
Changes:
{changes}

Full context:
{patch}

Analyze for:
1. Logic errors and potential bugs
2. Missing edge case handling
3. Incorrect conditional logic
4. Off-by-one errors
5. Null/undefined handling
6. Race conditions or concurrency issues
7. State management problems

For each issue found, provide:
- category (use "logic")
- severity (critical/high/medium/low/info)
- line_number (if applicable)
- filename
- code_snippet (the problematic code)
- issue_description (clear explanation)
- recommendation (how to fix)
- reasoning (why this is an issue)

Return ONLY valid JSON matching this structure:
{{
  "issues": [list of ReviewIssue objects],
  "potential_bugs": [list of string descriptions],
  "edge_cases_missing": [list of string descriptions]
}}

Be thorough but focus on real issues, not style preferences.
""")

        self.chain = (
            {"filename": lambda x: x["filename"],
             "language": lambda x: x["language"],
             "changes": lambda x: x["changes"],
             "patch": lambda x: x["patch"]}
            | self.prompt
            | self.llm
            | self.parser
        )

    def analyze(self, context: Dict[str, Any]) -> LogicAnalysisOutput:
        try:
            result = self.chain.invoke(context)
            return result
        except Exception as e:
            print(f"Logic analysis error: {e}")
            return LogicAnalysisOutput()


class SecurityAnalysisAgent(BaseAgent):
    """Identifies security vulnerabilities"""

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.parser = PydanticOutputParser(pydantic_object=SecurityAnalysisOutput)

        self.prompt = ChatPromptTemplate.from_template("""
You are a security expert reviewing code for vulnerabilities.

File: {filename}
Language: {language}
Changes:
{changes}

Full context:
{patch}

Scan for security issues:
1. SQL injection vulnerabilities
2. XSS (Cross-Site Scripting) risks
3. Authentication/Authorization flaws
4. Sensitive data exposure
5. Insecure cryptography
6. Command injection
7. Path traversal
8. Insecure dependencies
9. Hardcoded secrets/credentials
10. CSRF vulnerabilities
11. Improper input validation
12. Insecure deserialization

Provide:
- security_score (0-100, 100 being most secure)
- vulnerabilities (list of ReviewIssue objects with category="security")
- critical_issues (list of critical security concerns as strings)

Return ONLY valid JSON:
{{
  "vulnerabilities": [list of ReviewIssue objects],
  "security_score": integer,
  "critical_issues": [list of strings]
}}

Be paranoid but accurate. Flag real security risks.
""")

        self.chain = (
            {"filename": lambda x: x["filename"],
             "language": lambda x: x["language"],
             "changes": lambda x: x["changes"],
             "patch": lambda x: x["patch"]}
            | self.prompt
            | self.llm
            | self.parser
        )

    def analyze(self, context: Dict[str, Any]) -> SecurityAnalysisOutput:
        try:
            result = self.chain.invoke(context)
            return result
        except Exception as e:
            print(f"Security analysis error: {e}")
            return SecurityAnalysisOutput(security_score=50)


class PerformanceAnalysisAgent(BaseAgent):
    """Analyzes performance implications"""

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.parser = PydanticOutputParser(pydantic_object=PerformanceAnalysisOutput)

        self.prompt = ChatPromptTemplate.from_template("""
You are a performance optimization expert.

File: {filename}
Language: {language}
Changes:
{changes}

Full context:
{patch}

Analyze for performance issues:
1. Algorithmic complexity (O(n²), O(n³))
2. Unnecessary loops or iterations
3. Memory leaks
4. Inefficient data structures
5. Database query optimization
6. Network call efficiency
7. Caching opportunities
8. Resource cleanup
9. Synchronous blocking operations
10. Large payload handling

Provide:
- bottlenecks (ReviewIssue objects with category="performance")
- optimization_suggestions (concrete improvement ideas)
- complexity_warnings (algorithmic complexity concerns)

Return ONLY valid JSON:
{{
  "bottlenecks": [list of ReviewIssue objects],
  "optimization_suggestions": [list of strings],
  "complexity_warnings": [list of strings]
}}

Focus on measurable performance impacts.
""")

        self.chain = (
            {"filename": lambda x: x["filename"],
             "language": lambda x: x["language"],
             "changes": lambda x: x["changes"],
             "patch": lambda x: x["patch"]}
            | self.prompt
            | self.llm
            | self.parser
        )

    def analyze(self, context: Dict[str, Any]) -> PerformanceAnalysisOutput:
        try:
            result = self.chain.invoke(context)
            return result
        except Exception as e:
            print(f"Performance analysis error: {e}")
            return PerformanceAnalysisOutput()


class ReadabilityAnalysisAgent(BaseAgent):
    """Reviews code readability and maintainability"""

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.parser = PydanticOutputParser(pydantic_object=ReadabilityAnalysisOutput)

        self.prompt = ChatPromptTemplate.from_template("""
You are a code readability and maintainability expert.

File: {filename}
Language: {language}
Changes:
{changes}

Full context:
{patch}

Evaluate:
1. Code clarity and simplicity
2. Naming conventions (variables, functions, classes)
3. Function/method length and complexity
4. Code duplication
5. Comment quality and necessity
6. Documentation completeness
7. Consistent formatting
8. Magic numbers/strings
9. Code organization

Provide:
- readability_score (0-100, 100 being most readable)
- style_issues (ReviewIssue objects with category="readability")
- naming_suggestions (specific naming improvements)
- documentation_needed (areas lacking documentation)

Return ONLY valid JSON:
{{
  "style_issues": [list of ReviewIssue objects],
  "naming_suggestions": [list of strings],
  "documentation_needed": [list of strings],
  "readability_score": integer
}}

Be constructive and focus on maintainability.
""")

        self.chain = (
            {"filename": lambda x: x["filename"],
             "language": lambda x: x["language"],
             "changes": lambda x: x["changes"],
             "patch": lambda x: x["patch"]}
            | self.prompt
            | self.llm
            | self.parser
        )

    def analyze(self, context: Dict[str, Any]) -> ReadabilityAnalysisOutput:
        try:
            result = self.chain.invoke(context)
            return result
        except Exception as e:
            print(f"Readability analysis error: {e}")
            return ReadabilityAnalysisOutput(readability_score=50)


class TestingAnalysisAgent(BaseAgent):
    """Evaluates test coverage and quality"""

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.parser = PydanticOutputParser(pydantic_object=TestingAnalysisOutput)

        self.prompt = ChatPromptTemplate.from_template("""
You are a testing and quality assurance expert.

File: {filename}
Language: {language}
Changes:
{changes}

Full context:
{patch}

Analyze testing aspects:
1. Test coverage for new code
2. Missing test cases
3. Edge case testing
4. Unit vs integration test needs
5. Test quality and assertions
6. Mock/stub usage
7. Test naming and organization
8. Test maintenance concerns

Return ONLY valid JSON with this EXACT structure:
{{
  "missing_tests": ["test description 1", "test description 2"],
  "test_coverage_concerns": ["concern 1", "concern 2"],
  "test_quality_issues": [
    {{
      "category": "testing",
      "severity": "high",
      "line_number": null,
      "filename": "{filename}",
      "code_snippet": "relevant code here",
      "issue_description": "clear description of the issue",
      "recommendation": "how to fix it",
      "reasoning": "why this matters"
    }}
  ]
}}

CRITICAL: Each test_quality_issues item MUST include ALL fields:
- category (always "testing")
- severity (critical/high/medium/low/info)
- line_number (number or null)
- filename (the actual filename)
- code_snippet (the problematic code)
- issue_description (what's wrong)
- recommendation (how to fix)
- reasoning (why it matters)

Help ensure robust testing.
""")

        self.chain = (
            {"filename": lambda x: x["filename"],
             "language": lambda x: x["language"],
             "changes": lambda x: x["changes"],
             "patch": lambda x: x["patch"]}
            | self.prompt
            | self.llm
            | self.parser
        )

    def analyze(self, context: Dict[str, Any]) -> TestingAnalysisOutput:
        try:
            result = self.chain.invoke(context)
            return result
        except Exception as e:
            print(f"Testing analysis error: {e}")
            # Return empty but valid output on parsing failure
            return TestingAnalysisOutput(
                missing_tests=[],
                test_coverage_concerns=[],
                test_quality_issues=[]
            )