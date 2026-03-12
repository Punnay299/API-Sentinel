import React from 'react';
import { useAnalyticsSummary } from '@/hooks';
import { Card } from '@/components/ui/Card';
import { ShieldAlert, AlertTriangle, Ghost, Activity } from 'lucide-react';

export default function Dashboard() {
  const { data: analytics, isLoading, error } = useAnalyticsSummary();

  if (isLoading) return <div className="text-muted">Loading analytics...</div>;
  if (error || !analytics) return <div className="text-critical">Failed to load dashboard.</div>;

  return (
    <div>
      <h1 className="mb-6 font-semibold" style={{ fontSize: '1.5rem' }}>Platform Overview</h1>
      
      <div className="grid grid-cols-4 gap-6 mb-6">
        <Card title="Total APIs Managed" value={analytics.total_apis}>
            <div className="flex items-center gap-2 text-sm mt-4 text-muted">
               <Activity size={14} /> Active Scans context available
            </div>
        </Card>
        
        <Card title="Security Posture" value={analytics.avg_security_score}>
            <div className="progress-rail mt-4">
               <div 
                  className="progress-track" 
                  style={{ width: `${Math.min(100, (analytics.avg_security_score / 100) * 100)}%` }} 
               />
            </div>
        </Card>

        <Card title="Zombie Density" value={`${analytics.zombie_percentage}%`}>
             <div className="flex items-center gap-2 text-sm mt-4 text-zombie" style={{ color: 'var(--color-zombie)' }}>
               <Ghost size={14} /> Requires attention
            </div>
        </Card>

        <Card title="Critical Risks" value={analytics.critical_apis}>
             <div className="flex items-center gap-2 text-sm mt-4 text-critical">
               <AlertTriangle size={14} /> Unauthenticated/Shadow
            </div>
        </Card>
      </div>

      <div className="grid grid-cols-2 gap-6">
         <Card title="Classification Breakdown">
            <div className="flex-col gap-4 mt-4 text-sm font-mono">
               {Object.entries(analytics.status_breakdown).map(([status, count]) => (
                   <div key={status} className="flex justify-between" style={{ padding: '8px 0', borderBottom: '1px solid var(--color-surface-border)'}}>
                       <span style={{ textTransform: 'capitalize' }}>{status}</span>
                       <span>{count as number}</span>
                   </div>
               ))}
            </div>
         </Card>
         
         <Card title="Threat Surface Area">
            <div className="flex items-center justify-center p-8 text-secondary">
               <ShieldAlert size={64} style={{ opacity: 0.1 }} />
            </div>
            <div className="text-center font-mono text-xs text-muted">
                {analytics.shadow_count} Shadow APIs detected. Recommend immediate mitigation flow.
            </div>
         </Card>
      </div>
    </div>
  );
}
