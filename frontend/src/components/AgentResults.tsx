import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Brain, Eye, Zap, Shield, TestTube } from "lucide-react";

interface AgentAnalysis {
  agent_name: string;
  findings: Array<{
    severity: "critical" | "warning" | "suggestion" | "info";
    category: string;
    message: string;
    line?: number;
    file?: string;
  }>;
}

interface AgentResultsProps {
  analyses: AgentAnalysis[];
}

const agentIcons: Record<string, any> = {
  logic: Brain,
  readability: Eye,
  performance: Zap,
  security: Shield,
  testing: TestTube,
};

const severityColors: Record<string, string> = {
  critical: "destructive",
  warning: "warning",
  suggestion: "info",
  info: "muted",
};

const severityClasses: Record<string, string> = {
  critical: "border-destructive/50 bg-destructive/10 text-destructive",
  warning: "border-warning/50 bg-warning/10 text-warning",
  suggestion: "border-info/50 bg-info/10 text-info",
  info: "border-muted/50 bg-muted text-muted-foreground",
};

const AgentResults = ({ analyses }: AgentResultsProps) => {
  if (analyses.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <span className="w-3 h-3 bg-neon-teal rounded-full animate-glow-pulse" />
        <h2 className="text-xl font-bold text-glow-teal">Multi-Agent Analysis</h2>
      </div>

      <Accordion type="multiple" className="space-y-3">
        {analyses.map((analysis, idx) => {
          const agentKey = analysis.agent_name.toLowerCase().split(" ")[0];
          const Icon = agentIcons[agentKey] || Brain;
          
          return (
            <AccordionItem
              key={idx}
              value={`agent-${idx}`}
              className="glass-strong border border-border/50 rounded-sm overflow-hidden holo-border"
            >
              <AccordionTrigger className="px-6 py-4 hover:no-underline hover:bg-accent/5 transition-colors">
                <div className="flex items-center gap-3 w-full">
                  <Icon className="w-5 h-5 text-neon-teal" />
                  <span className="font-semibold text-base">{analysis.agent_name}</span>
                  <Badge variant="outline" className="ml-auto mr-2 glass text-xs">
                    {analysis.findings.length} findings
                  </Badge>
                </div>
              </AccordionTrigger>
              
              <AccordionContent className="px-6 pb-4">
                <div className="space-y-3 pt-2">
                  {analysis.findings.map((finding, fidx) => (
                    <div
                      key={fidx}
                      className={`glass p-4 rounded-sm border ${severityClasses[finding.severity]} transition-all hover:scale-[1.01]`}
                    >
                      <div className="flex items-start gap-3">
                        <div className="flex-1 space-y-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            <Badge
                              variant="outline"
                              className={`text-xs uppercase ${severityClasses[finding.severity]} border-none`}
                            >
                              {finding.severity}
                            </Badge>
                            <span className="text-xs text-muted-foreground">•</span>
                            <span className="text-xs font-medium">{finding.category}</span>
                            {finding.file && (
                              <>
                                <span className="text-xs text-muted-foreground">•</span>
                                <code className="text-xs font-mono text-neon-teal">
                                  {finding.file}
                                  {finding.line && `:${finding.line}`}
                                </code>
                              </>
                            )}
                          </div>
                          <p className="text-sm leading-relaxed">{finding.message}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </AccordionContent>
            </AccordionItem>
          );
        })}
      </Accordion>
    </div>
  );
};

export default AgentResults;
