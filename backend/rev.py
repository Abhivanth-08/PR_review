from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from custom_wrapper import OpenRouterChat
from pydantic import BaseModel, Field
from typing import List
import os
import json
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from datetime import datetime
from io import BytesIO

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

llm = OpenRouterChat(
    api_key=OPENROUTER_API_KEY,
    model="openai/gpt-3.5-turbo",
    temperature=0,
    max_tokens=1024
)

prompt = ChatPromptTemplate.from_template("""
You will receive JSON input containing automated pull request review data.

Your task:

1. Convert the JSON review into a clean, professional PR Review Report.
2. Output ONLY the formatted text. 
3. Do NOT wrap the answer in JSON, Python objects, quotes, backticks, dicts, or metadata.
4. The final answer must be plain text formatted with headings, bullet points, and tables.
5. The output must follow this exact structure:

## PR Metadata
- PR Number:
- Title:
- Author:
- Branch:
- Files changed, additions, deletions:

## Overall Review Summary
- Overall assessment:
- Approval status:
- Short summary:

## Critical Blockers (High Severity)
(For each blocker, include:)
- File:
- Issue:
- Code Snippet:
- Recommendation:
- Reasoning:

## All Issues (Non-Critical)
(Group by filename)

## Strengths
(List all strengths)

## Summary by Category
| Category | Issue Count |

## Priority Actions
(Numbered action items)

## Agent Analyses Summary
(Short summary for logic, security, performance, readability, testing)

## Final Verdict
(2-3 line closing remark + final status)

STRICT RULES:
- Do NOT output markdown code fences.
- Do NOT output JSON.
- Do NOT repeat or reprint the input.
- Only output the clean formatted text report.

The content:
{text}
""")

chain = (
        {"text": RunnablePassthrough()}
        | prompt
        | llm
)


def extract_pr(text):
    try:
        result = chain.invoke(text)
        # Use result.dict() if available for formatted output
        if hasattr(result, 'dict'):
            return result.dict()
        elif hasattr(result, 'model_dump'):  # Pydantic v2
            return result.model_dump()
        elif hasattr(result, 'content'):
            return result.content
        elif isinstance(result, str):
            return result
        else:
            return str(result)
    except Exception as e:
        print(f"Error extracting PR: {e}")
        return None


