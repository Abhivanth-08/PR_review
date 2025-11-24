const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export interface PRReviewRequest {
  github_url?: string;
  diff_content?: string;
  pr_metadata?: Record<string, any>;
}

export interface PRReviewResponse {
  pr_metadata?: {
    pr_number: number;
    title: string;
    description?: string;
    author: string;
    branch: string;
    files_changed: number;
    additions: number;
    deletions: number;
  };
  review: {
    overall_assessment: string;
    approval_status: string;
    critical_blockers: Array<{
      category: string;
      severity: string;
      line_number?: number;
      filename: string;
      code_snippet: string;
      issue_description: string;
      recommendation: string;
      reasoning: string;
    }>;
    all_issues: Array<{
      category: string;
      severity: string;
      line_number?: number;
      filename: string;
      code_snippet: string;
      issue_description: string;
      recommendation: string;
      reasoning: string;
    }>;
    strengths: string[];
    summary_by_category: Record<string, number>;
    priority_actions: string[];
  };
  agent_analyses: Record<string, any>;
  processing_time: number;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  async reviewPR(request: PRReviewRequest): Promise<PRReviewResponse> {
    const response = await fetch(`${this.baseUrl}/review`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  async formatReview(reviewData: any): Promise<{ formatted_report: string; original_data: any }> {
    const response = await fetch(`${this.baseUrl}/format-review`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(reviewData),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  async generatePDF(reviewData: any): Promise<Blob> {
    console.log('Generating PDF with data:', Object.keys(reviewData || {}));
    const response = await fetch(`${this.baseUrl}/generate-pdf`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(reviewData),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('PDF generation error:', response.status, errorText);
      let errorMessage = errorText;
      try {
        const errorJson = JSON.parse(errorText);
        errorMessage = errorJson.detail || errorJson.message || errorText;
      } catch {
        // Not JSON, use text as is
      }
      throw new Error(errorMessage || `HTTP error! status: ${response.status}`);
    }

    return response.blob();
  }

  async healthCheck(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/health`);
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.status}`);
    }
    return response.json();
  }
}

export const apiClient = new ApiClient(API_BASE_URL);

