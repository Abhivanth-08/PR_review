"""
Orchestrator for coordinating multiple review agents
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from agents import (
    LogicAnalysisAgent, SecurityAnalysisAgent,
    PerformanceAnalysisAgent, ReadabilityAnalysisAgent,
    TestingAnalysisAgent
)
from models import (
    FileChange, AggregatedReview, ReviewIssue,
    Severity, IssueCategory
)
from diff_parser import DiffParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from custom_wrapper import OpenRouterChat
import time


class ReviewOrchestrator:
    """Coordinates multiple specialized agents for comprehensive PR review"""

    def __init__(self, api_key: str):
        self.api_key = api_key

        # Initialize all specialized agents
        self.logic_agent = LogicAnalysisAgent(api_key)
        self.security_agent = SecurityAnalysisAgent(api_key)
        self.performance_agent = PerformanceAnalysisAgent(api_key)
        self.readability_agent = ReadabilityAnalysisAgent(api_key)
        self.testing_agent = TestingAnalysisAgent(api_key)

        # Aggregator LLM
        self.aggregator_llm = OpenRouterChat(
            api_key=api_key,
            model="openai/gpt-4o-mini",
            temperature=0.2,
            max_tokens=3000
        )

        self.parser = DiffParser()

    def review_pr(self, files: List[FileChange]) -> Dict[str, Any]:
        """Orchestrate multi-agent review of all files"""
        start_time = time.time()

        all_analyses = {
            'logic': [],
            'security': [],
            'performance': [],
            'readability': [],
            'testing': []
        }

        # Process each file
        for file_change in files:
            if file_change.status == 'deleted':
                continue

            file_analyses = self._analyze_file(file_change)

            # Aggregate results
            for key in all_analyses:
                if key in file_analyses:
                    all_analyses[key].append(file_analyses[key])

        # Aggregate all issues
        all_issues = self._collect_all_issues(all_analyses)

        # Generate final review
        aggregated_review = self._generate_aggregated_review(
            all_issues,
            all_analyses
        )

        processing_time = time.time() - start_time

        return {
            'review': aggregated_review,
            'agent_analyses': all_analyses,
            'processing_time': processing_time
        }

    def _analyze_file(self, file_change: FileChange) -> Dict[str, Any]:
        """Analyze a single file with all agents in parallel"""

        # Extract language from filename
        language = self.parser.get_file_extension(file_change.filename)

        # Get changed lines for context
        changed_lines = self.parser.extract_changed_lines(file_change.patch)
        changes_text = '\n'.join([line['raw'] for line in changed_lines])

        context = {
            'filename': file_change.filename,
            'language': language,
            'changes': changes_text,
            'patch': file_change.patch
        }

        results = {}

        # Run agents in parallel for faster processing
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self.logic_agent.analyze, context): 'logic',
                executor.submit(self.security_agent.analyze, context): 'security',
                executor.submit(self.performance_agent.analyze, context): 'performance',
                executor.submit(self.readability_agent.analyze, context): 'readability',
                executor.submit(self.testing_agent.analyze, context): 'testing'
            }

            for future in as_completed(futures):
                agent_name = futures[future]
                try:
                    results[agent_name] = future.result()
                except Exception as e:
                    print(f"Agent {agent_name} failed: {e}")
                    results[agent_name] = None

        return results

    def _collect_all_issues(self, analyses: Dict[str, List]) -> List[ReviewIssue]:
        """Collect all issues from agent analyses"""
        all_issues = []

        # Logic issues
        for analysis in analyses.get('logic', []):
            if analysis and hasattr(analysis, 'issues'):
                all_issues.extend(analysis.issues)

        # Security issues
        for analysis in analyses.get('security', []):
            if analysis and hasattr(analysis, 'vulnerabilities'):
                all_issues.extend(analysis.vulnerabilities)

        # Performance issues
        for analysis in analyses.get('performance', []):
            if analysis and hasattr(analysis, 'bottlenecks'):
                all_issues.extend(analysis.bottlenecks)

        # Readability issues
        for analysis in analyses.get('readability', []):
            if analysis and hasattr(analysis, 'style_issues'):
                all_issues.extend(analysis.style_issues)

        # Testing issues
        for analysis in analyses.get('testing', []):
            if analysis and hasattr(analysis, 'test_quality_issues'):
                all_issues.extend(analysis.test_quality_issues)

        return all_issues

    def _generate_aggregated_review(
            self,
            all_issues: List[ReviewIssue],
            analyses: Dict[str, List]
    ) -> AggregatedReview:
        """Generate final aggregated review with LLM"""

        # Categorize issues
        critical_blockers = [
            issue for issue in all_issues
            if issue.severity in [Severity.CRITICAL, Severity.HIGH]
        ]

        # Count by category
        summary_by_category = {}
        for issue in all_issues:
            category = issue.category.value if hasattr(issue.category, 'value') else str(issue.category)
            summary_by_category[category] = summary_by_category.get(category, 0) + 1

        # Determine approval status
        if any(issue.severity == Severity.CRITICAL for issue in all_issues):
            approval_status = "CHANGES_REQUESTED"
        elif critical_blockers:
            approval_status = "CHANGES_REQUESTED"
        elif all_issues:
            approval_status = "COMMENTED"
        else:
            approval_status = "APPROVED"

        # Generate overall assessment with LLM
        parser = PydanticOutputParser(pydantic_object=AggregatedReview)

        prompt = ChatPromptTemplate.from_template("""
