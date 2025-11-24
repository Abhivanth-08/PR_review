"""
FastAPI application for PR Review Agent
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import RequestValidationError
from models import PRReviewRequest, PRReviewResponse
from orchestrator import ReviewOrchestrator
from github_client import GitHubClient
from diff_parser import DiffParser
from dotenv import load_dotenv
import os
import uvicorn
from typing import Dict, Any
import uuid
import json
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from custom_wrapper import OpenRouterChat
from langchain_core.prompts import ChatPromptTemplate
from rev import generate_pdf_from_json

# Load environment variables
load_dotenv()

app = FastAPI(
    title="GitHub PR Review Agent",
    description="Automated multi-agent code review system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed messages"""
    errors = exc.errors()
    error_details = []
    for error in errors:
        error_details.append({
            "field": ".".join(str(x) for x in error.get("loc", [])),
            "message": error.get("msg"),
            "type": error.get("type")
        })

    return JSONResponse(
        status_code=400,
        content={
            "detail": "Validation error - check request format",
            "errors": error_details,
            "hint": "Request should be JSON with 'github_url' or 'diff_content' field. Example: {\"github_url\": \"https://github.com/owner/repo/pull/123\"} or {\"diff_content\": \"diff --git ...\"}"
        }
    )

# Global instances
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Optional

if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY must be set in environment")

orchestrator = ReviewOrchestrator(OPENROUTER_API_KEY)
github_client = GitHubClient(GITHUB_TOKEN)
diff_parser = DiffParser()

# Store for async review results
review_results: Dict[str, Dict] = {}


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "operational",
        "service": "PR Review Agent",
        "version": "1.0.0",
        "agents": [
            "Logic Analysis",
            "Security Analysis",
            "Performance Analysis",
            "Readability Analysis",
            "Testing Analysis"
        ]
    }


@app.post("/review/debug")
async def review_pr_debug(request: Request):
    """Debug endpoint to see what's being received"""
    try:
        body = await request.body()
        body_str = body.decode('utf-8') if body else None
        json_body = json.loads(body_str) if body_str else None

        # Try to create PRReviewRequest from the JSON
        try:
            pr_request = PRReviewRequest(**json_body) if json_body else None
            return {
                "received_body": body_str,
                "parsed_json": json_body,
                "pr_request_valid": pr_request is not None,
                "pr_request": pr_request.model_dump() if pr_request and hasattr(pr_request, 'model_dump') else pr_request.dict() if pr_request else None,
                "content_type": request.headers.get("content-type"),
                "method": request.method
            }
        except Exception as e:
            return {
                "received_body": body_str,
                "parsed_json": json_body,
                "pr_request_error": str(e),
                "content_type": request.headers.get("content-type"),
                "method": request.method
            }
    except Exception as e:
        return {
            "error": str(e),
            "body": str(body) if 'body' in locals() else None
        }


@app.post("/review/test")
async def review_pr_test(request: Request):
    """Test endpoint that accepts raw JSON and manually validates"""
    try:
        body = await request.json()

        # Manual validation
        github_url = body.get("github_url")
        diff_content = body.get("diff_content")

        if not github_url and not diff_content:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": "Must provide either 'github_url' or 'diff_content'",
                    "received": body
                }
            )

        # Create PRReviewRequest manually
        pr_request = PRReviewRequest(
            github_url=github_url,
            diff_content=diff_content,
            pr_metadata=body.get("pr_metadata")
        )

        # Now call the actual review function
        return await review_pr(pr_request)

    except json.JSONDecodeError as e:
        return JSONResponse(
            status_code=400,
            content={
                "detail": "Invalid JSON",
                "error": str(e)
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(e),
                "type": type(e).__name__
            }
        )


