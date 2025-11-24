import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Link2, Code2, Play } from "lucide-react";

interface PRInputModuleProps {
  onSubmit: (data: { github_url?: string; diff_content?: string }) => void;
  isLoading: boolean;
}

const PRInputModule = ({ onSubmit, isLoading }: PRInputModuleProps) => {
  const [githubUrl, setGithubUrl] = useState("");
  const [diffContent, setDiffContent] = useState("");
  const [activeTab, setActiveTab] = useState("url");

  const handleSubmit = () => {
    if (activeTab === "url" && githubUrl) {
      onSubmit({ github_url: githubUrl });
    } else if (activeTab === "diff" && diffContent) {
      onSubmit({ diff_content: diffContent });
    }
  };

  return (
    <div className="glass-strong p-6 rounded-sm holo-border relative overflow-hidden">
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-neon-teal to-transparent opacity-50" />
      
      <h2 className="text-lg font-semibold mb-4 text-foreground flex items-center gap-2">
        <span className="w-2 h-2 bg-neon-teal rounded-full animate-pulse" />
        Initialize Review Sequence
      </h2>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-2 glass mb-4">
          <TabsTrigger value="url" className="data-[state=active]:bg-neon-teal/20 data-[state=active]:text-neon-teal">
            <Link2 className="w-4 h-4 mr-2" />
            GitHub PR URL
          </TabsTrigger>
          <TabsTrigger value="diff" className="data-[state=active]:bg-neon-teal/20 data-[state=active]:text-neon-teal">
            <Code2 className="w-4 h-4 mr-2" />
            Raw Diff
          </TabsTrigger>
        </TabsList>

        <TabsContent value="url" className="space-y-4">
          <div className="space-y-2">
            <label className="text-xs uppercase tracking-wide text-muted-foreground">
              Pull Request URL
            </label>
            <Input
              placeholder="https://github.com/owner/repo/pull/123"
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              className="glass border-border/50 focus:border-neon-teal/50 transition-all"
            />
          </div>
        </TabsContent>

        <TabsContent value="diff" className="space-y-4">
          <div className="space-y-2">
            <label className="text-xs uppercase tracking-wide text-muted-foreground">
              Diff Content
            </label>
            <Textarea
              placeholder="Paste your git diff content here..."
              value={diffContent}
              onChange={(e) => setDiffContent(e.target.value)}
              className="glass border-border/50 focus:border-neon-teal/50 min-h-[200px] font-mono text-sm transition-all"
            />
          </div>
        </TabsContent>
      </Tabs>

      <Button
        onClick={handleSubmit}
        disabled={isLoading || (activeTab === "url" ? !githubUrl : !diffContent)}
        variant="cyber"
        size="lg"
        className="w-full mt-6 relative group"
      >
        <Play className="w-4 h-4 mr-2" />
        {isLoading ? "Processing..." : "Initialize Review Sequence"}
        
        {!isLoading && (
          <div className="absolute inset-0 rounded-sm opacity-0 group-hover:opacity-100 transition-opacity">
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-neon-teal/20 to-transparent animate-data-flow" />
          </div>
        )}
      </Button>
    </div>
  );
};

export default PRInputModule;