def parse_review_text(text):
    """Parse the formatted review text into structured sections"""
    sections = {
        'metadata': {},
        'overall_summary': {},
        'critical_blockers': [],
        'all_issues': [],
        'strengths': [],
        'summary_by_category': {},
        'priority_actions': [],
        'agent_analyses': '',
        'final_verdict': ''
    }

    lines = text.split('\n')
    current_section = None
    current_blocker = {}

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Detect sections
        if line.startswith('## PR Metadata'):
            current_section = 'metadata'
            continue
        elif line.startswith('## Overall Review Summary'):
            current_section = 'overall_summary'
            continue
        elif line.startswith('## Critical Blockers'):
            current_section = 'critical_blockers'
            continue
        elif line.startswith('## All Issues'):
            current_section = 'all_issues'
            continue
        elif line.startswith('## Strengths'):
            current_section = 'strengths'
            continue
        elif line.startswith('## Summary by Category'):
            current_section = 'summary_by_category'
            continue
        elif line.startswith('## Priority Actions'):
            current_section = 'priority_actions'
            continue
        elif line.startswith('## Agent Analyses'):
            current_section = 'agent_analyses'
            continue
        elif line.startswith('## Final Verdict'):
            current_section = 'final_verdict'
            continue

        # Parse content based on current section
        if current_section == 'metadata':
            if line.startswith('- PR Number:'):
                sections['metadata']['pr_number'] = line.split(':', 1)[1].strip()
            elif line.startswith('- Title:'):
                sections['metadata']['title'] = line.split(':', 1)[1].strip()
            elif line.startswith('- Author:'):
                sections['metadata']['author'] = line.split(':', 1)[1].strip()
            elif line.startswith('- Branch:'):
                sections['metadata']['branch'] = line.split(':', 1)[1].strip()
            elif line.startswith('- Files changed'):
                parts = line.split(':', 1)[1].strip().split(',')
                if len(parts) >= 3:
                    sections['metadata']['files_changed'] = parts[0].strip()
                    sections['metadata']['additions'] = parts[1].strip()
                    sections['metadata']['deletions'] = parts[2].strip()
        elif current_section == 'overall_summary':
            if line.startswith('- Overall assessment:'):
                sections['overall_summary']['assessment'] = line.split(':', 1)[1].strip()
            elif line.startswith('- Approval status:'):
                sections['overall_summary']['approval_status'] = line.split(':', 1)[1].strip()
            elif line.startswith('- Short summary:'):
                sections['overall_summary']['short_summary'] = line.split(':', 1)[1].strip()
        elif current_section == 'critical_blockers':
            if line.startswith('- File:'):
                if current_blocker:
                    sections['critical_blockers'].append(current_blocker)
                current_blocker = {'file': line.split(':', 1)[1].strip()}
            elif line.startswith('- Issue:'):
                current_blocker['issue'] = line.split(':', 1)[1].strip()
            elif line.startswith('- Code Snippet:'):
                current_blocker['code_snippet'] = line.split(':', 1)[1].strip()
            elif line.startswith('- Recommendation:'):
                current_blocker['recommendation'] = line.split(':', 1)[1].strip()
            elif line.startswith('- Reasoning:'):
                current_blocker['reasoning'] = line.split(':', 1)[1].strip()
        elif current_section == 'strengths':
            if line.startswith('- '):
                sections['strengths'].append(line[2:].strip())
        elif current_section == 'priority_actions':
            if re.match(r'^\d+\.', line):
                sections['priority_actions'].append(line.split('.', 1)[1].strip())
        elif current_section == 'agent_analyses':
            sections['agent_analyses'] += line + ' '
        elif current_section == 'final_verdict':
            sections['final_verdict'] += line + ' '

    # Add last blocker if exists
    if current_blocker and current_section == 'critical_blockers':
        sections['critical_blockers'].append(current_blocker)

    return sections