@app.post("/review")
async def review_pr(request: PRReviewRequest):
    """
    Review a GitHub PR or raw diff content

    Options:
    1. Provide github_url to fetch PR from GitHub
    2. Provide diff_content directly for manual review
    """
    # Log received request for debugging
    print(f"Received request - github_url: {bool(request.github_url)}, diff_content: {bool(request.diff_content)}")

    # Validate request has at least one input
    if not request.github_url and not request.diff_content:
        raise HTTPException(
            status_code=400,
            detail="Must provide either 'github_url' or 'diff_content' in request body"
        )

    pr_metadata = None
    files = []

    # Option 1: GitHub URL
    if request.github_url:
        parsed = github_client.parse_pr_url(request.github_url)
        if not parsed:
            raise HTTPException(
                status_code=400,
                detail="Invalid GitHub PR URL format"
            )

        owner = parsed['owner']
        repo = parsed['repo']
        pr_number = int(parsed['pr_number'])

        # Fetch PR metadata
        pr_metadata = github_client.fetch_pr_metadata(owner, repo, pr_number)
        if not pr_metadata:
            raise HTTPException(
                status_code=404,
                detail="Could not fetch PR metadata from GitHub"
            )

        # Fetch PR files
        files = github_client.fetch_pr_files(owner, repo, pr_number)
        if not files:
            raise HTTPException(
                status_code=404,
                detail="Could not fetch PR files from GitHub"
            )

    # Option 2: Direct diff content
    elif request.diff_content:
        files = diff_parser.parse_diff(request.diff_content)
        if not files:
            raise HTTPException(
                status_code=400,
                detail="Could not parse diff content"
            )

        # Create basic metadata if provided
        if request.pr_metadata:
            pr_metadata = PRMetadata(**request.pr_metadata)

    else:
        raise HTTPException(
            status_code=400,
            detail="Must provide either github_url or diff_content"
        )

    # Perform review
    try:
        review_result = orchestrator.review_pr(files)

        # Serialize agent_analyses (convert Pydantic models to dicts)
        serialized_analyses = {}
        for key, analyses_list in review_result['agent_analyses'].items():
            serialized_analyses[key] = []
            for analysis in analyses_list:
                if analysis:
                    # Convert Pydantic model to dict
                    if hasattr(analysis, 'model_dump'):
                        serialized_analyses[key].append(analysis.model_dump())
                    elif hasattr(analysis, 'dict'):
                        serialized_analyses[key].append(analysis.dict())
                    else:
                        serialized_analyses[key].append(analysis)

        response = PRReviewResponse(
            pr_metadata=pr_metadata,
            review=review_result['review'],
            agent_analyses=serialized_analyses,
            processing_time=review_result['processing_time']
        )

        # Use model_dump for Pydantic v2, or dict() for v1
        try:
            return response.model_dump() if hasattr(response, 'model_dump') else response.dict()
        except:
            return response

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Review processing error: {str(e)}"
        )


@app.post("/review/async")
async def review_pr_async(request: PRReviewRequest, background_tasks: BackgroundTasks):
    """
    Start an asynchronous PR review
    Returns a job_id to check status later
    """
    job_id = str(uuid.uuid4())
    review_results[job_id] = {"status": "processing"}

    background_tasks.add_task(process_review_async, job_id, request)

    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Review started. Check status at /review/status/{job_id}"
    }


async def process_review_async(job_id: str, request: PRReviewRequest):
    """Background task for async review processing"""
    try:
        # Similar logic as review_pr but runs in background
        pr_metadata = None
        files = []

        if request.github_url:
            parsed = github_client.parse_pr_url(request.github_url)
            if parsed:
                owner = parsed['owner']
                repo = parsed['repo']
                pr_number = int(parsed['pr_number'])

                pr_metadata = github_client.fetch_pr_metadata(owner, repo, pr_number)
                files = github_client.fetch_pr_files(owner, repo, pr_number)

        elif request.diff_content:
            files = diff_parser.parse_diff(request.diff_content)
            if request.pr_metadata:
                pr_metadata = PRMetadata(**request.pr_metadata)

        if files:
            review_result = orchestrator.review_pr(files)

            review_results[job_id] = {
                "status": "completed",
                "result": PRReviewResponse(
                    pr_metadata=pr_metadata,
                    review=review_result['review'],
                    agent_analyses=review_result['agent_analyses'],
                    processing_time=review_result['processing_time']
                ).dict()
            }
        else:
            review_results[job_id] = {
                "status": "failed",
                "error": "Could not process PR"
            }

    except Exception as e:
        review_results[job_id] = {
            "status": "failed",
            "error": str(e)
        }


@app.get("/review/status/{job_id}")
async def get_review_status(job_id: str):
    """Check status of async review"""
    if job_id not in review_results:
        raise HTTPException(status_code=404, detail="Job not found")

    return review_results[job_id]


