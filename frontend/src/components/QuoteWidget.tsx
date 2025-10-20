import React, { useState, useEffect } from 'react';
import { useRecordContext, useWidgetSettings } from '@attio/sdk';

interface DemandRow {
  id: string;
  habitat_name: string;
  units: number;
}

interface LocationInfo {
  postcode?: string;
  address?: string;
  lpa_name?: string;
  nca_name?: string;
}

interface JobStatus {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress?: string;
  result?: any;
  error?: string;
}

const QuoteWidget: React.FC = () => {
  const { recordId } = useRecordContext();
  const settings = useWidgetSettings();
  const backendUrl = settings.backendUrl || 'http://localhost:8080';
  
  // Form state
  const [demandRows, setDemandRows] = useState<DemandRow[]>([
    { id: '1', habitat_name: '', units: 0 }
  ]);
  const [location, setLocation] = useState<LocationInfo>({});
  const [nextId, setNextId] = useState(2);
  
  // Job state
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  
  // Available habitats - in production, fetch from backend
  const habitatOptions = [
    'Grassland - Other neutral grassland',
    'Woodland - Other woodland; broadleaved',
    'Heathland and shrub - Bramble scrub',
    'Cropland - Arable field margins game bird mix',
    // Add more options
  ];
  
  const addDemandRow = () => {
    setDemandRows([
      ...demandRows,
      { id: String(nextId), habitat_name: '', units: 0 }
    ]);
    setNextId(nextId + 1);
  };
  
  const removeDemandRow = (id: string) => {
    if (demandRows.length > 1) {
      setDemandRows(demandRows.filter(row => row.id !== id));
    }
  };
  
  const updateDemandRow = (id: string, field: keyof DemandRow, value: any) => {
    setDemandRows(demandRows.map(row =>
      row.id === id ? { ...row, [field]: value } : row
    ));
  };
  
  const handleRunQuote = async () => {
    try {
      setIsRunning(true);
      setLogs(['Starting quote optimization...']);
      setJobStatus(null);
      
      // Validate demand
      const validDemand = demandRows.filter(row => row.habitat_name && row.units > 0);
      if (validDemand.length === 0) {
        setLogs([...logs, 'Error: Please add at least one demand row with habitat and units']);
        setIsRunning(false);
        return;
      }
      
      // Start job
      const response = await fetch(`${backendUrl}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          record_id: recordId,
          demand: validDemand.map(row => ({
            habitat_name: row.habitat_name,
            units: row.units
          })),
          location: location
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      const newJobId = data.job_id;
      setJobId(newJobId);
      setLogs([...logs, `Job started with ID: ${newJobId}`, 'Polling for status...']);
      
      // Start polling
      pollJobStatus(newJobId);
      
    } catch (error) {
      setLogs([...logs, `Error: ${error.message}`]);
      setIsRunning(false);
    }
  };
  
  const pollJobStatus = async (jobId: string) => {
    const pollInterval = 2000; // 2 seconds
    const maxAttempts = 150; // 5 minutes max
    let attempts = 0;
    
    const poll = async () => {
      try {
        const response = await fetch(`${backendUrl}/status/${jobId}`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const status: JobStatus = await response.json();
        setJobStatus(status);
        
        if (status.progress) {
          setLogs(prev => [...prev, status.progress!]);
        }
        
        if (status.status === 'completed') {
          setLogs(prev => [...prev, 'Optimization completed successfully!']);
          setIsRunning(false);
          return;
        } else if (status.status === 'failed') {
          setLogs(prev => [...prev, `Job failed: ${status.error || 'Unknown error'}`]);
          setIsRunning(false);
          return;
        }
        
        // Continue polling
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, pollInterval);
        } else {
          setLogs(prev => [...prev, 'Polling timeout - job may still be running']);
          setIsRunning(false);
        }
        
      } catch (error) {
        setLogs(prev => [...prev, `Polling error: ${error.message}`]);
        setIsRunning(false);
      }
    };
    
    poll();
  };
  
  const handleSaveToAttio = async () => {
    if (!jobStatus?.result) {
      alert('No results to save');
      return;
    }
    
    try {
      const response = await fetch(`${backendUrl}/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          record_id: recordId,
          quote_results: jobStatus.result,
          object_type: 'quote'
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setLogs([...logs, 'Quote saved to Attio successfully!']);
      alert('Quote saved to Attio!');
      
    } catch (error) {
      setLogs([...logs, `Save error: ${error.message}`]);
      alert(`Failed to save: ${error.message}`);
    }
  };
  
  return (
    <div style={{ padding: '20px', fontFamily: 'system-ui, sans-serif' }}>
      <h2>BNG Quote Optimizer</h2>
      <p style={{ color: '#666', fontSize: '14px' }}>
        Record ID: {recordId || 'Not available'}
      </p>
      
      {/* Location Section */}
      <div style={{ marginBottom: '20px', padding: '15px', background: '#f5f5f5', borderRadius: '8px' }}>
        <h3 style={{ marginTop: 0 }}>Location</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontSize: '14px' }}>
              Postcode
            </label>
            <input
              type="text"
              value={location.postcode || ''}
              onChange={(e) => setLocation({ ...location, postcode: e.target.value })}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
              placeholder="e.g., SW1A 1AA"
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontSize: '14px' }}>
              Address
            </label>
            <input
              type="text"
              value={location.address || ''}
              onChange={(e) => setLocation({ ...location, address: e.target.value })}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
              placeholder="e.g., 10 Downing Street, London"
            />
          </div>
        </div>
      </div>
      
      {/* Demand Section */}
      <div style={{ marginBottom: '20px' }}>
        <h3>Demand</h3>
        {demandRows.map((row, index) => (
          <div key={row.id} style={{ display: 'flex', gap: '10px', marginBottom: '10px', alignItems: 'flex-end' }}>
            <div style={{ flex: 2 }}>
              <label style={{ display: 'block', marginBottom: '5px', fontSize: '14px' }}>
                Habitat {index + 1}
              </label>
              <select
                value={row.habitat_name}
                onChange={(e) => updateDemandRow(row.id, 'habitat_name', e.target.value)}
                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
              >
                <option value="">Select habitat...</option>
                {habitatOptions.map(habitat => (
                  <option key={habitat} value={habitat}>{habitat}</option>
                ))}
              </select>
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', marginBottom: '5px', fontSize: '14px' }}>
                Units
              </label>
              <input
                type="number"
                value={row.units}
                onChange={(e) => updateDemandRow(row.id, 'units', parseFloat(e.target.value) || 0)}
                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                min="0"
                step="0.01"
              />
            </div>
            <button
              onClick={() => removeDemandRow(row.id)}
              disabled={demandRows.length === 1}
              style={{
                padding: '8px 12px',
                borderRadius: '4px',
                border: '1px solid #ddd',
                background: demandRows.length === 1 ? '#eee' : '#fff',
                cursor: demandRows.length === 1 ? 'not-allowed' : 'pointer'
              }}
            >
              Remove
            </button>
          </div>
        ))}
        <button
          onClick={addDemandRow}
          style={{
            padding: '8px 16px',
            borderRadius: '4px',
            border: '1px solid #4CAF50',
            background: '#fff',
            color: '#4CAF50',
            cursor: 'pointer',
            fontSize: '14px'
          }}
        >
          + Add Row
        </button>
      </div>
      
      {/* Action Buttons */}
      <div style={{ marginBottom: '20px' }}>
        <button
          onClick={handleRunQuote}
          disabled={isRunning}
          style={{
            padding: '12px 24px',
            borderRadius: '4px',
            border: 'none',
            background: isRunning ? '#ccc' : '#2196F3',
            color: 'white',
            cursor: isRunning ? 'not-allowed' : 'pointer',
            fontSize: '16px',
            fontWeight: 'bold',
            marginRight: '10px'
          }}
        >
          {isRunning ? 'Running...' : 'Run Quote'}
        </button>
        
        {jobStatus?.status === 'completed' && (
          <button
            onClick={handleSaveToAttio}
            style={{
              padding: '12px 24px',
              borderRadius: '4px',
              border: 'none',
              background: '#4CAF50',
              color: 'white',
              cursor: 'pointer',
              fontSize: '16px',
              fontWeight: 'bold'
            }}
          >
            Save to Attio
          </button>
        )}
      </div>
      
      {/* Progress Logs */}
      {logs.length > 0 && (
        <div style={{ marginBottom: '20px', padding: '15px', background: '#f5f5f5', borderRadius: '8px' }}>
          <h3 style={{ marginTop: 0 }}>Progress</h3>
          <div style={{
            maxHeight: '200px',
            overflowY: 'auto',
            fontFamily: 'monospace',
            fontSize: '12px',
            background: '#fff',
            padding: '10px',
            borderRadius: '4px'
          }}>
            {logs.map((log, index) => (
              <div key={index}>{log}</div>
            ))}
          </div>
        </div>
      )}
      
      {/* Results */}
      {jobStatus?.result && (
        <div style={{ marginTop: '20px', padding: '15px', background: '#e8f5e9', borderRadius: '8px' }}>
          <h3 style={{ marginTop: 0 }}>Results</h3>
          <div style={{ marginBottom: '10px' }}>
            <strong>Contract Size:</strong> {jobStatus.result.contract_size}
          </div>
          <div style={{ marginBottom: '10px' }}>
            <strong>Total Cost:</strong> £{jobStatus.result.total_cost?.toLocaleString()}
          </div>
          <div style={{ marginBottom: '10px' }}>
            <strong>Allocations:</strong> {jobStatus.result.allocations?.length || 0}
          </div>
          {jobStatus.result.allocations && jobStatus.result.allocations.length > 0 && (
            <details>
              <summary style={{ cursor: 'pointer', marginTop: '10px' }}>
                View Allocation Details
              </summary>
              <pre style={{
                marginTop: '10px',
                padding: '10px',
                background: '#fff',
                borderRadius: '4px',
                overflow: 'auto',
                fontSize: '12px'
              }}>
                {JSON.stringify(jobStatus.result.allocations, null, 2)}
              </pre>
            </details>
          )}
        </div>
      )}
      
      {/* Error Display */}
      {jobStatus?.status === 'failed' && (
        <div style={{ marginTop: '20px', padding: '15px', background: '#ffebee', borderRadius: '8px' }}>
          <h3 style={{ marginTop: 0, color: '#c62828' }}>Error</h3>
          <p>{jobStatus.error}</p>
        </div>
      )}
    </div>
  );
};

export default QuoteWidget;