You are a senior code reviewer aggregating findings from multiple review agents.

Total Issues Found: {total_issues}
Critical Blockers: {critical_count}
Issues by Category: {category_summary}

All Issues (with full details):
{issues_detail}

Agent Insights:
{agent_insights}

Generate a comprehensive review summary. CRITICAL: Each ReviewIssue object MUST have ALL these fields:
- category: string (one of: logic, security, performance, readability, best_practices, testing, documentation)
- severity: string (one of: critical, high, medium, low, info)
- line_number: integer or null
- filename: string (the file path)
- code_snippet: string (the problematic code)
- issue_description: string (what the issue is)
- recommendation: string (how to fix it)
- reasoning: string (why this matters)

The response structure:
1. overall_assessment: string (2-3 sentences on code quality)
2. approval_status: string (use exactly: {approval_status})
3. critical_blockers: array of ReviewIssue objects (each with ALL 8 fields above)
4. all_issues: array of ReviewIssue objects (each with ALL 8 fields above)
5. strengths: array of strings (2-3 positive aspects)
6. summary_by_category: object with category names as keys and counts as values
7. priority_actions: array of strings (3-5 actionable items)

IMPORTANT: When creating ReviewIssue objects, use the actual issue data from the issues_detail above. 
Extract filename, code_snippet, and other details from the original issues. If information is missing, 
use reasonable defaults but ensure ALL 8 fields are present.

Return ONLY valid JSON matching this exact structure.
""")

        # Prepare context with full issue details
        issues_detail = '\n'.join([
            f"Issue {i+1}:\n"
            f"  - category: {issue.category.value}\n"
            f"  - severity: {issue.severity.value}\n"
            f"  - filename: {issue.filename}\n"
            f"  - line_number: {issue.line_number}\n"
            f"  - code_snippet: {issue.code_snippet[:200] if issue.code_snippet else 'N/A'}\n"
            f"  - issue_description: {issue.issue_description}\n"
            f"  - recommendation: {issue.recommendation}\n"
            f"  - reasoning: {issue.reasoning}\n"
            for i, issue in enumerate(all_issues[:15])  # Limit for token size
        ])

        agent_insights = self._summarize_agent_insights(analyses)

        context = {
            'total_issues': len(all_issues),
            'critical_count': len(critical_blockers),
            'category_summary': str(summary_by_category),
            'issues_detail': issues_detail,
            'agent_insights': agent_insights,
            'approval_status': approval_status
        }

        try:
            chain = prompt | self.aggregator_llm | parser
            result = chain.invoke(context)
            # Validate that all issues have required fields
            for issue in result.critical_blockers:
                if not issue.filename or not issue.code_snippet or not issue.issue_description:
                    raise ValueError(f"Invalid ReviewIssue in critical_blockers: missing required fields")
            for issue in result.all_issues:
                if not issue.filename or not issue.code_snippet or not issue.issue_description:
                    raise ValueError(f"Invalid ReviewIssue in all_issues: missing required fields")
            return result
        except Exception as e:
            print(f"Aggregation error: {e}")
            # Return basic review using actual issues (which have all required fields)
            return AggregatedReview(
                overall_assessment="Review completed with automated analysis.",
                approval_status=approval_status,
                critical_blockers=critical_blockers[:10],  # Use actual issues
                all_issues=all_issues[:50],  # Use actual issues
                strengths=["Code changes submitted"] + (["High security score"] if any('security' in str(a) for a in analyses.values()) else []),
                summary_by_category=summary_by_category,
                priority_actions=["Review all flagged issues", "Address critical blockers first", "Improve test coverage"]
            )

    def _summarize_agent_insights(self, analyses: Dict[str, List]) -> str:
        """Summarize key insights from each agent"""
        insights = []

        # Security insights
        security_analyses = analyses.get('security', [])
        if security_analyses:
            scores = [a.security_score for a in security_analyses if a and hasattr(a, 'security_score')]
            if scores:
                avg_score = sum(scores) / len(scores)
                insights.append(f"Security Score: {avg_score:.1f}/100")

        # Readability insights
        readability_analyses = analyses.get('readability', [])
        if readability_analyses:
            scores = [a.readability_score for a in readability_analyses if a and hasattr(a, 'readability_score')]
            if scores:
                avg_score = sum(scores) / len(scores)
                insights.append(f"Readability Score: {avg_score:.1f}/100")

        return ', '.join(insights) if insights else "No specific metrics available"

    