import { useEffect, useRef } from "react";
import { Terminal } from "lucide-react";

interface StatusStreamProps {
  logs: string[];
  isActive: boolean;
}

const StatusStream = ({ logs, isActive }: StatusStreamProps) => {
  const streamRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (streamRef.current) {
      streamRef.current.scrollTop = streamRef.current.scrollHeight;
    }
  }, [logs]);

  if (!isActive && logs.length === 0) {
    return null;
  }

  return (
    <div className="glass-strong p-6 rounded-sm border border-border/50 relative overflow-hidden">
      <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-holo-purple to-transparent opacity-60" />
      
      <div className="flex items-center gap-2 mb-4">
        <Terminal className="w-4 h-4 text-holo-purple" />
        <h3 className="text-sm font-semibold text-holo-purple uppercase tracking-wide">
          System Activity Stream
        </h3>
        {isActive && (
          <div className="ml-auto flex items-center gap-2">
            <span className="text-xs text-muted-foreground">ACTIVE</span>
            <div className="w-2 h-2 bg-holo-purple rounded-full animate-pulse" />
          </div>
        )}
      </div>

      <div
        ref={streamRef}
        className="space-y-1 max-h-64 overflow-y-auto font-mono text-xs custom-scrollbar"
      >
        {logs.length === 0 ? (
          <div className="text-muted-foreground italic">Waiting for input...</div>
        ) : (
          logs.map((log, index) => (
            <div
              key={index}
              className="flex items-start gap-2 animate-slide-in text-foreground/80"
              style={{ animationDelay: `${index * 0.05}s` }}
            >
              <span className="text-neon-teal mt-0.5">▸</span>
              <span>{log}</span>
            </div>
          ))
        )}
        {isActive && (
          <div className="flex items-center gap-2 text-neon-teal animate-pulse">
            <span>▸</span>
            <span className="inline-block w-2 h-3 bg-neon-teal animate-pulse" />
          </div>
        )}
      </div>

      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: hsl(var(--carbon));
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: hsl(var(--neon-teal) / 0.5);
          border-radius: 2px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: hsl(var(--neon-teal) / 0.8);
        }
      `}</style>
    </div>
  );
};

export default StatusStream;
