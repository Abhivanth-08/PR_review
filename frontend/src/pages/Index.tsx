import { useState } from "react";
import HolographicHeader from "@/components/HolographicHeader";
import PRInputModule from "@/components/PRInputModule";
import StatusStream from "@/components/StatusStream";
import AgentResults from "@/components/AgentResults";
import ReviewSummary from "@/components/ReviewSummary";
import { useToast } from "@/hooks/use-toast";
import { apiClient, PRReviewResponse } from "@/lib/api";
import cyberBg from "@/assets/cyber-bg.jpg";

const Index = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [results, setResults] = useState<any>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [useFormatted, setUseFormatted] = useState(false);
  const { toast } = useToast();

  const addLog = (message: string) => {
    setLogs((prev) => [...prev, message]);
  };

  const handleSubmit = async (data: { github_url?: string; diff_content?: string }) => {
    setIsLoading(true);
    setLogs([]);
    setResults(null);

    try {
      addLog("Initializing review sequence...");
      await new Promise((r) => setTimeout(r, 300));
      
      addLog("Parsing pull request data...");
      await new Promise((r) => setTimeout(r, 400));
      
      if (data.github_url) {
        addLog("Fetching PR from GitHub...");
      } else {
        addLog("Parsing diff content...");
      }
      await new Promise((r) => setTimeout(r, 500));
      
      addLog("Spawning analysis agents...");
      await new Promise((r) => setTimeout(r, 300));
      
      addLog("→ Logic Analysis Agent: active");
      await new Promise((r) => setTimeout(r, 200));
      
      addLog("→ Readability Analysis Agent: active");
      await new Promise((r) => setTimeout(r, 200));
      
      addLog("→ Performance Analysis Agent: active");
      await new Promise((r) => setTimeout(r, 200));
      
      addLog("→ Security Analysis Agent: active");
      await new Promise((r) => setTimeout(r, 200));
      
      addLog("→ Testing Analysis Agent: active");
      await new Promise((r) => setTimeout(r, 200));
      
      addLog("Aggregating agent reports...");
      
      // Make actual API call
      const response = await apiClient.reviewPR(data);
      
      addLog("Generating final review summary...");
      await new Promise((r) => setTimeout(r, 300));
      
      addLog("✓ Review sequence complete");

      // Transform backend response to frontend format
      const transformedResults = transformBackendResponse(response);
      
      setResults(transformedResults);
      setIsLoading(false);

      toast({
        title: "Review Complete",
        description: "AI agents have completed their analysis.",
      });
    } catch (error: any) {
      setIsLoading(false);
      addLog(`✗ Error: ${error.message || 'Failed to process review'}`);
      
      toast({
        title: "Review Failed",
        description: error.message || "Failed to process the review. Please try again.",
        variant: "destructive",
      });
    }
  };

  // Transform backend response to match frontend component expectations
  const transformBackendResponse = (response: PRReviewResponse) => {
    const agentAnalyses: any[] = [];
    const agentMap: Record<string, any> = {
      logic: { name: "Logic Analysis", key: "logic", issuesKey: "issues" },
      security: { name: "Security Analysis", key: "security", issuesKey: "vulnerabilities" },
      performance: { name: "Performance Analysis", key: "performance", issuesKey: "bottlenecks" },
      readability: { name: "Readability Analysis", key: "readability", issuesKey: "style_issues" },
      testing: { name: "Testing Analysis", key: "testing", issuesKey: "test_quality_issues" },
    };

    // Process each agent type
    for (const [key, config] of Object.entries(agentMap)) {
      const analyses = response.agent_analyses[key];
      if (!analyses || !Array.isArray(analyses)) continue;

      const findings: any[] = [];
      
      for (const analysis of analyses) {
        if (!analysis) continue;
        
        const issues = analysis[config.issuesKey] || [];
        for (const issue of issues) {
          findings.push({
            severity: issue.severity?.toLowerCase() || "info",
            category: issue.category || key,
            message: issue.issue_description || "",
            file: issue.filename || "",
            line: issue.line_number,
          });
        }
      }

      if (findings.length > 0) {
        agentAnalyses.push({
          agent_name: config.name,
          findings,
        });
      }
    }

    // Count issues by severity
    const allIssues = response.review.all_issues || [];
    const severityCounts = {
      critical: 0,
      warning: 0,
      suggestion: 0,
      info: 0,
    };

    for (const issue of allIssues) {
      const severity = issue.severity?.toLowerCase() || "info";
      if (severity === "critical" || severity === "high") {
        severityCounts.critical++;
      } else if (severity === "medium" || severity === "warning") {
        severityCounts.warning++;
      } else if (severity === "low" || severity === "suggestion") {
        severityCounts.suggestion++;
      } else {
        severityCounts.info++;
      }
    }

    return {
      agent_analyses: agentAnalyses,
      summary: {
        total_issues: allIssues.length,
        critical: severityCounts.critical,
        warning: severityCounts.warning,
        suggestion: severityCounts.suggestion,
        info: severityCounts.info,
        final_review: response.review.overall_assessment || "Review completed.",
        processing_time: response.processing_time,
      },
      raw_data: response, // Keep raw data for PDF export
    };
  };

  const handleExport = async (format: 'json' | 'pdf' = 'json') => {
    if (!results?.raw_data) {
      toast({
        title: "Export Failed",
        description: "No review data available to export.",
        variant: "destructive",
      });
      return;
    }

    setIsExporting(true);

    try {
      if (format === 'pdf') {
        // Generate PDF from backend
        const blob = await apiClient.generatePDF(results.raw_data);
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `pr-review-${Date.now()}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        toast({
          title: "PDF Export Successful",
          description: "Review report PDF has been downloaded.",
        });
      } else {
        // Export as JSON
        let exportData = results.raw_data;
        
        // Optionally format with LLM
        if (useFormatted) {
          try {
            const formatted = await apiClient.formatReview(results.raw_data);
            exportData = {
              ...results.raw_data,
              formatted_report: formatted.formatted_report,
            };
          } catch (error) {
            console.error("Formatting failed, exporting raw data:", error);
          }
        }

        const jsonData = JSON.stringify(exportData, null, 2);
        const blob = new Blob([jsonData], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `pr-review-${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        toast({
          title: "Export Successful",
          description: `Review report has been downloaded as ${useFormatted ? 'formatted ' : ''}JSON.`,
        });
      }
    } catch (error: any) {
      toast({
        title: "Export Failed",
        description: error.message || "Failed to export the review report.",
        variant: "destructive",
      });
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="min-h-screen relative">
      {/* Cyber background */}
      <div
        className="fixed inset-0 z-0 opacity-20"
        style={{
          backgroundImage: `url(${cyberBg})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
      />
      
      {/* Gradient overlay */}
      <div className="fixed inset-0 z-0 bg-gradient-to-b from-cyber-black via-transparent to-cyber-black" />

      {/* Content */}
      <div className="relative z-10">
        <HolographicHeader />

        <main className="container mx-auto px-6 py-8 space-y-8">
          <PRInputModule onSubmit={handleSubmit} isLoading={isLoading} />
          
          <StatusStream logs={logs} isActive={isLoading} />

          {results && (
            <>
              <AgentResults analyses={results.agent_analyses} />
              <ReviewSummary 
                summary={results.summary} 
                onExport={handleExport}
                isExporting={isExporting}
                useFormatted={useFormatted}
                onFormatToggle={setUseFormatted}
              />
            </>
          )}
        </main>
      </div>
    </div>
  );
};

export default Index;
