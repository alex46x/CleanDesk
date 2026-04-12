// src/components/TitleBar.tsx — Custom frameless window title bar

import React from 'react';
import { Minus, Square, X, Brain } from 'lucide-react';

const electron = (window as any).electron;

export default function TitleBar() {
  return (
    <div className="title-bar flex items-center justify-between h-10 px-4 bg-[#0a0a0e] border-b border-white/5 flex-shrink-0">
      {/* Logo + Title */}
      <div className="flex items-center gap-2.5">
        <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-violet-600 to-cyan-500 flex items-center justify-center">
          <Brain size={13} className="text-white" />
        </div>
        <span className="text-sm font-semibold text-white/80 tracking-wide">
          Smart File Organizer <span className="text-violet-400">AI</span>
        </span>
      </div>

      {/* Window controls */}
      <div className="flex items-center gap-1">
        <button
          id="btn-minimize"
          onClick={() => electron?.minimize()}
          className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-white/8 transition-colors text-white/50 hover:text-white"
        >
          <Minus size={13} />
        </button>
        <button
          id="btn-maximize"
          onClick={() => electron?.maximize()}
          className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-white/8 transition-colors text-white/50 hover:text-white"
        >
          <Square size={11} />
        </button>
        <button
          id="btn-close"
          onClick={() => electron?.close()}
          className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-rose-500/80 transition-colors text-white/50 hover:text-white"
        >
          <X size={13} />
        </button>
      </div>
    </div>
  );
}
