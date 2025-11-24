const HolographicHeader = () => {
  return (
    <header className="relative border-b border-neon-teal/20 circuit-line">
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-neon-teal/5 to-transparent opacity-50" />
      
      <div className="container mx-auto px-6 py-6 relative z-10">
        <div className="flex items-center gap-4">
          <div className="relative">
            <img 
              src="/logo.png" 
              alt="PR Review Agent Logo" 
              className="w-8 h-8 animate-glow-pulse"
            />
            <div className="absolute inset-0 w-8 h-8 blur-md animate-glow-pulse opacity-50">
              <img src="/logo.png" alt="" className="w-full h-full" />
            </div>
          </div>
          
          <div>
            <h1 className="text-2xl font-bold text-glow-teal tracking-tight">
              PR Review Agent
            </h1>
            <p className="text-xs text-muted-foreground tracking-widest uppercase mt-1">
              Automated Reasoning System v1.0
            </p>
          </div>
        </div>
      </div>
      
      {/* Circuit pattern overlay */}
      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-neon-teal to-transparent opacity-60" />
    </header>
  );
};

export default HolographicHeader;
