// src/store/appStore.ts — Zustand global state

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

export type View = 'dashboard' | 'preview' | 'rules' | 'logs' | 'settings' | 'duplicates';

export interface ScanSession {
  id: number;
  root_path: string;
  started_at: number | null;
  completed_at: number | null;
  total_files: number | null;
  status: string;
}

export interface FileRecord {
  id: number;
  path: string;
  name: string;
  extension: string | null;
  size: number | null;
  category: string | null;
  last_modified: number | null;
}

export interface LogRecord {
  id: number;
  old_path: string;
  new_path: string;
  operation: string;
  status: string;
  timestamp: number;
  error_message: string | null;
}

export interface OrganizeResult {
  total: number;
  succeeded: number;
  failed: number;
  dry_run: boolean;
}

export interface ScanProgress {
  total_files: number;
  processed: number;
  files_per_second: number;
}

interface AppState {
  // Navigation
  activeView: View;
  setActiveView: (v: View) => void;

  // Scan
  scanPaths: string[];
  setScanPaths: (paths: string[]) => void;
  currentSession: ScanSession | null;
  setCurrentSession: (s: ScanSession | null) => void;
  scanProgress: ScanProgress;
  setScanProgress: (p: Partial<ScanProgress>) => void;
  isScanning: boolean;
  setIsScanning: (v: boolean) => void;

  // Files
  files: FileRecord[];
  setFiles: (f: FileRecord[]) => void;
  selectedFiles: Set<number>;
  toggleFileSelection: (id: number) => void;
  clearSelection: () => void;

  // Organize
  destinationBase: string;
  setDestinationBase: (d: string) => void;
  organizeResult: OrganizeResult | null;
  setOrganizeResult: (r: OrganizeResult | null) => void;
  isOrganizing: boolean;
  setIsOrganizing: (v: boolean) => void;

  // Logs
  logs: LogRecord[];
  setLogs: (l: LogRecord[]) => void;

  // Stats
  categoryStats: Record<string, number>;
  setCategoryStats: (s: Record<string, number>) => void;

  // Settings
  dryRunMode: boolean;
  toggleDryRun: () => void;
  autoOrganize: boolean;
  toggleAutoOrganize: () => void;
}

export const useAppStore = create<AppState>()(
  devtools(
    (set, get) => ({
      // Navigation
      activeView: 'dashboard',
      setActiveView: (v) => set({ activeView: v }),

      // Scan
      scanPaths: [],
      setScanPaths: (paths) => set({ scanPaths: paths }),
      currentSession: null,
      setCurrentSession: (s) => set({ currentSession: s }),
      scanProgress: { total_files: 0, processed: 0, files_per_second: 0 },
      setScanProgress: (p) =>
        set((state) => ({ scanProgress: { ...state.scanProgress, ...p } })),
      isScanning: false,
      setIsScanning: (v) => set({ isScanning: v }),

      // Files
      files: [],
      setFiles: (f) => set({ files: f }),
      selectedFiles: new Set(),
      toggleFileSelection: (id) =>
        set((state) => {
          const next = new Set(state.selectedFiles);
          if (next.has(id)) next.delete(id);
          else next.add(id);
          return { selectedFiles: next };
        }),
      clearSelection: () => set({ selectedFiles: new Set() }),

      // Organize
      destinationBase: '',
      setDestinationBase: (d) => set({ destinationBase: d }),
      organizeResult: null,
      setOrganizeResult: (r) => set({ organizeResult: r }),
      isOrganizing: false,
      setIsOrganizing: (v) => set({ isOrganizing: v }),

      // Logs
      logs: [],
      setLogs: (l) => set({ logs: l }),

      // Stats
      categoryStats: {},
      setCategoryStats: (s) => set({ categoryStats: s }),

      // Settings
      dryRunMode: false,
      toggleDryRun: () => set((s) => ({ dryRunMode: !s.dryRunMode })),
      autoOrganize: false,
      toggleAutoOrganize: () => set((s) => ({ autoOrganize: !s.autoOrganize })),
    }),
    { name: 'smart-file-organizer' }
  )
);
