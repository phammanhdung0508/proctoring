import type { AnalysisMetadata } from '../types';

const STEP_CONFIG = [
  { key: 'preprocessing_time_ms', label: 'Preprocessing' },
  { key: 'detection_time_ms', label: 'Detection' },
  { key: 'processing_time_ms', label: 'Post Processing' },
] as const;

type PipelineTimelineProps = {
  metadata?: AnalysisMetadata;
};

export function PipelineTimeline({ metadata }: PipelineTimelineProps) {
  const steps = STEP_CONFIG.map((step) => {
    const value = metadata?.[step.key];
    return {
      ...step,
      value: typeof value === 'number' ? value : undefined,
    };
  });

  const maxValue = Math.max(
    1,
    ...steps.map((step) => step.value ?? 0),
  );

  return (
    <div className="glass p-6 rounded-2xl shadow-sm" data-testid="pipeline-timeline">
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-1">Pipeline Timing</p>
          <h3 className="text-lg font-bold text-slate-900">Latest Analysis Steps</h3>
        </div>
        {metadata?.timestamp && (
          <span className="text-xs font-mono text-slate-500">{new Date(metadata.timestamp * 1000).toLocaleTimeString()}</span>
        )}
      </div>

      <div className="space-y-4">
        {steps.every((step) => step.value === undefined) ? (
          <div className="text-sm text-slate-400 italic">No timing data available yet.</div>
        ) : (
          steps.map((step) => (
            <div key={step.key} className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="font-semibold text-slate-700">{step.label}</span>
                <span className="font-mono text-slate-500">
                  {step.value !== undefined ? `${step.value.toFixed(0)} ms` : '—'}
                </span>
              </div>
              <div className="w-full bg-slate-200/70 h-2 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full bg-indigo-500/80 transition-all duration-300"
                  style={{ width: `${Math.min(((step.value ?? 0) / maxValue) * 100, 100)}%` }}
                ></div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
