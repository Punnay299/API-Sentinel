import React, { useEffect, useRef } from 'react';
import { useScan } from '@/hooks';
import { Button } from '@/components/ui/Button';
import { Play, Activity, ShieldCheck, AlertCircle } from 'lucide-react';

export default function ScanEngine() {
  const { startScan, status, progress, events, apisFound } = useScan();
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
     logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  const handleStart = () => {
    startScan();
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
         <div>
            <h1 className="font-semibold mb-1" style={{ fontSize: '1.5rem' }}>Discovery Engine</h1>
            <p className="text-muted text-sm">Initiate automated infrastructure sweeps and ML baseline re-evaluations.</p>
         </div>
         <Button 
            onClick={handleStart} 
            disabled={status === "running"}
            icon={status === "running" ? <Activity className="animate-spin mr-2" size={16}/> : <Play className="mr-2" size={16}/>}
         >
            {status === "running" ? "SCAN IN PROGRESS" : "START GLOBAL SCAN"}
         </Button>
      </div>

      <div className="grid grid-cols-3 gap-6 mb-6">
         <div className="card col-span-2">
            <h3 className="card-title mb-4">Live Telemetry</h3>
            
            <div className="flex items-center gap-4 mb-2 text-sm font-mono flex-wrap">
               <span className="text-muted">STATUS:</span>
               <span className={status === "running" ? "text-primary" : status === "completed" ? "text-success" : ""}>
                   {status.toUpperCase()}
               </span>
               <span className="text-muted ml-4">APIS DISCOVERED:</span>
               <span className="text-primary">{apisFound}</span>
            </div>

            <div className="progress-rail mt-6 mb-2">
               <div 
                  className={`progress-track ${status === "running" ? "pulsing" : ""}`}
                  style={{ width: `${progress}%` }} 
               />
            </div>
            <div className="text-right text-xs text-muted font-mono">{progress}%</div>
         </div>

         <div className="card flex-col items-center justify-center text-center">
            {status === "completed" ? (
                <>
                   <ShieldCheck size={48} className="text-success mb-4" />
                   <h3 className="font-semibold text-lg">Scan Complete</h3>
                   <p className="text-sm text-muted mt-2">ML Baselines updated. {apisFound} total endpoints analysed.</p>
                </>
            ) : status === "running" ? (
                <>
                   <Activity size={48} className="text-primary mb-4 animate-bounce" />
                   <h3 className="font-semibold text-lg">Analyzing...</h3>
                   <p className="text-sm text-muted mt-2">Correlating gateway logs with repository definitions.</p>
                </>
            ) : (
                <>
                   <AlertCircle size={48} className="text-muted mb-4 opacity-50" />
                   <h3 className="font-semibold text-lg text-muted">System Idle</h3>
                   <p className="text-sm text-muted mt-2">Ready to initiate full environment assessment.</p>
                </>
            )}
         </div>
      </div>

      <div className="log-terminal">
         {events.map((e, idx) => (
             <div key={idx} className="log-entry">
                <span className="log-time">[{new Date(e.created_at).toLocaleTimeString()}]</span>
                <span className="log-source">[{e.source || 'SYSTEM'}]</span>
                <span className="text-primary">{e.message}</span>
                {e.apis_found > 0 && <span className="text-warning">+{e.apis_found} detected</span>}
             </div>
         ))}
         {status === 'running' && (
             <div className="log-entry mt-2 opacity-50">
                <span className="log-source animate-pulse">Waiting for telemetry...</span>
             </div>
         )}
         <div ref={logEndRef} />
      </div>
    </div>
  );
}
