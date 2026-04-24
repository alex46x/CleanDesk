// src/components/Dashboard.tsx — Main dashboard view

import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FolderOpen, Zap, Shield, TrendingUp,
  Image, Video, Music, FileText, Code, Archive,
  HardDrive, Activity, ChevronRight, Plus, X, Loader2, Files,
} from 'lucide-react';
import { useAppStore } from '@/store/appStore';
import { api } from '@/lib/api';
import toast from 'react-hot-toast';
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  Images:      <Image size={14} />,
  Videos:      <Video size={14} />,
  Audio:       <Music size={14} />,
  Documents:   <FileText size={14} />,
  Code:        <Code size={14} />,
  Archives:    <Archive size={14} />,
};

const CATEGORY_COLORS: Record<string, string> = {
  Images:      '#22d3ee',
  Videos:      '#f59e0b',
  Audio:       '#a78bfa',
  Documents:   '#34d399',
  Code:        '#fb7185',
  Archives:    '#60a5fa',
  Others:      '#9ca3af',
};

const STATS = [
  { label: 'Files Scanned',  icon: <HardDrive size={20} />, color: '#7c3aed', key: 'total_files' },
  { label: 'Organized',      icon: <Zap size={20} />,       color: '#22d3ee', key: 'organized' },
  { label: 'Protected',      icon: <Shield size={20} />,    color: '#34d399', key: 'protected' },
  { label: 'Speed (f/s)',    icon: <Activity size={20} />,  color: '#fbbf24', key: 'speed' },
];