def generate_pdf_from_review(review_text, output_filename="review.pdf", return_bytes=False):
    """Generate a well-formatted PDF from the review text

    Args:
        review_text: The formatted review text to convert to PDF
        output_filename: Filename to save PDF (ignored if return_bytes=True)
        return_bytes: If True, return PDF bytes instead of writing to file

    Returns:
        If return_bytes=True, returns bytes. Otherwise, writes to file and returns None.
    """
    print("Generating PDF from review text...")
    print(f"Review text length: {len(str(review_text))}")

    sections = parse_review_text(str(review_text))
    print(f"Parsed sections: {list(sections.keys())}")

    # Check if we have meaningful content
    has_meaningful_content = (
            sections.get('metadata') or
            sections.get('overall_summary') or
            len(sections.get('critical_blockers', [])) > 0 or
            len(sections.get('strengths', [])) > 0 or
            len(sections.get('priority_actions', [])) > 0
    )

    if not has_meaningful_content:
        print("Warning: Parsing may have failed or no structured content found, using raw text fallback")
        return generate_pdf_from_raw_text(str(review_text), output_filename, return_bytes)

    # Create PDF - use BytesIO if returning bytes, otherwise use filename
    if return_bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    else:
        doc = SimpleDocTemplate(output_filename, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    story = []
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a73e8'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#1a73e8'),
        spaceAfter=12,
        spaceBefore=20,
        fontName='Helvetica-Bold'
    )

    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#5f6368'),
        spaceAfter=8,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )

    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#202124'),
        spaceAfter=6,
        leading=14,
        alignment=TA_JUSTIFY
    )

    # Title
    story.append(Paragraph("Pull Request Review Report", title_style))
    story.append(Spacer(1, 0.3 * inch))

    # PR Metadata
    if sections['metadata']:
        story.append(Paragraph("PR Metadata", heading_style))
        metadata = sections['metadata']
        metadata_text = f"""
        <b>PR Number:</b> {metadata.get('pr_number', 'N/A')}<br/>
        <b>Title:</b> {metadata.get('title', 'N/A')}<br/>
        <b>Author:</b> {metadata.get('author', 'N/A')}<br/>
        <b>Branch:</b> {metadata.get('branch', 'N/A')}<br/>
        <b>Files Changed:</b> {metadata.get('files_changed', 'N/A')} | 
        <b>Additions:</b> +{metadata.get('additions', 'N/A')} | 
        <b>Deletions:</b> -{metadata.get('deletions', 'N/A')}
        """
        story.append(Paragraph(metadata_text, normal_style))
        story.append(Spacer(1, 0.2 * inch))

    # Overall Review Summary
    if sections['overall_summary']:
        story.append(PageBreak())
        story.append(Paragraph("Overall Review Summary", heading_style))
        summary = sections['overall_summary']

        if summary.get('assessment'):
            story.append(Paragraph("<b>Overall Assessment:</b>", subheading_style))
            story.append(Paragraph(summary['assessment'], normal_style))
            story.append(Spacer(1, 0.1 * inch))

        if summary.get('approval_status'):
            status_color = colors.red if 'CHANGES_REQUESTED' in summary[
                'approval_status'] else colors.orange if 'COMMENTED' in summary['approval_status'] else colors.green
            story.append(Paragraph(
                f"<b>Approval Status:</b> <font color='{status_color.hexval()}'>{summary['approval_status']}</font>",
                normal_style))
            story.append(Spacer(1, 0.1 * inch))

        if summary.get('short_summary'):
            story.append(Paragraph(f"<b>Summary:</b> {summary['short_summary']}", normal_style))

        story.append(Spacer(1, 0.2 * inch))

    # Critical Blockers
    if sections['critical_blockers']:
        story.append(PageBreak())
        story.append(Paragraph("Critical Blockers (High Severity)", heading_style))

        for i, blocker in enumerate(sections['critical_blockers'], 1):
            story.append(Paragraph(f"Blocker {i}", subheading_style))

            blocker_text = f"""
            <b>File:</b> {blocker.get('file', 'N/A')}<br/>
            <b>Issue:</b> {blocker.get('issue', 'N/A')}<br/>
            """
            story.append(Paragraph(blocker_text, normal_style))

            if blocker.get('code_snippet'):
                code_text = f"<b>Code Snippet:</b><br/><font face='Courier' size='8'>{blocker['code_snippet']}</font>"
                story.append(Paragraph(code_text, normal_style))

            if blocker.get('recommendation'):
                story.append(Paragraph(f"<b>Recommendation:</b> {blocker['recommendation']}", normal_style))

            if blocker.get('reasoning'):
                story.append(Paragraph(f"<b>Reasoning:</b> {blocker['reasoning']}", normal_style))

            story.append(Spacer(1, 0.15 * inch))

    # Strengths
    if sections['strengths']:
        story.append(PageBreak())
        story.append(Paragraph("Strengths", heading_style))
        for strength in sections['strengths']:
            story.append(Paragraph(f"• {strength}", normal_style))
        story.append(Spacer(1, 0.2 * inch))

    # Priority Actions
    if sections['priority_actions']:
        story.append(Paragraph("Priority Actions", heading_style))
        for i, action in enumerate(sections['priority_actions'], 1):
            story.append(Paragraph(f"{i}. {action}", normal_style))
        story.append(Spacer(1, 0.2 * inch))

    # Summary by Category
    if sections['summary_by_category']:
        story.append(Paragraph("Summary by Category", heading_style))
        category_data = [['Category', 'Issue Count']]
        for cat, count in sections['summary_by_category'].items():
            category_data.append([cat.title(), str(count)])

        category_table = Table(category_data, colWidths=[4 * inch, 1.5 * inch])
        category_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a73e8')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#202124')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dadce0')),
        ]))
        story.append(category_table)
        story.append(Spacer(1, 0.2 * inch))

    # Agent Analyses
    if sections['agent_analyses']:
        story.append(Paragraph("Agent Analyses Summary", heading_style))
        story.append(Paragraph(sections['agent_analyses'].strip(), normal_style))
        story.append(Spacer(1, 0.2 * inch))

    # Final Verdict
    if sections['final_verdict']:
        story.append(PageBreak())
        story.append(Paragraph("Final Verdict", heading_style))
        story.append(Paragraph(sections['final_verdict'].strip(), normal_style))

    # Footer with date
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(f"<i>Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>",
                           ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey,
                                          alignment=TA_CENTER)))

    # Build PDF
    doc.build(story)

    if return_bytes:
        buffer.seek(0)
        pdf_bytes = buffer.read()
        print(f"PDF generated successfully in memory ({len(pdf_bytes)} bytes)")
        print(f"Total elements in PDF: {len(story)}")
        return pdf_bytes
    else:
        print(f"PDF generated successfully: {output_filename}")
        print(f"Total elements in PDF: {len(story)}")
        return None


