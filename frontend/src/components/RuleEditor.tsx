// src/components/RuleEditor.tsx — Create and manage classification rules

import React, { useState, useEffect } from 'react';
import { Plus, Trash2, ToggleLeft, ToggleRight, Save, AlertCircle } from 'lucide-react';
import { api } from '@/lib/api';
import toast from 'react-hot-toast';
import { motion, AnimatePresence } from 'framer-motion';

interface Rule {
  id: number;
  name: string;
  pattern: string;
  match_type: string;
  category: string;
  target_folder: string;
  priority: number;
  enabled: boolean;
  created_at: number;
}

interface RuleForm {
  name: string;
  pattern: string;
  match_type: string;
  category: string;
  target_folder: string;
  priority: number;
}

const MATCH_TYPES = ['extension', 'glob', 'regex'];
const DEFAULT_FORM: RuleForm = {
  name: '',
  pattern: '',
  match_type: 'extension',
  category: '',
  target_folder: '',
  priority: 0,
};

export default function RuleEditor() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [form, setForm] = useState<RuleForm>(DEFAULT_FORM);
  const [loading, setLoading] = useState(false);

  const fetchRules = async () => {
    const data = await api.getRules().catch(() => []);
    setRules(data);
  };

  useEffect(() => { fetchRules(); }, []);

  const handleCreate = async () => {
    if (!form.name || !form.pattern || !form.category) {
      toast.error('Name, pattern, and category are required');
      return;
    }
    setLoading(true);
    try {
      await api.createRule(form);
      toast.success('Rule created');
      setForm(DEFAULT_FORM);
      await fetchRules();
    } catch (e: any) {
      toast.error(`Failed: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async (rule: Rule) => {
    await api.updateRule(rule.id, { enabled: !rule.enabled }).catch(() => {});
    await fetchRules();
  };

  const handleDelete = async (id: number) => {
    await api.deleteRule(id);
    toast.success('Rule deleted');
    await fetchRules();
  };

  return (
    <div className="h-full overflow-y-auto p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Rule Editor</h1>
        <p className="text-sm text-white/40 mt-0.5">
          Define custom classification rules. Higher priority rules take precedence.
        </p>
      </div>

      {/* Create rule form */}
      <div className="glass p-5 space-y-4">
        <h2 className="text-sm font-semibold text-white/80 flex items-center gap-2">
          <Plus size={15} className="text-violet-400" />
          New Rule
        </h2>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-white/40 mb-1 block">Rule Name</label>
            <input
              id="input-rule-name"
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="e.g. Tax Documents"
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder:text-white/20 focus:outline-none focus:border-violet-500"
            />
          </div>
          <div>
            <label className="text-xs text-white/40 mb-1 block">Match Type</label>
            <select
              id="select-match-type"
              value={form.match_type}
              onChange={(e) => setForm({ ...form, match_type: e.target.value })}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500"
            >
              {MATCH_TYPES.map((t) => (
                <option key={t} value={t} className="bg-[#1a1a24] capitalize">{t}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-white/40 mb-1 block">
              Pattern
              <span className="ml-1 text-white/25">
                ({form.match_type === 'extension' ? 'e.g. .pdf' : form.match_type === 'glob' ? 'e.g. *invoice*' : 'regex'})
              </span>
            </label>
            <input
              id="input-rule-pattern"
              type="text"
              value={form.pattern}
              onChange={(e) => setForm({ ...form, pattern: e.target.value })}
              placeholder={form.match_type === 'extension' ? '.pdf' : '.+_invoice.+'}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm font-mono text-white placeholder:text-white/20 focus:outline-none focus:border-violet-500"
            />
          </div>
          <div>
            <label className="text-xs text-white/40 mb-1 block">Category</label>
            <input
              id="input-rule-category"
              type="text"
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              placeholder="e.g. Finance"
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder:text-white/20 focus:outline-none focus:border-violet-500"
            />
          </div>
          <div>
            <label className="text-xs text-white/40 mb-1 block">Target Folder</label>
            <input
              id="input-rule-target"
              type="text"
              value={form.target_folder}
              onChange={(e) => setForm({ ...form, target_folder: e.target.value })}
              placeholder="e.g. Finance"
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm font-mono text-white placeholder:text-white/20 focus:outline-none focus:border-violet-500"
            />
          </div>
          <div>
            <label className="text-xs text-white/40 mb-1 block">Priority (0–1000)</label>
            <input
              id="input-rule-priority"
              type="number"
              min={0}
              max={1000}
              value={form.priority}
              onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500"
            />
          </div>
        </div>

        <button
          id="btn-create-rule"
          onClick={handleCreate}
          disabled={loading}
          className="btn-primary"
        >
          <Save size={14} />
          Save Rule
        </button>
      </div>

      {/* Rules list */}
      <div className="glass p-5 space-y-3">
        <h2 className="text-sm font-semibold text-white/80">
          Active Rules ({rules.length})
        </h2>

        {rules.length === 0 && (
          <div className="flex items-center gap-2 text-sm text-white/30 py-4">
            <AlertCircle size={15} />
            No custom rules yet. Default extension rules are always applied.
          </div>
        )}

        <AnimatePresence>
          {rules.map((rule) => (
            <motion.div
              key={rule.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10 }}
              className={`flex items-center gap-3 p-3 rounded-xl border transition-colors ${
                rule.enabled
                  ? 'bg-white/4 border-white/8'
                  : 'bg-white/2 border-white/4 opacity-50'
              }`}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-white truncate">{rule.name}</span>
                  <span className="badge text-[10px] bg-violet-400/10 text-violet-400">
                    {rule.match_type}
                  </span>
                  <span className="text-[10px] text-white/30">p:{rule.priority}</span>
                </div>
                <div className="flex items-center gap-3 mt-0.5">
                  <code className="text-xs font-mono text-amber-400">{rule.pattern}</code>
                  <span className="text-xs text-white/30">→</span>
                  <span className="text-xs text-cyan-400">{rule.category}</span>
                  <span className="text-xs text-white/30">→</span>
                  <span className="text-xs text-emerald-400 font-mono">{rule.target_folder}/</span>
                </div>
              </div>

              <button
                onClick={() => handleToggle(rule)}
                className="text-white/40 hover:text-white transition-colors"
                title={rule.enabled ? 'Disable' : 'Enable'}
              >
                {rule.enabled ? (
                  <ToggleRight size={20} className="text-emerald-400" />
                ) : (
                  <ToggleLeft size={20} />
                )}
              </button>

              <button
                onClick={() => handleDelete(rule.id)}
                className="text-white/25 hover:text-rose-400 transition-colors"
                title="Delete rule"
              >
                <Trash2 size={14} />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
