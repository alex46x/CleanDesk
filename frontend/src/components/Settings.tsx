// src/components/Settings.tsx — App settings panel

import React from 'react';
import {
  Shield, Eye, Zap, Bell, RefreshCw,
  HardDrive, Info, ChevronRight,
} from 'lucide-react';
import { useAppStore } from '@/store/appStore';
import { motion } from 'framer-motion';

interface ToggleRowProps {
  id: string;
  icon: React.ReactNode;
  label: string;
  description: string;
  value: boolean;
  onChange: () => void;
  accent?: string;
}

function ToggleRow({ id, icon, label, description, value, onChange, accent = '#7c3aed' }: ToggleRowProps) {
  return (
    <div className="flex items-center gap-4 p-4 rounded-xl bg-white/3 border border-white/6 hover:bg-white/5 transition-colors">
      <div
        className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
        style={{ background: `${accent}20`, color: accent }}
      >
        {icon}
      </div>
      <div className="flex-1">
        <p className="text-sm font-semibold text-white">{label}</p>
        <p className="text-xs text-white/40 mt-0.5">{description}</p>
      </div>
      <button
        id={id}
        onClick={onChange}
        className={`relative w-11 h-6 rounded-full transition-colors duration-300 flex-shrink-0 ${
          value ? 'bg-violet-600' : 'bg-white/15'
        }`}
      >
        <motion.span
          animate={{ x: value ? 20 : 2 }}
          transition={{ type: 'spring', stiffness: 500, damping: 30 }}
          className="absolute top-1 w-4 h-4 rounded-full bg-white shadow-sm"
        />
      </button>
    </div>
  );
}

export default function Settings() {
  const { dryRunMode, toggleDryRun, autoOrganize, toggleAutoOrganize } = useAppStore();

  return (
    <div className="h-full overflow-y-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-white">Settings</h1>
        <p className="text-sm text-white/40 mt-0.5">
          Configure how Smart File Organizer AI behaves
        </p>
      </div>

      {/* Safety */}
      <section className="space-y-3">
        <h2 className="text-xs font-bold text-white/40 uppercase tracking-widest px-1">
          Safety & Preview
        </h2>
        <div className="space-y-2">
          <ToggleRow
            id="toggle-dry-run"
            icon={<Eye size={17} />}
            label="Dry Run Mode"
            description="Preview all operations without moving any files. No changes are made."
            value={dryRunMode}
            onChange={toggleDryRun}
            accent="#fbbf24"
          />
          <ToggleRow
            id="toggle-auto-organize"
            icon={<Zap size={17} />}
            label="Auto-Organize on Change"
            description="Automatically organize files when new files appear in watched folders."
            value={autoOrganize}
            onChange={toggleAutoOrganize}
            accent="#22d3ee"
          />
        </div>
      </section>

      {/* Performance */}
      <section className="space-y-3">
        <h2 className="text-xs font-bold text-white/40 uppercase tracking-widest px-1">
          Performance
        </h2>
        <div className="glass p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-white">Scanner Threads</p>
              <p className="text-xs text-white/40">Parallel threads used during filesystem scan</p>
            </div>
            <span className="text-sm font-mono font-bold text-violet-400">
              {navigator.hardwareConcurrency || 4} (auto)
            </span>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-white">Incremental Scanning</p>
              <p className="text-xs text-white/40">Skip files with unchanged size and modification time</p>
            </div>
            <span className="badge bg-emerald-400/10 text-emerald-400 border border-emerald-400/20">
              Enabled
            </span>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-white">Hashing Algorithm</p>
              <p className="text-xs text-white/40">Used for duplicate detection</p>
            </div>
            <span className="text-sm font-mono text-cyan-400">XXHash64</span>
          </div>
        </div>
      </section>

      {/* Protected Directories */}
      <section className="space-y-3">
        <h2 className="text-xs font-bold text-white/40 uppercase tracking-widest px-1">
          Protected Directories
        </h2>
        <div className="glass p-4">
          <div className="flex items-start gap-3 mb-3">
            <Shield size={16} className="text-emerald-400 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-white/60">
              The following directories are always protected and will never be modified:
            </p>
          </div>
          <ul className="space-y-1.5">
            {[
              'C:\\Windows',
              'C:\\Program Files',
              'C:\\Program Files (x86)',
              'C:\\ProgramData',
              'C:\\System Volume Information',
              'C:\\$Recycle.Bin',
            ].map((p) => (
              <li key={p} className="flex items-center gap-2 text-xs font-mono text-white/50">
                <Shield size={10} className="text-emerald-400 flex-shrink-0" />
                {p}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* About */}
      <section className="space-y-3">
        <h2 className="text-xs font-bold text-white/40 uppercase tracking-widest px-1">
          About
        </h2>
        <div className="glass p-4 space-y-2">
          {[
            ['Version', '1.0.0'],
            ['Tech Stack', 'Python · FastAPI · Electron · React'],
            ['Database', 'SQLite (PostgreSQL-ready)'],
            ['Scanner', 'Multi-threaded os.scandir() + Rust FFI (Phase 6)'],
          ].map(([k, v]) => (
            <div key={k} className="flex items-center justify-between text-sm">
              <span className="text-white/40">{k}</span>
              <span className="text-white/70 font-mono text-xs">{v}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
