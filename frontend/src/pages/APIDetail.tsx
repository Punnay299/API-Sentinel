
import { useParams, useNavigate } from 'react-router-dom';
import { useAPI, useDecommissionStatus, useStartDecommission, useReanalyzeAPI } from '@/hooks';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ArrowLeft, ShieldAlert, Activity, GitBranch, RefreshCw, PowerOff, CheckCircle2 } from 'lucide-react';

export default function APIDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: api, isLoading, error } = useAPI(id!);
  const { mutate: reanalyze, isPending: isAnalyzing } = useReanalyzeAPI();
  const { mutate: startDecomm } = useStartDecommission();
  const { data: decommStatus } = useDecommissionStatus(id!);

  if (isLoading) return <div className="p-8 text-center text-muted">Loading intelligence...</div>;
  if (error || !api) return <div className="p-8 text-critical">Failed to load API details.</div>;

  const isDecommissioning = decommStatus && ["pending", "in_progress"].includes(decommStatus.status);
  const isDecommissioned = api.classification.status === "decommissioned" || (decommStatus && decommStatus.status === "completed");

  const handleDecommission = () => {
     if (window.confirm(`Initiate automated decommissioning workflow for ${api.endpoint}?`)) {
         startDecomm(api.id);
     }
  };

  return (
    <div>
       <div className="flex items-center gap-4 mb-6">
          <Button variant="outline" onClick={() => navigate('/inventory')} icon={<ArrowLeft size={16}/>}>
             Back to Inventory
          </Button>
          <div className="flex-1"></div>
          <Button 
             variant="outline" 
             onClick={() => reanalyze(api.id)} 
             disabled={isAnalyzing || isDecommissioned}
             icon={<RefreshCw size={16} className={isAnalyzing ? "animate-spin" : ""} />}
          >
             {isAnalyzing ? "Recalculating..." : "Force ML Re-analysis"}
          </Button>
          <Button 
             variant="critical" 
             onClick={handleDecommission}
             disabled={isDecommissioning || isDecommissioned}
             icon={<PowerOff size={16} />}
          >
             {isDecommissioned ? "DECOMMISSIONED" : isDecommissioning ? "SHUTTING DOWN..." : "DECOMMISSION"}
          </Button>
       </div>

       <div className="card mb-6" style={{ padding: '32px' }}>
          <div className="flex justify-between items-start mb-6">
             <div>
                <div className="flex items-center gap-3 mb-2">
                   <h1 className="font-mono text-primary text-2xl font-bold m-0">{api.endpoint}</h1>
                   <span className="font-mono text-xs px-2 py-1 rounded" style={{ backgroundColor: 'var(--color-surface-hover)', border: '1px solid var(--color-surface-border)' }}>
                     {api.method}
                   </span>
                   {isDecommissioned && <Badge status="Decommissioned" className="ml-2" />}
                </div>
                <div className="text-muted text-sm flex gap-4">
                   <span>ID: {api.id}</span>
                   <span>Owner: {api.owner_team || 'UNASSIGNED'}</span>
                   <span>Source: {api.source}</span>
                </div>
             </div>
             <div className="text-right">
                <div className="text-4xl font-mono font-bold mb-1" style={{ color: api.security.risk_level === 'critical' ? 'var(--color-critical)' : 'inherit' }}>
                  {api.security.security_score}
                </div>
                <div className="text-xs text-muted font-mono tracking-wider">SECURITY SCORE</div>
             </div>
          </div>

          <div className="grid grid-cols-4 gap-4 mt-8 pt-8" style={{ borderTop: '1px solid var(--color-surface-border)'}}>
             <div>
               <div className="text-xs text-muted mb-1">CLASSIFICATION</div>
               <Badge status={api.classification.status} />
             </div>
             <div>
               <div className="text-xs text-muted mb-1">DATA SENSITIVITY</div>
               <div className="font-mono" style={{ textTransform: 'uppercase'}}>{api.data_sensitivity}</div>
             </div>
             <div>
               <div className="text-xs text-muted mb-1">30D CALL VOLUME</div>
               <div className="font-mono text-lg">{api.call_volume_30d.toLocaleString()}</div>
             </div>
             <div>
               <div className="text-xs text-muted mb-1">LAST CALLED</div>
               <div className="font-mono">{api.last_called_at ? new Date(api.last_called_at).toLocaleDateString() : 'Never'}</div>
             </div>
          </div>
       </div>

       <div className="grid grid-cols-2 gap-6">
          {/* Security Findings Hub */}
          <div className="card">
             <h3 className="card-title flex items-center gap-2 mb-4"><ShieldAlert size={16}/> Intelligence Findings</h3>
             
             {api.security.issues.length > 0 ? (
                 <div className="flex-col gap-3">
                   {api.security.issues.map((issue, idx) => (
                      <div key={idx} className="p-3 rounded" style={{ backgroundColor: issue.severity === 'critical' ? 'var(--color-critical-bg)' : 'var(--color-warning-bg)' }}>
                         <div className="flex justify-between items-center mb-1">
                            <span className="font-semibold text-sm" style={{ color: issue.severity === 'critical' ? 'var(--color-critical)' : 'var(--color-warning)'}}>
                               {issue.type}
                            </span>
                            <span className="text-xs font-mono uppercase opacity-70">{issue.severity}</span>
                         </div>
                         <div className="text-xs text-muted">{issue.msg}</div>
                      </div>
                   ))}
                 </div>
             ) : (
                 <div className="text-center p-8 text-success flex items-center justify-center gap-2">
                     <CheckCircle2 size={16}/> No security issues detected
                 </div>
             )}
             
             <div className="mt-6 pt-4" style={{ borderTop: '1px solid var(--color-surface-border)'}}>
                <div className="text-xs text-muted mb-2 font-mono">ML PROBABILITIES</div>
                {Object.entries(api.classification.probabilities).map(([key, val]) => (
                    <div key={key} className="flex items-center gap-2 mb-2">
                       <span className="text-xs" style={{ width: '80px'}}>{key}</span>
                       <div className="progress-rail" style={{ flex: 1, height: '4px' }}>
                           <div className="progress-track" style={{ width: `${val * 100}%`, backgroundColor: 'var(--color-text-secondary)' }} />
                       </div>
                       <span className="text-xs font-mono" style={{ width: '40px', textAlign: 'right'}}>{(val as number * 100).toFixed(0)}%</span>
                    </div>
                ))}
             </div>
          </div>

          {/* Workflow / Remediation Tracker */}
          <div className="card">
             <h3 className="card-title flex items-center gap-2 mb-4"><GitBranch size={16}/> Remediation Tracker</h3>
             
             {decommStatus ? (
                 <div className="flex-col gap-4">
                     <div className="p-4 rounded mb-4" style={{ backgroundColor: 'var(--color-bg-base)', border: '1px solid var(--color-surface-border)' }}>
                        <div className="font-mono text-sm text-primary mb-1">Workflow Status: {decommStatus.status.replace("_", " ").toUpperCase()}</div>
                        <div className="text-xs text-muted">ID: {decommStatus.id}</div>
                     </div>
                     
                     {/* Hardcoded steps from backend for visualization */}
                     {[
                         { id: "identify_callers", label: "Identify Active Callers" },
                         { id: "notify_stakeholders", label: "Notify Stakeholders" },
                         { id: "deprecation_header_deployed", label: "Deploy Deprecation Headers" },
                         { id: "gateway_route_disabled", label: "Disable API Gateway Route" },
                         { id: "traffic_confirmed_zero", label: "Confirm Zero Traffic" },
                         { id: "spec_archived", label: "Archive API Specification" },
                         { id: "service_terminated", label: "Terminate Service" },
                     ].map((step, idx) => {
                         const isCompleted = decommStatus.completed_steps.includes(step.id);
                         const isCurrent = decommStatus.current_step === step.id && decommStatus.status !== "completed";
                         
                         return (
                             <div key={step.id} className="flex items-center gap-3">
                                 <div className="flex justify-center items-center" style={{ 
                                     width: '24px', height: '24px', borderRadius: '50%', 
                                     backgroundColor: isCompleted ? 'var(--color-success)' : isCurrent ? 'var(--color-primary)' : 'var(--color-surface-border)',
                                     color: isCompleted ? 'var(--color-bg-base)' : 'var(--color-text-muted)'
                                  }}>
                                     {isCompleted ? <CheckCircle2 size={14}/> : <span className="text-xs font-mono">{idx + 1}</span>}
                                 </div>
                                 <div className={isCompleted ? 'text-success' : isCurrent ? 'text-primary font-bold animate-pulse' : 'text-muted'}>
                                     {step.label}
                                 </div>
                             </div>
                         )
                     })}
                 </div>
             ) : (
                 <div className="flex-col items-center justify-center p-8 text-center h-full">
                     <Activity size={32} className="text-muted mb-4 opacity-30" />
                     <p className="text-muted text-sm">No active remediation workflows.</p>
                     {api.remediation.map((r, i) => (
                         <div key={i} className="mt-4 p-3 w-full rounded text-left border border-[var(--color-surface-border)] bg-[var(--color-bg-base)]">
                             <div className="text-primary font-bold text-xs font-mono uppercase mb-1">RECOMMENDED ACTION</div>
                             <div className="text-sm">{r.action}: {r.detail}</div>
                         </div>
                     ))}
                 </div>
             )}
          </div>
       </div>
    </div>
  );
}
