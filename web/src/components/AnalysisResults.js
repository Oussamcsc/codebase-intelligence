import React, { useState } from 'react';
import { 
  ArrowLeft, 
  RotateCcw, 
  Download, 
  FileText, 
  AlertTriangle, 
  CheckCircle,
  XCircle,
  Info,
  ChevronDown,
  ChevronRight,
  Github,
  Bug,
  Zap,
  Shield,
  Code2
} from 'lucide-react';

const AnalysisResults = ({ results, onBack, onNewAnalysis }) => {
  const [selectedFile, setSelectedFile] = useState(null);

  if (!results || !results.results || results.results.length === 0) {
    return (
      <div className="container">
        <div className="card">
          <div className="card-content" style={{ textAlign: 'center', padding: '3rem' }}>
            <FileText size={48} style={{ marginBottom: '1rem', color: '#6b7280' }} />
            <h3 style={{ marginBottom: '0.5rem' }}>No Results Available</h3>
            <p style={{ color: 'rgba(255, 255, 255, 0.7)' }}>
              The analysis didn't return any results.
            </p>
            <button 
              className="btn-primary" 
              onClick={onNewAnalysis}
              style={{ marginTop: '1rem' }}
            >
              Start New Analysis
            </button>
          </div>
        </div>
      </div>
    );
  }

  const getSeverityIcon = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'critical':
        return <XCircle size={16} style={{ color: '#ef4444' }} />;
      case 'warning':
        return <AlertTriangle size={16} style={{ color: '#f59e0b' }} />;
      case 'suggestion':
        return <Info size={16} style={{ color: '#3b82f6' }} />;
      default:
        return <AlertTriangle size={16} style={{ color: '#f59e0b' }} />;
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'critical': return '#ef4444';
      case 'warning': return '#f59e0b';
      case 'suggestion': return '#3b82f6';
      default: return '#f59e0b';
    }
  };

  const getCategoryIcon = (category) => {
    switch (category?.toLowerCase()) {
      case 'security':
        return <Shield size={16} style={{ color: '#ef4444' }} />;
      case 'performance':
        return <Zap size={16} style={{ color: '#f59e0b' }} />;
      case 'bugs':
      case 'correctness':
        return <Bug size={16} style={{ color: '#ef4444' }} />;
      case 'style':
      case 'typing':
        return <Code2 size={16} style={{ color: '#3b82f6' }} />;
      default:
        return <FileText size={16} style={{ color: '#6b7280' }} />;
    }
  };

  const exportResults = () => {
    const dataStr = JSON.stringify(results, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `code-review-${new Date().toISOString().split('T')[0]}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  const totalIssues = results.results.reduce((sum, file) => 
    sum + (file.review.issues ? file.review.issues.length : 0), 0
  );

  const filesSummary = results.results.map(file => ({
    ...file,
    issueCount: file.review.issues ? file.review.issues.length : 0,
    qualityScore: file.review.overall_quality || 'N/A'
  })).sort((a, b) => b.issueCount - a.issueCount);

  return (
    <div className="container">
      {/* Header */}
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
            <CheckCircle size={24} style={{ color: '#10b981' }} />
            <h2 className="card-title">Analysis Results</h2>
          </div>
          
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button className="btn-secondary" onClick={exportResults}>
              <Download size={16} />
              Export
            </button>
            <button className="btn-primary" onClick={onNewAnalysis}>
              <RotateCcw size={16} />
              New Analysis
            </button>
          </div>
        </div>

        <div className="card-content">
          {/* Summary Stats */}
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '1rem',
            marginBottom: '2rem'
          }}>
            <div style={{
              background: 'rgba(100, 255, 218, 0.1)',
              borderRadius: '8px',
              padding: '1rem',
              textAlign: 'center',
              border: '1px solid rgba(100, 255, 218, 0.2)'
            }}>
              <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#64ffda', marginBottom: '0.25rem' }}>
                {results.files_analyzed}
              </div>
              <div style={{ fontSize: '0.875rem', color: 'rgba(255, 255, 255, 0.8)' }}>
                Files Analyzed
              </div>
            </div>

            <div style={{
              background: 'rgba(239, 68, 68, 0.1)',
              borderRadius: '8px',
              padding: '1rem',
              textAlign: 'center',
              border: '1px solid rgba(239, 68, 68, 0.2)'
            }}>
              <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#ef4444', marginBottom: '0.25rem' }}>
                {totalIssues}
              </div>
              <div style={{ fontSize: '0.875rem', color: 'rgba(255, 255, 255, 0.8)' }}>
                Total Issues
              </div>
            </div>

            <div style={{
              background: 'rgba(102, 126, 234, 0.1)',
              borderRadius: '8px',
              padding: '1rem',
              textAlign: 'center',
              border: '1px solid rgba(102, 126, 234, 0.2)'
            }}>
              <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#667eea', marginBottom: '0.25rem' }}>
                {results.branch}
              </div>
              <div style={{ fontSize: '0.875rem', color: 'rgba(255, 255, 255, 0.8)' }}>
                Branch
              </div>
            </div>
          </div>

          {/* Repository Info */}
          <div style={{
            background: 'rgba(255, 255, 255, 0.05)',
            borderRadius: '8px',
            padding: '1rem',
            marginBottom: '2rem',
            border: '1px solid rgba(255, 255, 255, 0.1)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <Github size={16} />
              <strong>Repository:</strong>
            </div>
            <a 
              href={results.repository} 
              target="_blank" 
              rel="noopener noreferrer"
              style={{ 
                color: '#64ffda', 
                textDecoration: 'none',
                fontSize: '0.9rem',
                fontFamily: 'monospace'
              }}
            >
              {results.repository}
            </a>
          </div>
        </div>
      </div>

      {/* Files List */}
      <div className="card">
        <div className="card-header">
          <h3>Files Overview</h3>
        </div>
        <div className="card-content">
          <div style={{ display: 'grid', gap: '0.5rem' }}>
            {filesSummary.map((file, index) => (
              <div
                key={index}
                onClick={() => setSelectedFile(selectedFile === index ? null : index)}
                style={{
                  background: selectedFile === index 
                    ? 'rgba(102, 126, 234, 0.1)' 
                    : 'rgba(255, 255, 255, 0.05)',
                  border: selectedFile === index 
                    ? '1px solid rgba(102, 126, 234, 0.3)' 
                    : '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                  padding: '1rem',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease'
                }}
              >
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between',
                  marginBottom: selectedFile === index ? '1rem' : '0'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    {selectedFile === index ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    <code style={{ 
                      fontSize: '0.9rem',
                      background: 'rgba(255, 255, 255, 0.1)',
                      padding: '0.25rem 0.5rem',
                      borderRadius: '4px'
                    }}>
                      {file.file_path}
                    </code>
                  </div>
                  
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <span style={{ 
                      fontSize: '0.875rem',
                      color: file.issueCount > 0 ? '#ef4444' : '#10b981'
                    }}>
                      {file.issueCount} issues
                    </span>
                    <span style={{ 
                      fontSize: '0.875rem',
                      color: 'rgba(255, 255, 255, 0.7)'
                    }}>
                      Quality: {file.qualityScore}/10
                    </span>
                  </div>
                </div>

                {selectedFile === index && file.review.issues && (
                  <div style={{ paddingLeft: '1.5rem' }}>
                    {file.review.issues.map((issue, issueIndex) => (
                      <div
                        key={issueIndex}
                        style={{
                          background: 'rgba(255, 255, 255, 0.05)',
                          borderRadius: '6px',
                          padding: '0.75rem',
                          marginBottom: '0.5rem',
                          border: `1px solid ${getSeverityColor(issue.severity)}40`
                        }}
                      >
                        <div style={{ 
                          display: 'flex', 
                          alignItems: 'flex-start', 
                          gap: '0.5rem',
                          marginBottom: '0.5rem'
                        }}>
                          {getSeverityIcon(issue.severity)}
                          <div style={{ flex: 1 }}>
                            <div style={{ 
                              display: 'flex', 
                              alignItems: 'center', 
                              gap: '0.5rem',
                              marginBottom: '0.25rem'
                            }}>
                              {getCategoryIcon(issue.category)}
                              <span style={{ 
                                fontSize: '0.875rem',
                                fontWeight: '500',
                                color: getSeverityColor(issue.severity)
                              }}>
                                {issue.severity?.toUpperCase()} - {issue.category}
                              </span>
                              {issue.line && (
                                <span style={{ 
                                  fontSize: '0.75rem',
                                  color: 'rgba(255, 255, 255, 0.6)',
                                  background: 'rgba(255, 255, 255, 0.1)',
                                  padding: '0.125rem 0.375rem',
                                  borderRadius: '3px'
                                }}>
                                  Line {issue.line}
                                </span>
                              )}
                            </div>
                            <p style={{ 
                              fontSize: '0.875rem',
                              marginBottom: '0.5rem',
                              lineHeight: '1.4'
                            }}>
                              {issue.issue}
                            </p>
                            {issue.suggestion && (
                              <div style={{
                                background: 'rgba(100, 255, 218, 0.1)',
                                borderRadius: '4px',
                                padding: '0.5rem',
                                fontSize: '0.8rem',
                                color: '#64ffda',
                                border: '1px solid rgba(100, 255, 218, 0.2)'
                              }}>
                                <strong>Suggestion:</strong> {issue.suggestion}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}

                    {/* Show summary and recommendations if available */}
                    {file.review.summary && (
                      <div style={{
                        background: 'rgba(102, 126, 234, 0.1)',
                        borderRadius: '6px',
                        padding: '0.75rem',
                        marginTop: '1rem',
                        border: '1px solid rgba(102, 126, 234, 0.2)'
                      }}>
                        <strong>Summary:</strong>
                        <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
                          {file.review.summary}
                        </p>
                      </div>
                    )}

                    {file.review.strengths && file.review.strengths.length > 0 && (
                      <div style={{
                        background: 'rgba(16, 185, 129, 0.1)',
                        borderRadius: '6px',
                        padding: '0.75rem',
                        marginTop: '0.5rem',
                        border: '1px solid rgba(16, 185, 129, 0.2)'
                      }}>
                        <strong style={{ color: '#10b981' }}>Strengths:</strong>
                        <ul style={{ fontSize: '0.875rem', marginTop: '0.5rem', paddingLeft: '1rem' }}>
                          {file.review.strengths.map((strength, i) => (
                            <li key={i}>{strength}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {file.review.recommendations && file.review.recommendations.length > 0 && (
                      <div style={{
                        background: 'rgba(168, 85, 247, 0.1)',
                        borderRadius: '6px',
                        padding: '0.75rem',
                        marginTop: '0.5rem',
                        border: '1px solid rgba(168, 85, 247, 0.2)'
                      }}>
                        <strong style={{ color: '#a855f7' }}>Recommendations:</strong>
                        <ul style={{ fontSize: '0.875rem', marginTop: '0.5rem', paddingLeft: '1rem' }}>
                          {file.review.recommendations.map((rec, i) => (
                            <li key={i}>{rec}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalysisResults;