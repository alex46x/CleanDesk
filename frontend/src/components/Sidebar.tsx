// src/components/Sidebar.tsx — Navigation sidebar

import React from 'react';
import {
  LayoutDashboard,
  Files,
  ListFilter,
  ScrollText,
  Settings,
  CopyX,
  Sparkles,
} from 'lucide-react';
import { useAppStore, View } from '@/store/appStore';
import { motion } from 'framer-motion';

interface NavItem {
  id: View;
  label: string;
  icon: React.ReactNode;
  badge?: string;
}

const NAV_ITEMS: NavItem[] = [
  { id: 'dashboard',   label: 'Dashboard',   icon: <LayoutDashboard size={18} /> },
  { id: 'preview',     label: 'File Preview', icon: <Files size={18} /> },
  { id: 'duplicates',  label: 'Duplicates',   icon: <CopyX size={18} /> },
  { id: 'rules',       label: 'Rule Editor',  icon: <ListFilter size={18} /> },
  { id: 'logs',        label: 'Activity Log', icon: <ScrollText size={18} /> },
  { id: 'settings',    label: 'Settings',     icon: <Settings size={18} /> },
];

export default function Sidebar() {
  const { activeView, setActiveView } = useAppStore();

  return (
    <aside className="w-58 flex-shrink-0 flex flex-col bg-[#0d0d12] border-r border-white/5 py-4 px-3">
      {/* Branding */}
      <div className="flex items-center gap-2 px-2 mb-6">
        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-violet-600 to-cyan-400 flex items-center justify-center shadow-lg shadow-violet-900/40">
          <Sparkles size={15} className="text-white" />
        </div>
        <div>
          <p className="text-xs font-bold text-white leading-none">File Organizer</p>
          <p className="text-[10px] text-violet-400 font-medium mt-0.5">AI-Powered</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex flex-col gap-1 flex-1">
        {NAV_ITEMS.map((item) => (
          <motion.button
            key={item.id}
            id={`nav-${item.id}`}
            whileTap={{ scale: 0.97 }}
            onClick={() => setActiveView(item.id)}
            className={`nav-item ${activeView === item.id ? 'active' : ''}`}
          >
            <span className={activeView === item.id ? 'text-violet-400' : 'text-white/40'}>
              {item.icon}
            </span>
            <span>{item.label}</span>
            {item.badge && (
              <span className="ml-auto text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-violet-600/30 text-violet-300">
                {item.badge}
              </span>
            )}
          </motion.button>
        ))}
      </nav>

      {/* Version */}
      <p className="text-[10px] text-white/20 text-center mt-4">v1.0.0 — Phase 1</p>
    </aside>
  );
}
