import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAPIList } from '@/hooks';
import { Badge } from '@/components/ui/Badge';
import { ShieldAlert, Search } from 'lucide-react';

export default function Inventory() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState({
    status: '',
    risk: '',
    search: '',
  });

  const { data, isLoading } = useAPIList({ ...filters, page_size: 100 });

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="font-semibold" style={{ fontSize: '1.5rem' }}>API Inventory</h1>
        <div className="flex gap-4">
           {/* Simple custom search input for the glassmorphic feel */}
           <div className="flex items-center gap-2 px-3 py-2" style={{ backgroundColor: 'var(--color-surface)', border: '1px solid var(--color-surface-border)', borderRadius: 'var(--radius-md)'}}>
              <Search size={16} className="text-muted" />
              <input 
                type="text" 
                placeholder="Search endpoints..." 
                value={filters.search}
                onChange={e => setFilters(s => ({ ...s, search: e.target.value }))}
                style={{ background: 'transparent', border: 'none', color: 'var(--color-text-primary)', outline: 'none', fontSize: '0.875rem'}}
              />
           </div>
           
           <select 
              value={filters.status} 
              onChange={e => setFilters(s => ({ ...s, status: e.target.value }))}
              style={{ padding: '8px 12px', backgroundColor: 'var(--color-surface)', color: 'var(--color-text-primary)', border: '1px solid var(--color-surface-border)', borderRadius: 'var(--radius-md)', outline: 'none' }}
           >
             <option value="">All Statuses</option>
             <option value="active">Active</option>
             <option value="zombie">Zombie</option>
             <option value="shadow">Shadow</option>
             <option value="orphaned">Orphaned</option>
             <option value="deprecated">Deprecated</option>
           </select>
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {isLoading ? (
           <div className="p-8 text-center text-muted">Loading dependencies...</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>ENDPOINT</th>
                <th>METHOD</th>
                <th>OWNER</th>
                <th>CLASSIFICATION</th>
                <th>RISK</th>
                <th>SCORE</th>
              </tr>
            </thead>
            <tbody>
              {data?.apis.map(api => (
                <tr key={api.id} onClick={() => navigate(`/api/${api.id}`)}>
                  <td className="font-mono text-primary">{api.endpoint}</td>
                  <td className="font-mono text-xs">{api.method}</td>
                  <td className="text-muted">{api.owner_team || 'Unassigned'}</td>
                  <td>
                     <Badge status={api.ml_status} />
                  </td>
                  <td>
                    {api.ml_risk_level === 'critical' && <ShieldAlert size={14} className="text-critical inline mr-1" />}
                    <span style={{ textTransform: 'capitalize' }}>{api.ml_risk_level}</span>
                  </td>
                  <td className="font-mono">{api.ml_security_score}/100</td>
                </tr>
              ))}
              {data?.apis.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center p-8 text-muted">No APIs match the criteria.</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
