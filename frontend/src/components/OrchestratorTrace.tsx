import React from 'react';
import { Cpu, Zap, Eye, Compass, Info } from 'lucide-react';
import type { AgentTier } from '../types/api';

interface OrchestratorTraceProps {
  tier: AgentTier;
  reasoning?: string;
}

export const OrchestratorTrace: React.FC<OrchestratorTraceProps> = ({ tier, reasoning }) => {
  const getTierBadge = () => {
    switch (tier) {
      case 'SKILL':
        return {
          label: 'Tier 1: Skill Agent',
          icon: <Zap className="w-4 h-4 text-emerald-500" />,
          color: 'bg-emerald-50 border-emerald-200 text-emerald-800',
          speed: '<500ms Ultra-Fast Lookup',
        };
      case 'REACTIVE':
        return {
          label: 'Tier 2: Reactive Agent',
          icon: <Eye className="w-4 h-4 text-sky-500" />,
          color: 'bg-sky-50 border-sky-200 text-sky-800',
          speed: 'Multi-Modal Computer Vision Pipeline',
        };
      case 'DEEP':
        return {
          label: 'Tier 3: Deep Agent',
          icon: <Compass className="w-4 h-4 text-purple-500" />,
          color: 'bg-purple-50 border-purple-200 text-purple-800',
          speed: 'Autonomous Bedrock Knowledge Base Investigation',
        };
      default:
        return {
          label: 'Autonomous Routing',
          icon: <Cpu className="w-4 h-4 text-slate-500" />,
          color: 'bg-slate-50 border-slate-200 text-slate-800',
          speed: 'Standard Inspection',
        };
    }
  };

  const badge = getTierBadge();

  return (
    <div className="bg-white rounded-xl border border-slate-200/80 p-3.5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center space-x-2">
          <div className="p-1.5 rounded-lg bg-slate-100 text-slate-700">
            <Cpu className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Orchestrator Routing Decision
              </span>
              <span className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-md text-xs font-medium border ${badge.color}`}>
                {badge.icon}
                <span>{badge.label}</span>
              </span>
            </div>
          </div>
        </div>

        <span className="text-[11px] font-mono text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
          {badge.speed}
        </span>
      </div>

      {reasoning && (
        <div className="mt-2.5 pt-2 border-t border-slate-100 flex items-start space-x-2 text-xs text-slate-600">
          <Info className="w-3.5 h-3.5 text-slate-400 mt-0.5 flex-shrink-0" />
          <p className="leading-relaxed">
            <strong className="text-slate-700 font-medium">Orchestration Reasoning:</strong> {reasoning}
          </p>
        </div>
      )}
    </div>
  );
};