def generate_pdf_from_raw_text(review_text, output_filename="review.pdf", return_bytes=False):
    """Fallback: Generate PDF directly from raw text if parsing fails

    Args:
        review_text: The raw review text to convert to PDF
        output_filename: Filename to save PDF (ignored if return_bytes=True)
        return_bytes: If True, return PDF bytes instead of writing to file

    Returns:
        If return_bytes=True, returns bytes. Otherwise, writes to file and returns None.
    """
    print("Using raw text fallback for PDF generation")

    # Create PDF - use BytesIO if returning bytes, otherwise use filename
    if return_bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    else:
        doc = SimpleDocTemplate(output_filename, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    story = []
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a73e8'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#1a73e8'),
        spaceAfter=12,
        spaceBefore=20,
        fontName='Helvetica-Bold'
    )

    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#202124'),
        spaceAfter=6,
        leading=14,
        alignment=TA_LEFT
    )

    # Title
    story.append(Paragraph("Pull Request Review Report", title_style))
    story.append(Spacer(1, 0.3 * inch))

    # Process text line by line
    lines = review_text.split('\n')
    current_heading = None

    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 0.1 * inch))
            continue

        # Detect markdown headings
        if line.startswith('## '):
            if current_heading:
                story.append(Spacer(1, 0.2 * inch))
            current_heading = line[3:].strip()
            story.append(Paragraph(current_heading, heading_style))
        elif line.startswith('### '):
            if current_heading:
                story.append(Spacer(1, 0.15 * inch))
            current_heading = line[4:].strip()
            story.append(Paragraph(current_heading, ParagraphStyle('SubHeading', parent=styles['Heading3'], fontSize=12,
                                                                   textColor=colors.HexColor('#5f6368'), spaceAfter=8)))
        elif line.startswith('- ') or line.startswith('* '):
            # Bullet point
            content = line[2:].strip()
            # Handle bold text in bullet points
            content = content.replace('**', '<b>').replace('**', '</b>')
            story.append(Paragraph(f"• {content}", normal_style))
        elif re.match(r'^\d+\.', line):
            # Numbered list
            content = line.split('.', 1)[1].strip()
            content = content.replace('**', '<b>').replace('**', '</b>')
            story.append(Paragraph(content, normal_style))
        elif line.startswith('|') and '|' in line[1:]:
            # Table row - skip for now or format as text
            story.append(Paragraph(line.replace('|', ' | '),
                                   ParagraphStyle('TableText', parent=normal_style, fontSize=9, fontName='Courier')))
        else:
            # Regular paragraph
            # Escape HTML and handle basic markdown
            content = line
            content = content.replace('**', '<b>').replace('**', '</b>')
            content = content.replace('*', '<i>').replace('*', '</i>')
            # Handle code blocks
            if '`' in content:
                parts = content.split('`')
                formatted = ''
                for i, part in enumerate(parts):
                    if i % 2 == 0:
                        formatted += part
                    else:
                        formatted += f"<font face='Courier' size='9'>{part}</font>"
                content = formatted

            story.append(Paragraph(content, normal_style))

    # Footer
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(f"<i>Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>",
                           ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey,
                                          alignment=TA_CENTER)))

    # Build PDF
    doc.build(story)

    if return_bytes:
        buffer.seek(0)
        pdf_bytes = buffer.read()
        print(f"PDF generated successfully from raw text in memory ({len(pdf_bytes)} bytes)")
        print(f"Total elements in PDF: {len(story)}")
        return pdf_bytes
    else:
        print(f"PDF generated successfully from raw text: {output_filename}")
        print(f"Total elements in PDF: {len(story)}")
        return None