@app.post("/parse-diff")
async def parse_diff_endpoint(diff_content: str):
    """
    Parse a git diff and return structured file changes
    Useful for testing diff parsing
    """
    try:
        files = diff_parser.parse_diff(diff_content)
        return {
            "files_count": len(files),
            "files": [file.dict() for file in files]
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Diff parsing error: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Detailed health check"""
    # Get all registered routes
    routes = [r.path for r in app.routes if hasattr(r, 'path')]
    return {
        "status": "healthy",
        "openrouter_configured": bool(OPENROUTER_API_KEY),
        "github_token_configured": bool(GITHUB_TOKEN),
        "agents_active": 5,
        "registered_routes": sorted(routes),
        "pdf_route_exists": "/generate-pdf" in routes,
        "test_route_exists": "/test-pdf-route" in routes
    }


@app.get("/test-pdf-route")
async def test_pdf_route():
    """Test endpoint to verify PDF route is accessible"""
    return {"message": "PDF route is accessible", "endpoint": "/generate-pdf"}


@app.get("/generate-pdf/test")
async def test_pdf_get():
    """Test GET endpoint for PDF route"""
    return {"message": "PDF endpoint is accessible via GET", "use": "POST /generate-pdf with JSON body"}


@app.post("/format-review")
async def format_review_with_llm(review_data: Dict[str, Any]):
    """
    Format review JSON using LLM to create a human-readable, well-structured report
    """
    try:
        formatter_llm = OpenRouterChat(
            api_key=OPENROUTER_API_KEY,
            model="openai/gpt-4o-mini",
            temperature=0.3,
            max_tokens=4000
        )

        prompt = ChatPromptTemplate.from_template("""
You are a technical documentation expert. Format the following PR review JSON data into a well-structured, 
human-readable markdown report.

The report should include:
1. Executive Summary
2. Overview of findings by category
3. Detailed findings with context
4. Recommendations prioritized by severity
5. Overall assessment

Be clear, concise, and professional. Use proper markdown formatting with headers, lists, and code blocks.

Review Data:
{review_json}

Generate a comprehensive, well-formatted markdown report.
""")

        review_json_str = json.dumps(review_data, indent=2)
        chain = prompt | formatter_llm
        result = chain.invoke({"review_json": review_json_str})

        formatted_text = result.content if hasattr(result, 'content') else str(result)

        return {
            "formatted_report": formatted_text,
            "original_data": review_data
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Formatting error: {str(e)}"
        )


@app.post("/generate-pdf")
async def generate_pdf(request: Request):
    """
    Generate a well-structured PDF report from review data using rev.py workflow.
    This endpoint uses the LLM-formatted PDF generation from rev.py.

    Expected JSON structure (same as PRReviewResponse):
    {
        "pr_metadata": {...},
        "review": {...},
        "agent_analyses": {...},
        "processing_time": 123.45
    }
    """
    print("=" * 50)
    print("PDF ENDPOINT HIT! (Using rev.py workflow)")
    print("=" * 50)
    print(f"Request method: {request.method}")
    print(f"Request URL: {request.url}")
    try:
        # Parse request body
        try:
            review_data = await request.json()
            print(f"PDF generation endpoint called with data keys: {list(review_data.keys()) if review_data else 'None'}")
        except Exception as json_error:
            print(f"JSON parsing error: {json_error}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON in request body: {str(json_error)}"
            )

        # Validate input
        if not review_data:
            raise HTTPException(
                status_code=400,
                detail="review_data is required in request body"
            )

        # Use rev.py workflow to generate PDF from JSON
        try:
            pdf_bytes = generate_pdf_from_json(review_data)

            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=pr-review-report-{uuid.uuid4().hex[:8]}.pdf"
                }
            )
        except Exception as pdf_error:
            print(f"Error generating PDF with rev.py: {pdf_error}")
            import traceback
            traceback.print_exc()
            # Fallback to original PDF generation if rev.py fails
            print("Falling back to original PDF generation method...")
            from io import BytesIO

            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch)
            story = []
            styles = getSampleStyleSheet()

            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#00D9FF'),
                spaceAfter=30,
                alignment=TA_CENTER
            )

            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=16,
                textColor=colors.HexColor('#00D9FF'),
                spaceAfter=12,
                spaceBefore=12
            )

            # Title
            story.append(Paragraph("PR Review Report", title_style))
            story.append(Spacer(1, 0.2*inch))

            # PR Metadata
            if review_data.get('pr_metadata'):
                metadata = review_data['pr_metadata']
                story.append(Paragraph("Pull Request Information", heading_style))
                metadata_text = f"""
                <b>PR #{metadata.get('pr_number', 'N/A')}</b>: {metadata.get('title', 'N/A')}<br/>
                Author: {metadata.get('author', 'N/A')}<br/>
                Branch: {metadata.get('branch', 'N/A')}<br/>
                Files Changed: {metadata.get('files_changed', 0)}<br/>
                Additions: +{metadata.get('additions', 0)} | Deletions: -{metadata.get('deletions', 0)}
                """
                story.append(Paragraph(metadata_text, styles['Normal']))
                story.append(Spacer(1, 0.2*inch))

            # Review Summary
            if review_data.get('review'):
                review = review_data['review']
                # Handle both dict and Pydantic model
                if hasattr(review, 'model_dump'):
                    review = review.model_dump()
                elif hasattr(review, 'dict'):
                    review = review.dict()

                story.append(Paragraph("Review Summary", heading_style))

                # Approval Status
                approval_status = review.get('approval_status') if isinstance(review, dict) else getattr(review, 'approval_status', 'N/A')
                status_color = colors.red if approval_status == 'CHANGES_REQUESTED' else colors.orange if approval_status == 'COMMENTED' else colors.green
                story.append(Paragraph(f"<b>Status:</b> <font color='{status_color.hexval()}'>{approval_status}</font>", styles['Normal']))
                story.append(Spacer(1, 0.1*inch))

                # Overall Assessment
                overall_assessment = review.get('overall_assessment') if isinstance(review, dict) else getattr(review, 'overall_assessment', 'N/A')
                story.append(Paragraph("<b>Overall Assessment:</b>", styles['Normal']))
                story.append(Paragraph(str(overall_assessment), styles['Normal']))
                story.append(Spacer(1, 0.2*inch))

                # Issue Counts
                summary_by_category = review.get('summary_by_category') if isinstance(review, dict) else getattr(review, 'summary_by_category', {})
                if summary_by_category:
                    story.append(Paragraph("<b>Issues by Category:</b>", styles['Normal']))
                    category_data = [['Category', 'Count']]
                    for cat, count in summary_by_category.items():
                        category_data.append([str(cat).title(), str(count)])

                    category_table = Table(category_data, colWidths=[4*inch, 1.5*inch])
                    category_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#00D9FF')),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 12),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#0f0f1e')),
                        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#ffffff')),
                        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#00D9FF')),
                    ]))
                    story.append(category_table)
                    story.append(Spacer(1, 0.2*inch))

                # Critical Blockers
                critical_blockers = review.get('critical_blockers') if isinstance(review, dict) else getattr(review, 'critical_blockers', [])
                if critical_blockers:
                    story.append(Paragraph("Critical Blockers", heading_style))
                    for blocker in critical_blockers[:10]:  # Limit to first 10
                        if isinstance(blocker, dict):
                            blocker_text = f"""
                            <b>{blocker.get('category', 'N/A').title()}</b> - {blocker.get('severity', 'N/A').upper()}<br/>
                            File: {blocker.get('filename', 'N/A')}:{blocker.get('line_number', 'N/A')}<br/>
                            <i>{blocker.get('issue_description', 'N/A')}</i><br/>
                            Recommendation: {blocker.get('recommendation', 'N/A')}
                            """
                        else:
                            blocker_text = f"""
                            <b>{getattr(blocker, 'category', 'N/A').title()}</b> - {getattr(blocker, 'severity', 'N/A').upper()}<br/>
                            File: {getattr(blocker, 'filename', 'N/A')}:{getattr(blocker, 'line_number', 'N/A')}<br/>
                            <i>{getattr(blocker, 'issue_description', 'N/A')}</i><br/>
                            Recommendation: {getattr(blocker, 'recommendation', 'N/A')}
                            """
                        story.append(Paragraph(blocker_text, styles['Normal']))
                        story.append(Spacer(1, 0.15*inch))
                    story.append(PageBreak())

                # Priority Actions
                priority_actions = review.get('priority_actions') if isinstance(review, dict) else getattr(review, 'priority_actions', [])
                if priority_actions:
                    story.append(Paragraph("Priority Actions", heading_style))
                    for i, action in enumerate(priority_actions, 1):
                        story.append(Paragraph(f"{i}. {action}", styles['Normal']))
                    story.append(Spacer(1, 0.2*inch))

            # Agent Analyses
            if review_data.get('agent_analyses'):
                story.append(PageBreak())
                story.append(Paragraph("Detailed Agent Analyses", heading_style))

                agent_names = {
                    'logic': 'Logic Analysis',
                    'security': 'Security Analysis',
                    'performance': 'Performance Analysis',
                    'readability': 'Readability Analysis',
                    'testing': 'Testing Analysis'
                }

                for agent_key, agent_name in agent_names.items():
                    analyses = review_data['agent_analyses'].get(agent_key, [])
                    if not analyses or not isinstance(analyses, list):
                        continue

                    story.append(Paragraph(agent_name, heading_style))

                    for analysis in analyses:
                        if not analysis:
                            continue

                        # Handle dict (from JSON) or object (from Pydantic)
                        if isinstance(analysis, dict):
                            # Logic Analysis
                            if agent_key == 'logic' and 'issues' in analysis:
                                for issue in analysis.get('issues', [])[:5]:
                                    issue_text = f"""
                                    <b>Issue:</b> {issue.get('issue_description', 'N/A')}<br/>
                                    <b>File:</b> {issue.get('filename', 'N/A')}:{issue.get('line_number', 'N/A')}<br/>
                                    <b>Recommendation:</b> {issue.get('recommendation', 'N/A')}
                                    """
                                    story.append(Paragraph(issue_text, styles['Normal']))
                                    story.append(Spacer(1, 0.1*inch))

                            # Security Analysis
                            elif agent_key == 'security' and 'vulnerabilities' in analysis:
                                security_score = analysis.get('security_score', 'N/A')
                                story.append(Paragraph(f"Security Score: {security_score}/100", styles['Normal']))
                                for vuln in analysis.get('vulnerabilities', [])[:5]:
                                    vuln_text = f"""
                                    <b>Vulnerability:</b> {vuln.get('issue_description', 'N/A')}<br/>
                                    <b>File:</b> {vuln.get('filename', 'N/A')}:{vuln.get('line_number', 'N/A')}<br/>
                                    <b>Recommendation:</b> {vuln.get('recommendation', 'N/A')}
                                    """
                                    story.append(Paragraph(vuln_text, styles['Normal']))
                                    story.append(Spacer(1, 0.1*inch))

                            # Performance Analysis
                            elif agent_key == 'performance' and 'bottlenecks' in analysis:
                                for bottleneck in analysis.get('bottlenecks', [])[:5]:
                                    perf_text = f"""
                                    <b>Bottleneck:</b> {bottleneck.get('issue_description', 'N/A')}<br/>
                                    <b>File:</b> {bottleneck.get('filename', 'N/A')}:{bottleneck.get('line_number', 'N/A')}<br/>
                                    <b>Recommendation:</b> {bottleneck.get('recommendation', 'N/A')}
                                    """
                                    story.append(Paragraph(perf_text, styles['Normal']))
                                    story.append(Spacer(1, 0.1*inch))

                            # Readability Analysis
                            elif agent_key == 'readability' and 'style_issues' in analysis:
                                readability_score = analysis.get('readability_score', 'N/A')
                                story.append(Paragraph(f"Readability Score: {readability_score}/100", styles['Normal']))
                                for issue in analysis.get('style_issues', [])[:5]:
                                    style_text = f"""
                                    <b>Style Issue:</b> {issue.get('issue_description', 'N/A')}<br/>
                                    <b>File:</b> {issue.get('filename', 'N/A')}:{issue.get('line_number', 'N/A')}<br/>
                                    <b>Recommendation:</b> {issue.get('recommendation', 'N/A')}
                                    """
                                    story.append(Paragraph(style_text, styles['Normal']))
                                    story.append(Spacer(1, 0.1*inch))

                            # Testing Analysis
                            elif agent_key == 'testing' and 'test_quality_issues' in analysis:
                                for issue in analysis.get('test_quality_issues', [])[:5]:
                                    test_text = f"""
                                    <b>Testing Issue:</b> {issue.get('issue_description', 'N/A')}<br/>
                                    <b>File:</b> {issue.get('filename', 'N/A')}:{issue.get('line_number', 'N/A')}<br/>
                                    <b>Recommendation:</b> {issue.get('recommendation', 'N/A')}
                                    """
                                    story.append(Paragraph(test_text, styles['Normal']))
                                    story.append(Spacer(1, 0.1*inch))
                        else:
                            # Handle Pydantic objects (if needed)
                            if agent_key == 'logic' and hasattr(analysis, 'issues'):
                                for issue in analysis.issues[:5]:
                                    issue_text = f"""
                                    <b>Issue:</b> {issue.issue_description}<br/>
                                    <b>File:</b> {issue.filename}:{issue.line_number or 'N/A'}<br/>
                                    <b>Recommendation:</b> {issue.recommendation}
                                    """
                                    story.append(Paragraph(issue_text, styles['Normal']))
                                    story.append(Spacer(1, 0.1*inch))

                    story.append(Spacer(1, 0.3*inch))

            # Build PDF
            doc.build(story)
            buffer.seek(0)

            return Response(
                content=buffer.read(),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=pr-review-report-{uuid.uuid4().hex[:8]}.pdf"
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PDF generation error: {error_trace}")
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation error: {str(e)}"
        )

