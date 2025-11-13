import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { ArrowLeft, CheckCircle, XCircle, Clock, FileText, Zap } from 'lucide-react';

const ProgressTracker = ({ jobId, onComplete, onBack }) => {
  console.log('🚀 ProgressTracker MOUNTED');
  console.log('🆔 jobId prop:', jobId);

  const [status, setStatus] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    console.log('🔄 useEffect triggered - jobId:', jobId);

    if (!jobId) {
      console.error('❌ NO JOB ID PROVIDED!');
      setError('No job ID provided');
      return;
    }

    let isCancelled = false;
    let pollInterval = null;

    const pollStatus = async () => {
      if (isCancelled) {
        console.log('⏹️ Polling cancelled');
        return;
      }

      try {
        console.log(`📡 Polling status for job: ${jobId}`);

        const response = await axios.get(`/github/status/${jobId}`, {
          timeout: 10000
        });

        const jobStatus = response.data;
        console.log('📊 Status update:', jobStatus);

        if (isCancelled) return;

        setStatus(jobStatus);

        if (jobStatus.status === 'completed') {
          console.log('🎉 JOB COMPLETED!');

          if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
          }

          try {
            console.log(`📥 Fetching results...`);
            const resultsResponse = await axios.get(`/github/results/${jobId}`);
            console.log('✅ GOT RESULTS:', resultsResponse.data);

            if (!isCancelled) {
              const results = resultsResponse.data.results;
              console.log('🎯 Calling onComplete');
              onComplete(results);
            }
          } catch (error) {
            console.error('❌ Failed to fetch results:', error);
            if (!isCancelled) {
              setError(`Failed to fetch results: ${error.message}`);
            }
          }
        } else if (jobStatus.status === 'failed') {
          console.error('❌ JOB FAILED');
          if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
          }
          if (!isCancelled) {
            setError(`Analysis failed: ${jobStatus.current_task || 'Unknown error'}`);
          }
        }
      } catch (error) {
        console.error('❌ Polling error:', error);

        if (isCancelled) return;

        if (error.code === 'ECONNABORTED') {
          console.log('⏰ Request timeout, will retry...');
        } else if (error.response?.status === 404) {
          if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
          }
          setError('Job not found. Server may have restarted.');
        } else {
          console.log('⚠️ Polling error, will retry:', error.message);
        }
      }
    };

    // Start polling
    console.log('▶️ Starting polling interval');
    pollStatus(); // Poll immediately
    pollInterval = setInterval(pollStatus, 2000);

    // Cleanup
    return () => {
      console.log('🧹 Cleanup - stopping polling');
      isCancelled = true;
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [jobId, onComplete]);

  const getStatusIcon = () => {
    if (!status) return <Clock className="animate-spin" size={20} />;

    switch (status.status) {
      case 'completed':
        return <CheckCircle size={20} style={{ color: '#10b981' }} />;
      case 'failed':
        return <XCircle size={20} style={{ color: '#ef4444' }} />;
      case 'running':
        return <Zap className="animate-pulse" size={20} style={{ color: '#f59e0b' }} />;
      default:
        return <Clock className="animate-spin" size={20} />;
    }
  };

  const getStatusColor = () => {
    if (!status) return '#6b7280';

    switch (status.status) {
      case 'completed': return '#10b981';
      case 'failed': return '#ef4444';
      case 'running': return '#f59e0b';
      default: return '#6b7280';
    }
  };

  return (
    <div className="container">
      <div className="card">
        <div className="card-header">
          <button
            className="btn-secondary"
            onClick={onBack}
            style={{
              background: 'none',
              border: 'none',
              color: 'white',
              cursor: 'pointer',
              padding: '0.5rem',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}
          >
            <ArrowLeft size={20} />
            Back
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            {getStatusIcon()}
            <h2 className="card-title">Analysis Progress</h2>
          </div>
        </div>

        <div className="card-content">
          {error ? (
            <div style={{
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.2)',
              borderRadius: '8px',
              padding: '2rem',
              textAlign: 'center',
              color: '#fca5a5'
            }}>
              <XCircle size={48} style={{ margin: '0 auto 1rem' }} />
              <h3 style={{ marginBottom: '0.5rem' }}>Analysis Failed</h3>
              <p>{error}</p>
              <button
                onClick={() => window.location.reload()}
                style={{
                  marginTop: '1rem',
                  padding: '0.75rem 1.5rem',
                  background: '#ef4444',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '0.9rem'
                }}
              >
                Refresh & Try Again
              </button>
            </div>
          ) : !status ? (
            <div style={{ textAlign: 'center', padding: '2rem' }}>
              <div className="loading-spinner" style={{
                width: '40px',
                height: '40px',
                margin: '0 auto 1rem'
              }} />
              <p>Connecting to analysis service...</p>
              <p style={{ fontSize: '0.875rem', color: 'rgba(255, 255, 255, 0.7)', marginTop: '0.5rem' }}>
                Job ID: {jobId}
              </p>
            </div>
          ) : (
            <div>
              {/* Progress Bar */}
              <div style={{ marginBottom: '2rem' }}>
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '0.5rem'
                }}>
                  <span style={{ fontWeight: '500' }}>
                    Progress: {status.progress}%
                  </span>
                  <span style={{
                    fontSize: '0.875rem',
                    color: 'rgba(255, 255, 255, 0.7)'
                  }}>
                    {status.status === 'completed' ? 'Completed' :
                     status.status === 'failed' ? 'Failed' :
                     status.status === 'running' ? 'Running' : 'Pending'}
                  </span>
                </div>

                <div style={{
                  width: '100%',
                  height: '10px',
                  background: 'rgba(255, 255, 255, 0.1)',
                  borderRadius: '5px',
                  overflow: 'hidden'
                }}>
                  <div
                    style={{
                      width: `${status.progress}%`,
                      height: '100%',
                      background: `linear-gradient(90deg, ${getStatusColor()}, ${getStatusColor()}dd)`,
                      borderRadius: '5px',
                      transition: 'width 0.5s ease'
                    }}
                  />
                </div>
              </div>

              {/* Current Task */}
              <div style={{
                background: 'rgba(255, 255, 255, 0.05)',
                borderRadius: '8px',
                padding: '1.5rem',
                marginBottom: '2rem',
                border: '1px solid rgba(255, 255, 255, 0.1)'
              }}>
                <h3 style={{
                  fontSize: '1.1rem',
                  marginBottom: '0.5rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}>
                  <FileText size={18} />
                  Current Task
                </h3>
                <p style={{
                  fontSize: '0.95rem',
                  color: 'rgba(255, 255, 255, 0.9)',
                  fontFamily: 'monospace'
                }}>
                  {status.current_task}
                </p>
              </div>

              {/* Statistics */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '1rem'
              }}>
                <div style={{
                  background: 'rgba(100, 255, 218, 0.1)',
                  borderRadius: '8px',
                  padding: '1rem',
                  textAlign: 'center',
                  border: '1px solid rgba(100, 255, 218, 0.2)'
                }}>
                  <div style={{
                    fontSize: '1.5rem',
                    fontWeight: '700',
                    color: '#64ffda',
                    marginBottom: '0.25rem'
                  }}>
                    {status.files_analyzed}
                  </div>
                  <div style={{
                    fontSize: '0.875rem',
                    color: 'rgba(255, 255, 255, 0.8)'
                  }}>
                    Files Analyzed
                  </div>
                </div>

                <div style={{
                  background: 'rgba(102, 126, 234, 0.1)',
                  borderRadius: '8px',
                  padding: '1rem',
                  textAlign: 'center',
                  border: '1px solid rgba(102, 126, 234, 0.2)'
                }}>
                  <div style={{
                    fontSize: '1.5rem',
                    fontWeight: '700',
                    color: '#667eea',
                    marginBottom: '0.25rem'
                  }}>
                    {status.total_files}
                  </div>
                  <div style={{
                    fontSize: '0.875rem',
                    color: 'rgba(255, 255, 255, 0.8)'
                  }}>
                    Total Files
                  </div>
                </div>

                <div style={{
                  background: 'rgba(168, 85, 247, 0.1)',
                  borderRadius: '8px',
                  padding: '1rem',
                  textAlign: 'center',
                  border: '1px solid rgba(168, 85, 247, 0.2)'
                }}>
                  <div style={{
                    fontSize: '1.5rem',
                    fontWeight: '700',
                    color: '#a855f7',
                    marginBottom: '0.25rem'
                  }}>
                    {status.total_files > 0
                      ? Math.round((status.files_analyzed / status.total_files) * 100)
                      : 0}%
                  </div>
                  <div style={{
                    fontSize: '0.875rem',
                    color: 'rgba(255, 255, 255, 0.8)'
                  }}>
                    Complete
                  </div>
                </div>
              </div>

              {/* Job Info */}
              <div style={{
                marginTop: '2rem',
                padding: '1rem',
                background: 'rgba(255, 255, 255, 0.05)',
                borderRadius: '8px',
                border: '1px solid rgba(255, 255, 255, 0.1)'
              }}>
                <p style={{
                  fontSize: '0.875rem',
                  color: 'rgba(255, 255, 255, 0.7)',
                  lineHeight: '1.4'
                }}>
                  Real-time updates every 2 seconds. Job ID: <code style={{
                    background: 'rgba(255, 255, 255, 0.1)',
                    padding: '0.125rem 0.375rem',
                    borderRadius: '3px',
                    fontSize: '0.8rem'
                  }}>
                    {jobId}
                  </code>
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProgressTracker;