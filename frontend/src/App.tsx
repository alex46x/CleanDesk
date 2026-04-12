// src/App.tsx — Root application shell

import React, { useEffect } from 'react';
import { Toaster } from 'react-hot-toast';
import TitleBar from '@/components/TitleBar';
import Sidebar from '@/components/Sidebar';
import Dashboard from '@/components/Dashboard';
import FilePreview from '@/components/FilePreview';
import RuleEditor from '@/components/RuleEditor';
import LogViewer from '@/components/LogViewer';
import Settings from '@/components/Settings';
import DuplicateDetector from '@/components/DuplicateDetector';
import { useAppStore } from '@/store/appStore';
import { useWebSocket } from '@/hooks/useWebSocket';
import { api } from '@/lib/api';
import { motion, AnimatePresence } from 'framer-motion';

const VIEWS: Record<string, React.ReactNode> = {
  dashboard:  <Dashboard />,
  preview:    <FilePreview />,
  duplicates: <DuplicateDetector />,
  rules:      <RuleEditor />,
  logs:       <LogViewer />,
  settings:   <Settings />,
};

function BackendStatus() {
  const [online, setOnline] = React.useState<boolean | null>(null);

  useEffect(() => {
    const check = async () => {
      try {
        await api.health();
        setOnline(true);
      } catch {
        setOnline(false);
      }
    };
    check();
    const interval = setInterval(check, 10_000);
    return () => clearInterval(interval);
  }, []);

  if (online === null) return null;

  return (
    <div
      className={`flex items-center gap-1.5 text-[11px] font-medium px-3 py-1 rounded-full ${
        online
          ? 'bg-emerald-500/10 text-emerald-400'
          : 'bg-rose-500/10 text-rose-400'
      }`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          online ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'
        }`}
      />
      {online ? 'API Connected' : 'API Offline'}
    </div>
  );
}

export default function App() {
  const { activeView } = useAppStore();
  useWebSocket(); // Establish persistent WebSocket connection

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-[#0f0f13]">
      {/* Custom title bar */}
      <TitleBar />

      {/* Status bar under title */}
      <div className="flex items-center justify-end px-4 py-1 bg-[#0a0a0e] border-b border-white/5 flex-shrink-0">
        <BackendStatus />
      </div>

      {/* Main layout */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />

        {/* Content area with page transitions */}
        <main className="flex-1 overflow-hidden bg-animated-gradient relative">
          {/* Subtle grid overlay */}
          <div
            className="absolute inset-0 pointer-events-none opacity-[0.025]"
            style={{
              backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
                                linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
              backgroundSize: '40px 40px',
            }}
          />

          <AnimatePresence mode="wait">
            <motion.div
              key={activeView}
              initial={{ opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -12 }}
              transition={{ duration: 0.18, ease: 'easeOut' }}
              className="absolute inset-0 overflow-hidden"
            >
              {VIEWS[activeView] ?? <Dashboard />}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>

      {/* Toast notifications */}
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: '#1a1a24',
            color: '#f0f0f8',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '12px',
            fontSize: '13px',
            fontFamily: 'Inter, sans-serif',
          },
          success: {
            iconTheme: { primary: '#34d399', secondary: '#1a1a24' },
          },
          error: {
            iconTheme: { primary: '#fb7185', secondary: '#1a1a24' },
          },
        }}
      />
    </div>
  );
}