def execute_pr(txt):
    result = extract_pr(txt)

    # Ensure result is not None
    if result is None:
        print("Error: extract_pr returned None")
        return None

    # Handle result - it could be a dict, string, or object
    if isinstance(result, dict):
        # If result is a dict, extract content from it
        if 'content' in result:
            result_str = str(result['content'])
        else:
            # Format the dict nicely for display
            result_str = json.dumps(result, indent=2, ensure_ascii=False)
    elif hasattr(result, 'content'):
        result_str = str(result.content)
    else:
        result_str = str(result)

    print(f"Result type: {type(result)}")
    print(f"Result length: {len(result_str)}")

    # Write formatted output to review.txt
    f = open("review.txt", "w", encoding="utf-8")
    if isinstance(result, dict):
        # Write formatted dict representation
        f.write(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        f.write(result_str)
    f.close()
    print("Review text written to review.txt")

    # Generate PDF - extract content from dict if needed
    pdf_content = result_str
    if isinstance(result, dict) and 'content' in result:
        pdf_content = str(result['content'])

    try:
        generate_pdf_from_review(pdf_content, "review.pdf")
        print("PDF generation completed")
    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        # Try fallback
        try:
            print("Attempting raw text fallback...")
            generate_pdf_from_raw_text(pdf_content, "review.pdf")
        except Exception as e2:
            print(f"Fallback also failed: {e2}")

    return result


def generate_pdf_from_json(review_json):
    """
    Generate PDF from JSON review data using the rev.py workflow.

    This function:
    1. Takes JSON review data (from /review endpoint)
    2. Formats it using LLM via extract_pr
    3. Generates a clean PDF from the formatted text
    4. Returns PDF bytes for download

    Args:
        review_json: Dictionary containing review data (same format as PRReviewResponse)

    Returns:
        bytes: PDF file content as bytes
    """
    try:
        print("Starting PDF generation from JSON using rev.py workflow...")

        # Convert JSON to string for LLM processing
        json_str = json.dumps(review_json, indent=2, ensure_ascii=False)

        # Use extract_pr to format the JSON with LLM
        result = extract_pr(json_str)

        if result is None:
            raise ValueError("extract_pr returned None")

        # Extract content from result
        if isinstance(result, dict):
            if 'content' in result:
                formatted_text = str(result['content'])
            else:
                formatted_text = json.dumps(result, indent=2, ensure_ascii=False)
        elif hasattr(result, 'content'):
            formatted_text = str(result.content)
        else:
            formatted_text = str(result)

        print(f"Formatted text length: {len(formatted_text)}")

        # Generate PDF from formatted text and return bytes
        try:
            pdf_bytes = generate_pdf_from_review(formatted_text, return_bytes=True)
            print(f"PDF generated successfully: {len(pdf_bytes)} bytes")
            return pdf_bytes
        except Exception as e:
            print(f"Error generating PDF from formatted text: {e}")
            import traceback
            traceback.print_exc()
            # Try fallback with raw text
            print("Attempting raw text fallback...")
            pdf_bytes = generate_pdf_from_raw_text(formatted_text, return_bytes=True)
            print(f"PDF generated successfully from raw text: {len(pdf_bytes)} bytes")
            return pdf_bytes

    except Exception as e:
        print(f"Error in generate_pdf_from_json: {e}")
        import traceback
        traceback.print_exc()
        raise