export default function Dashboard() {
  const {
    scanPaths, setScanPaths, isScanning, setIsScanning,
    scanProgress, currentSession, setCurrentSession,
    categoryStats, setCategoryStats, destinationBase, setDestinationBase,
    dryRunMode, isOrganizing, setIsOrganizing, setOrganizeResult, setFiles,
  } = useAppStore();

  const [newPath, setNewPath] = useState('');

  const addPath = useCallback(() => {
    const p = newPath.trim();
    if (p && !scanPaths.includes(p)) {
      setScanPaths([...scanPaths, p]);
    }
    setNewPath('');
  }, [newPath, scanPaths, setScanPaths]);

  const removePath = useCallback(
    (p: string) => setScanPaths(scanPaths.filter((x) => x !== p)),
    [scanPaths, setScanPaths]
  );

  const handleScan = useCallback(async () => {
    if (scanPaths.length === 0) {
      toast.error('Add at least one folder to scan');
      return;
    }
    setIsScanning(true);
    setFiles([]);
    setCategoryStats({});
    try {
      const session = await api.startScan(scanPaths, false);
      setCurrentSession(session);
      toast.success('Scan started!');

      // Polling function checks the latest session
      const pollFn = async () => {
        try {
          const sessions = await api.getSessions().catch(() => []);
          const latest = sessions[0];
          
          if (latest && latest.status !== 'running') {
            setIsScanning(false);
            setCurrentSession(latest);

            const stats = await api.getSessionStats(latest.id);
            setCategoryStats(stats.categories);
            
            if (latest.status === 'done') {
              toast.success(`Scan complete — ${latest.total_files} files found`);
            } else {
              toast.error('Scan failed during execution.');
            }
            return true; // indicates we should stop polling
          }
        } catch (e) {
          // ignore network errors
        }
        return false;
      };

      // Poll until done
      const poll = setInterval(async () => {
        const done = await pollFn();
        if (done) clearInterval(poll);
      }, 1500);
    } catch (err: any) {
      setIsScanning(false);
      const msg = err.response?.data?.detail || err.message;
      toast.error(`Scan failed: ${msg}`);
    }
  }, [scanPaths, setIsScanning, setCurrentSession, setFiles, setCategoryStats]);

  const handleOrganize = useCallback(async () => {
    if (!currentSession || !destinationBase) {
      toast.error('Run a scan first and set a destination folder');
      return;
    }
    setIsOrganizing(true);
    try {
      const result = await api.organize(
        currentSession.id,
        destinationBase,
        dryRunMode
      );
      setOrganizeResult(result);
      toast.success(
        dryRunMode
          ? `Dry run: would move ${result.total} files`
          : `Organized ${result.succeeded} files!`
      );
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message;
      toast.error(`Organize failed: ${msg}`);
    } finally {
      setIsOrganizing(false);
    }
  }, [currentSession, destinationBase, dryRunMode, setIsOrganizing, setOrganizeResult]);

  const pieData = Object.entries(categoryStats).map(([name, value]) => ({
    name, value,
  }));

  const progressPct =
    scanProgress.total_files > 0
      ? Math.round((scanProgress.processed / scanProgress.total_files) * 100)
      : 0;

  return (
    <div className="h-full overflow-y-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">
            Smart File Organizer <span className="gradient-text">AI</span>
          </h1>
          <p className="text-sm text-white/50 mt-1">
            Scan, classify, and organize your entire file system with one click
          </p>
        </div>

        <div className="flex items-center gap-3">
          {dryRunMode && (
            <span className="badge bg-amber-400/15 text-amber-400 border border-amber-400/25">
              🔍 Dry Run Mode
            </span>
          )}
          <button
            id="btn-organize"
            onClick={handleOrganize}
            disabled={isOrganizing || isScanning || !currentSession}
            className="btn-secondary disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isOrganizing ? <Loader2 size={15} className="animate-spin" /> : <Zap size={15} />}
            Organize Now
          </button>
          <button
            id="btn-scan"
            onClick={handleScan}
            disabled={isScanning}
            className="btn-primary disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isScanning ? (
              <Loader2 size={15} className="animate-spin" />
            ) : (
              <FolderOpen size={15} />
            )}
            {isScanning ? 'Scanning…' : 'Start Scan'}
          </button>
        </div>
      </div>

      {/* Progress bar */}
      <AnimatePresence>
        {isScanning && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="glass p-4 space-y-2"
          >
            <div className="flex justify-between text-sm">
              <span className="text-white/70 font-medium">Scanning file system…</span>
              <span className="text-violet-400 font-mono font-bold">{progressPct}%</span>
            </div>
            <div className="w-full bg-white/10 rounded-full h-1.5 overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-violet-600 to-cyan-400 rounded-full"
                animate={{ width: `${progressPct}%` }}
                transition={{ ease: 'easeOut' }}
              />
            </div>
            <div className="flex gap-6 text-xs text-white/40">
              <span>{scanProgress.processed.toLocaleString()} processed</span>
              <span>{Math.round(scanProgress.files_per_second).toLocaleString()} files/sec</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Scan path configurator + Destination */}
      <div className="grid grid-cols-2 gap-4">
        {/* Source paths */}
        <div className="glass p-5 space-y-3">
          <h2 className="text-sm font-semibold text-white/80 flex items-center gap-2">
            <FolderOpen size={15} className="text-violet-400" />
            Source Folders
          </h2>
          <div className="flex gap-2">
            <input
              id="input-scan-path"
              type="text"
              value={newPath}
              onChange={(e) => setNewPath(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addPath()}
              placeholder="e.g. C:\Users\You\Downloads"
              className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder:text-white/25 focus:outline-none focus:border-violet-500 transition-colors"
            />
            <button
              id="btn-add-path"
              onClick={addPath}
              className="p-2 rounded-xl bg-violet-600/30 hover:bg-violet-600/50 border border-violet-500/30 transition-colors text-violet-300"
            >
              <Plus size={16} />
            </button>
          </div>
          <ul className="space-y-1.5">
            {scanPaths.map((p) => (
              <li
                key={p}
                className="flex items-center justify-between px-3 py-2 rounded-lg bg-white/4 border border-white/6 text-xs text-white/70"
              >
                <span className="truncate font-mono">{p}</span>
                <button
                  onClick={() => removePath(p)}
                  className="ml-2 text-white/30 hover:text-rose-400 transition-colors flex-shrink-0"
                >
                  <X size={12} />
                </button>
              </li>
            ))}
            {scanPaths.length === 0 && (
              <p className="text-xs text-white/25 text-center py-2">No folders added</p>
            )}
          </ul>
        </div>

        {/* Destination */}
        <div className="glass p-5 space-y-3">
          <h2 className="text-sm font-semibold text-white/80 flex items-center gap-2">
            <HardDrive size={15} className="text-cyan-400" />
            Destination Base Folder
          </h2>
          <input
            id="input-destination"
            type="text"
            value={destinationBase}
            onChange={(e) => setDestinationBase(e.target.value)}
            placeholder="e.g. D:\Organized"
            className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder:text-white/25 focus:outline-none focus:border-cyan-500 transition-colors"
          />
          <p className="text-xs text-white/30">
            Files will be moved to sub-folders like:
            <br />
            <span className="font-mono text-cyan-400">
              {destinationBase || 'D:\\Organized'}
              \Images, \Videos, \Documents…
            </span>
          </p>
          {currentSession && (
            <div className="mt-2 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300">
              ✓ Session #{currentSession.id} ready —{' '}
              <span className="font-semibold">
                {(currentSession.total_files || 0).toLocaleString()} files
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-4 gap-4">
        {STATS.map((stat) => {
          const val =
            stat.key === 'total_files'
              ? (currentSession?.total_files || 0)
              : stat.key === 'speed'
              ? Math.round(scanProgress.files_per_second)
              : 0;
          return (
            <motion.div
              key={stat.label}
              whileHover={{ y: -2, boxShadow: `0 8px 32px ${stat.color}30` }}
              className="stat-card p-4"
            >
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center mb-3"
                style={{ background: `${stat.color}20`, color: stat.color }}
              >
                {stat.icon}
              </div>
              <p className="text-2xl font-bold text-white">
                {val.toLocaleString()}
              </p>
              <p className="text-xs text-white/50 mt-0.5">{stat.label}</p>
            </motion.div>
          );
        })}
      </div>

      {/* Category chart + breakdown */}
      {pieData.length > 0 && (
        <div className="grid grid-cols-2 gap-4">
          {/* Pie chart */}
          <div className="glass p-5">
            <h2 className="text-sm font-semibold text-white/80 mb-3 flex items-center gap-2">
              <TrendingUp size={15} className="text-violet-400" />
              File Distribution
            </h2>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {pieData.map((entry) => (
                    <Cell
                      key={entry.name}
                      fill={CATEGORY_COLORS[entry.name] || '#6b7280'}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: '#1a1a24',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: 12,
                    fontSize: 12,
                    color: '#fff',
                  }}
                />
                <Legend
                  iconType="circle"
                  iconSize={8}
                  wrapperStyle={{ fontSize: 11, color: '#aaa' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Category list */}
          <div className="glass p-5 space-y-2 overflow-y-auto max-h-80">
            <h2 className="text-sm font-semibold text-white/80 mb-3 flex items-center gap-2">
              <Files size={15} className="text-cyan-400" />
              Categories
            </h2>
            {pieData
              .sort((a, b) => b.value - a.value)
              .map((item) => {
                const total = pieData.reduce((s, i) => s + i.value, 0);
                const pct = total > 0 ? Math.round((item.value / total) * 100) : 0;
                const color = CATEGORY_COLORS[item.name] || '#6b7280';
                return (
                  <div key={item.name} className="flex items-center gap-3">
                    <span
                      className="w-7 h-7 rounded-lg flex items-center justify-center text-white flex-shrink-0"
                      style={{ background: `${color}25` }}
                    >
                      {CATEGORY_ICONS[item.name] || <Archive size={14} />}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between items-baseline mb-0.5">
                        <span className="text-xs font-medium text-white/80">{item.name}</span>
                        <span className="text-xs text-white/40 font-mono">{item.value.toLocaleString()}</span>
                      </div>
                      <div className="w-full bg-white/8 rounded-full h-1">
                        <div
                          className="h-1 rounded-full transition-all duration-500"
                          style={{ width: `${pct}%`, background: color }}
                        />
                      </div>
                    </div>
                    <span className="text-[11px] text-white/30 w-8 text-right">{pct}%</span>
                  </div>
                );
              })}
          </div>
        </div>
      )}
    </div>
  );
}
