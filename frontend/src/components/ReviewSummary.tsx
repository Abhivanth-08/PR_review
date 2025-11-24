import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Download, CheckCircle2, AlertTriangle, AlertCircle, Info, FileText, Sparkles } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

interface ReviewSummaryProps {
  summary: {
    total_issues: number;
    critical: number;
    warning: number;
    suggestion: number;
    info: number;
    final_review: string;
    processing_time?: number;
  };
  onExport: (format: 'json' | 'pdf') => void;
  isExporting?: boolean;
  useFormatted?: boolean;
  onFormatToggle?: (value: boolean) => void;
}

const ReviewSummary = ({ summary, onExport, isExporting = false, useFormatted = false, onFormatToggle }: ReviewSummaryProps) => {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <CheckCircle2 className="w-5 h-5 text-neon-teal animate-glow-pulse" />
        <h2 className="text-xl font-bold text-glow-teal">Review Summary</h2>
      </div>

      <Card className="glass-strong p-6 border-neon-teal/30 relative overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-neon-teal to-transparent opacity-50" />
        
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <div className="glass p-4 rounded-sm border border-border/50 text-center">
            <div className="text-2xl font-bold text-foreground">{summary.total_issues}</div>
            <div className="text-xs text-muted-foreground uppercase tracking-wide mt-1">Total Issues</div>
          </div>
          
          <div className="glass p-4 rounded-sm border border-destructive/50 text-center hover:scale-105 transition-transform">
            <div className="flex items-center justify-center gap-2 text-2xl font-bold text-destructive">
              <AlertCircle className="w-5 h-5" />
              {summary.critical}
            </div>
            <div className="text-xs text-muted-foreground uppercase tracking-wide mt-1">Critical</div>
          </div>
          
          <div className="glass p-4 rounded-sm border border-warning/50 text-center hover:scale-105 transition-transform">
            <div className="flex items-center justify-center gap-2 text-2xl font-bold text-warning">
              <AlertTriangle className="w-5 h-5" />
              {summary.warning}
            </div>
            <div className="text-xs text-muted-foreground uppercase tracking-wide mt-1">Warning</div>
          </div>
          
          <div className="glass p-4 rounded-sm border border-info/50 text-center hover:scale-105 transition-transform">
            <div className="text-2xl font-bold text-info">{summary.suggestion}</div>
            <div className="text-xs text-muted-foreground uppercase tracking-wide mt-1">Suggestion</div>
          </div>
          
          <div className="glass p-4 rounded-sm border border-muted/50 text-center hover:scale-105 transition-transform">
            <div className="flex items-center justify-center gap-2 text-2xl font-bold text-muted-foreground">
              <Info className="w-4 h-4" />
              {summary.info}
            </div>
            <div className="text-xs text-muted-foreground uppercase tracking-wide mt-1">Info</div>
          </div>
        </div>

        <div className="glass p-5 rounded-sm border border-holo-purple/30 mb-4">
          <h3 className="text-sm font-semibold text-holo-purple uppercase tracking-wide mb-3 flex items-center gap-2">
            <span className="w-2 h-2 bg-holo-purple rounded-full animate-pulse" />
            Final Assessment
          </h3>
          <p className="text-sm leading-relaxed text-foreground/90">{summary.final_review}</p>
        </div>

        {summary.processing_time && (
          <div className="text-xs text-muted-foreground mb-4">
            Processing completed in {summary.processing_time.toFixed(2)}s
          </div>
        )}

        {/* Formatting Option */}
        {onFormatToggle && (
          <div className="glass p-4 rounded-sm border border-border/50 mb-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Sparkles className="w-4 h-4 text-holo-purple" />
              <div>
                <Label htmlFor="format-toggle" className="text-sm font-medium cursor-pointer">
                  Use AI Formatting
                </Label>
                <p className="text-xs text-muted-foreground">
                  Format report with LLM for better readability
                </p>
              </div>
            </div>
            <Switch
              id="format-toggle"
              checked={useFormatted}
              onCheckedChange={onFormatToggle}
              disabled={isExporting}
            />
          </div>
        )}

        {/* Export Buttons */}
        <div className="flex gap-3">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button 
                variant="cyber" 
                size="lg" 
                className="flex-1 relative group"
                disabled={isExporting}
              >
                <Download className="w-4 h-4 mr-2" />
                {isExporting ? "Exporting..." : "Export Report"}
                
                {!isExporting && (
                  <div className="absolute inset-0 rounded-sm opacity-0 group-hover:opacity-100 transition-opacity">
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-neon-teal/20 to-transparent animate-data-flow" />
                  </div>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="glass-strong border-border/50">
              <DropdownMenuItem onClick={() => onExport('json')} disabled={isExporting}>
                <FileText className="w-4 h-4 mr-2" />
                Export as JSON
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onExport('pdf')} disabled={isExporting}>
                <Download className="w-4 h-4 mr-2" />
                Export as PDF
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </Card>
    </div>
  );
};

export default ReviewSummary;
