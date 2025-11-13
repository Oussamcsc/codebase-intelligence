import React, { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Download, Share2, Copy, Check } from 'lucide-react';

const AnalysisResults = ({ results, jobId }) => {
  const [expandedIssues, setExpandedIssues] = useState(new Set());
  const [selectedFile, setSelectedFile] = useState(0);
  const [copiedLink, setCopiedLink] = useState(false);

  if (!results) {
    return (
      <div style={styles.container}>
        <div style={styles.emptyState}>
          <h3 style={styles.emptyTitle}>No analysis results yet</h3>
          <p style={styles.emptyText}>Submit a repository URL to start analyzing</p>
        </div>
      </div>
    );
  }

  const fileReviews = results.results || [];
  const totalIssues = results.total_issues || 0;
  const filesAnalyzed = results.files_analyzed || fileReviews.length;

  if (fileReviews.length === 0) {
    return (
      <div style={styles.container}>
        <div style={styles.emptyState}>
          <h3 style={styles.emptyTitle}>No files analyzed</h3>
          <p style={styles.emptyText}>The repository analysis completed but no files were reviewed</p>
        </div>
      </div>
    );
  }

  const currentFileData = fileReviews[selectedFile];
  const currentReview = currentFileData?.review || {};

  const toggleIssue = (index) => {
    const newExpanded = new Set(expandedIssues);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedIssues(newExpanded);
  };

  // Export and Share functions
  const handleExportJSON = () => {
    window.open(`http://localhost:8000/github/export/${jobId}/json`, '_blank');
  };

  const handleCopyShareLink = async () => {
    const shareLink = `http://localhost:8000/github/share/${jobId}`;
    try {
      await navigator.clipboard.writeText(shareLink);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    } catch (err) {
      alert(`Share link: ${shareLink}`);
    }
  };

  const handleDownloadResults = () => {
    // Download as JSON file directly
    const dataStr = JSON.stringify(results, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `analysis-${jobId}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const getSeverityColor = (severity) => {
    const sev = (severity || '').toLowerCase();
    if (sev === 'critical') return '#ef4444';
    if (sev === 'warning') return '#f59e0b';
    return '#3b82f6';
  };

  const getSeverityBadgeStyle = (severity) => {
    const sev = (severity || '').toLowerCase();
    if (sev === 'critical') {
      return { background: '#2d1515', color: '#fca5a5', border: '1px solid #3d1f1f' };
    }
    if (sev === 'warning') {
      return { background: '#2d2415', color: '#fcd34d', border: '1px solid #3d331f' };
    }
    return { background: '#152d3d', color: '#93c5fd', border: '1px solid #1f3d52' };
  };

  const getQualityColor = (score) => {
    const numScore = parseInt(score);
    if (numScore >= 8) return '#10b981';
    if (numScore >= 6) return '#f59e0b';
    return '#ef4444';
  };

  // Aggregate stats
  const aggregateStats = {
    avgQuality: 0,
    totalCritical: 0,
    totalWarning: 0,
    totalSuggestion: 0,
    totalCorrectness: 0,
    totalStability: 0,
    totalPerformance: 0,
    totalMaintainability: 0
  };

  fileReviews.forEach(fr => {
    const review = fr.review || {};
    aggregateStats.avgQuality += parseInt(review.overall_quality) || 0;

    const findings = review.critical_findings || {};
    aggregateStats.totalCorrectness += findings.correctness_issues || 0;
    aggregateStats.totalStability += findings.stability_risks || 0;
    aggregateStats.totalPerformance += findings.performance_problems || 0;
    aggregateStats.totalMaintainability += findings.maintainability_debt || 0;

    (review.issues || []).forEach(issue => {
      const sev = (issue.severity || issue.issue_type || '').toLowerCase();
      if (sev === 'critical') aggregateStats.totalCritical++;
      else if (sev === 'warning') aggregateStats.totalWarning++;
      else aggregateStats.totalSuggestion++;
    });
  });

  aggregateStats.avgQuality = (aggregateStats.avgQuality / fileReviews.length).toFixed(1);

  const codePurpose = currentReview.code_purpose || currentReview.code_understanding;
  const qualityScore = currentReview.overall_quality;
  const qualitySummary = currentReview.quality_summary || currentReview.summary;
  const criticalFindings = currentReview.critical_findings;
  const issues = currentReview.issues || [];
  const strengths = currentReview.strengths || [];
  const architecturalRecs = currentReview.architectural_recommendations || [];
  const immediateActions = currentReview.immediate_actions || [];

  return (
    <div style={styles.container}>
      {/* Header with Export/Share buttons */}
      <div style={styles.header}>
        <h1 style={styles.headerTitle}>Repository Analysis</h1>
        <div style={styles.actionButtons}>
          <button style={styles.exportButton} onClick={handleDownloadResults}>
            <Download size={18} />
            <span>Download JSON</span>
          </button>
          <button style={styles.exportButton} onClick={handleExportJSON}>
            <Download size={18} />
            <span>Export from Server</span>
          </button>
          <button style={styles.shareButton} onClick={handleCopyShareLink}>
            {copiedLink ? <Check size={18} /> : <Copy size={18} />}
            <span>{copiedLink ? 'Link Copied!' : 'Copy Share Link'}</span>
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div style={styles.headerStats}>
        <div style={styles.statCard}>
          <div style={styles.statValue}>{filesAnalyzed}</div>
          <div style={styles.statLabel}>Files</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statValue}>{totalIssues}</div>
          <div style={styles.statLabel}>Issues</div>
        </div>
        <div style={styles.statCard}>
          <div style={{...styles.statValue, color: getQualityColor(aggregateStats.avgQuality)}}>
            {aggregateStats.avgQuality}
          </div>
          <div style={styles.statLabel}>Avg Quality</div>
        </div>
      </div>

      {/* Overview Cards */}
      <div style={styles.overviewGrid}>
        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <h3 style={styles.cardTitle}>Severity</h3>
          </div>
          <div style={styles.severityGrid}>
            <div style={styles.metricItem}>
              <div style={{...styles.metricValue, color: '#ef4444'}}>{aggregateStats.totalCritical}</div>
              <div style={styles.metricLabel}>Critical</div>
            </div>
            <div style={styles.metricItem}>
              <div style={{...styles.metricValue, color: '#f59e0b'}}>{aggregateStats.totalWarning}</div>
              <div style={styles.metricLabel}>Warnings</div>
            </div>
            <div style={styles.metricItem}>
              <div style={{...styles.metricValue, color: '#3b82f6'}}>{aggregateStats.totalSuggestion}</div>
              <div style={styles.metricLabel}>Suggestions</div>
            </div>
          </div>
        </div>

        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <h3 style={styles.cardTitle}>Categories</h3>
          </div>
          <div style={styles.categoryGrid}>
            <div style={styles.metricItem}>
              <div style={styles.metricValue}>{aggregateStats.totalCorrectness}</div>
              <div style={styles.metricLabel}>Correctness</div>
            </div>
            <div style={styles.metricItem}>
              <div style={styles.metricValue}>{aggregateStats.totalStability}</div>
              <div style={styles.metricLabel}>Stability</div>
            </div>
            <div style={styles.metricItem}>
              <div style={styles.metricValue}>{aggregateStats.totalPerformance}</div>
              <div style={styles.metricLabel}>Performance</div>
            </div>
            <div style={styles.metricItem}>
              <div style={styles.metricValue}>{aggregateStats.totalMaintainability}</div>
              <div style={styles.metricLabel}>Maintainability</div>
            </div>
          </div>
        </div>
      </div>

      {/* File Selector */}
      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>Files</h2>
        <div style={styles.fileGrid}>
          {fileReviews.map((fileData, idx) => {
            const fileIssues = fileData.review?.issues?.length || 0;
            const fileQuality = fileData.review?.overall_quality || 'N/A';
            const isActive = selectedFile === idx;

            return (
              <button
                key={idx}
                style={{
                  ...styles.fileCard,
                  ...(isActive ? styles.fileCardActive : {})
                }}
                onClick={() => {
                  setSelectedFile(idx);
                  setExpandedIssues(new Set());
                }}
              >
                <div style={styles.fileName}>{fileData.file_path}</div>
                <div style={styles.fileStats}>
                  <span style={styles.fileQuality}>Quality: {fileQuality}/10</span>
                  <span style={styles.fileSeparator}>•</span>
                  <span style={styles.fileIssues}>{fileIssues} issues</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Current File Header */}
      <div style={styles.currentFileHeader}>
        <h2 style={styles.currentFileTitle}>{currentFileData?.file_path}</h2>
      </div>

      {/* Code Understanding */}
      {codePurpose && (
        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <h3 style={styles.cardTitle}>Code Understanding</h3>
          </div>
          <div style={styles.cardContent}>
            <p style={styles.purposeText}>
              {codePurpose.summary || codePurpose.main_purpose}
            </p>
            {codePurpose.key_functionality && codePurpose.key_functionality.length > 0 && (
              <div style={styles.featureSection}>
                <h4 style={styles.featureTitle}>Key Functionality</h4>
                <ul style={styles.featureList}>
                  {codePurpose.key_functionality.map((feature, idx) => (
                    <li key={idx} style={styles.featureItem}>{feature}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Quality & Findings */}
      <div style={styles.overviewGrid}>
        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <h3 style={styles.cardTitle}>Quality Score</h3>
            <div
              style={{
                ...styles.qualityBadge,
                color: getQualityColor(qualityScore)
              }}
            >
              {qualityScore}/10
            </div>
          </div>
          {qualitySummary && (
            <div style={styles.cardContent}>
              <p style={styles.summaryText}>{qualitySummary}</p>
            </div>
          )}
        </div>

        {criticalFindings && (
          <div style={styles.card}>
            <div style={styles.cardHeader}>
              <h3 style={styles.cardTitle}>Critical Findings</h3>
            </div>
            <div style={styles.cardContent}>
              <div style={styles.findingsGrid}>
                <div style={styles.findingItem}>
                  <div style={styles.findingValue}>{criticalFindings.correctness_issues || 0}</div>
                  <div style={styles.findingLabel}>Correctness</div>
                </div>
                <div style={styles.findingItem}>
                  <div style={styles.findingValue}>{criticalFindings.stability_risks || 0}</div>
                  <div style={styles.findingLabel}>Stability</div>
                </div>
                <div style={styles.findingItem}>
                  <div style={styles.findingValue}>{criticalFindings.performance_problems || 0}</div>
                  <div style={styles.findingLabel}>Performance</div>
                </div>
                <div style={styles.findingItem}>
                  <div style={styles.findingValue}>{criticalFindings.maintainability_debt || 0}</div>
                  <div style={styles.findingLabel}>Maintainability</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Immediate Actions */}
      {immediateActions && immediateActions.length > 0 && (
        <div style={styles.alertCard}>
          <div style={styles.alertHeader}>
            <h3 style={styles.alertTitle}>Immediate Actions Required</h3>
          </div>
          <ul style={styles.alertList}>
            {immediateActions.map((action, idx) => (
              <li key={idx} style={styles.alertItem}>{action}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Issues */}
      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>Issues ({issues.length})</h2>

        {issues.length === 0 ? (
          <div style={styles.successCard}>
            <div style={styles.successText}>✓ No significant issues found</div>
          </div>
        ) : (
          <div style={styles.issueList}>
            {issues.map((issue, index) => {
              const isExpanded = expandedIssues.has(index);
              const severity = issue.severity || issue.issue_type || 'Suggestion';
              const badgeStyle = getSeverityBadgeStyle(severity);

              return (
                <div key={index} style={styles.issueCard}>
                  <div
                    style={styles.issueHeader}
                    onClick={() => toggleIssue(index)}
                  >
                    <div style={styles.issueHeaderLeft}>
                      <span style={{...styles.severityBadge, ...badgeStyle}}>
                        {severity}
                      </span>
                      <span style={styles.issueLocation}>
                        {issue.location || `Line ${issue.line || 'N/A'}`}
                      </span>
                    </div>
                    <span style={styles.expandIcon}>{isExpanded ? '−' : '+'}</span>
                  </div>

                  <div style={styles.issueTitle}>
                    {issue.bug_risk || issue.issue}
                  </div>

                  {issue.impact && (
                    <div style={styles.impactBadge}>
                      Impact: {issue.impact}
                    </div>
                  )}

                  {isExpanded && (
                    <div style={styles.issueBody}>
                      {issue.problematic_code && (
                        <div style={styles.codeSection}>
                          <div style={styles.codeSectionHeader}>
                            <span style={styles.codeLabel}>Problematic Code</span>
                          </div>
                          <SyntaxHighlighter
                            language="python"
                            style={vscDarkPlus}
                            customStyle={styles.codeBlock}
                          >
                            {issue.problematic_code}
                          </SyntaxHighlighter>
                        </div>
                      )}

                      {issue.fixed_code && (
                        <div style={styles.codeSection}>
                          <div style={styles.codeSectionHeader}>
                            <span style={styles.codeLabel}>Fixed Code</span>
                          </div>
                          <SyntaxHighlighter
                            language="python"
                            style={vscDarkPlus}
                            customStyle={styles.codeBlock}
                          >
                            {issue.fixed_code}
                          </SyntaxHighlighter>
                        </div>
                      )}

                      {issue.explanation && (
                        <div style={styles.explanationSection}>
                          <div style={styles.explanationLabel}>Why This Fix Works</div>
                          <p style={styles.explanationText}>{issue.explanation}</p>
                        </div>
                      )}

                      {!issue.explanation && issue.suggestion && (
                        <div style={styles.explanationSection}>
                          <div style={styles.explanationLabel}>Suggestion</div>
                          <p style={styles.explanationText}>{issue.suggestion}</p>
                        </div>
                      )}

                      {issue.refactor_suggestion && (
                        <div style={styles.explanationSection}>
                          <div style={styles.explanationLabel}>Refactor Suggestion</div>
                          <p style={styles.explanationText}>{issue.refactor_suggestion}</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Strengths */}
      {strengths && strengths.length > 0 && (
        <div style={styles.successCard}>
          <div style={styles.cardHeader}>
            <h3 style={styles.cardTitle}>Code Strengths</h3>
          </div>
          <ul style={styles.strengthList}>
            {strengths.map((strength, idx) => (
              <li key={idx} style={styles.strengthItem}>{strength}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Architecture */}
      {architecturalRecs && architecturalRecs.length > 0 && (
        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <h3 style={styles.cardTitle}>Architectural Recommendations</h3>
          </div>
          <ul style={styles.architectureList}>
            {architecturalRecs.map((rec, idx) => (
              <li key={idx} style={styles.architectureItem}>{rec}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

const styles = {
  container: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '32px 24px',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    backgroundColor: '#0a0a0a',
    minHeight: '100vh',
    color: '#e5e5e5',
  },

  // Header with action buttons
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
    flexWrap: 'wrap',
    gap: '16px',
  },
  headerTitle: {
    fontSize: '28px',
    fontWeight: '600',
    color: '#ffffff',
    margin: 0,
    letterSpacing: '-0.02em',
  },
  actionButtons: {
    display: 'flex',
    gap: '12px',
  },
  exportButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    background: '#1a1a1a',
    border: '1px solid #2a2a2a',
    borderRadius: '8px',
    padding: '10px 16px',
    color: '#e5e5e5',
    fontSize: '14px',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  shareButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    background: '#ffffff',
    border: 'none',
    borderRadius: '8px',
    padding: '10px 16px',
    color: '#0a0a0a',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },

  headerStats: {
    display: 'flex',
    gap: '12px',
    marginBottom: '32px',
  },
  statCard: {
    background: '#1a1a1a',
    border: '1px solid #2a2a2a',
    borderRadius: '8px',
    padding: '16px 24px',
    textAlign: 'center',
  },
  statValue: {
    fontSize: '24px',
    fontWeight: '600',
    color: '#ffffff',
    marginBottom: '4px',
  },
  statLabel: {
    fontSize: '13px',
    color: '#888888',
  },

  overviewGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
    gap: '16px',
    marginBottom: '32px',
  },

  card: {
    background: '#1a1a1a',
    border: '1px solid #2a2a2a',
    borderRadius: '8px',
    overflow: 'hidden',
  },
  cardHeader: {
    padding: '16px 20px',
    borderBottom: '1px solid #2a2a2a',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  cardTitle: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#ffffff',
    margin: 0,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  cardContent: {
    padding: '20px',
  },

  severityGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '1px',
    background: '#2a2a2a',
  },
  categoryGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '1px',
    background: '#2a2a2a',
  },
  metricItem: {
    padding: '20px',
    background: '#1a1a1a',
    textAlign: 'center',
  },
  metricValue: {
    fontSize: '28px',
    fontWeight: '700',
    color: '#ffffff',
    marginBottom: '4px',
  },
  metricLabel: {
    fontSize: '12px',
    color: '#888888',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },

  qualityBadge: {
    fontSize: '24px',
    fontWeight: '700',
  },
  summaryText: {
    fontSize: '14px',
    lineHeight: '1.6',
    color: '#b3b3b3',
    margin: 0,
  },

  findingsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '16px',
  },
  findingItem: {
    textAlign: 'center',
  },
  findingValue: {
    fontSize: '24px',
    fontWeight: '700',
    color: '#ffffff',
    marginBottom: '4px',
  },
  findingLabel: {
    fontSize: '12px',
    color: '#888888',
  },

  section: {
    marginBottom: '32px',
  },
  sectionTitle: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#ffffff',
    marginBottom: '16px',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },

  fileGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
    gap: '12px',
  },
  fileCard: {
    background: '#1a1a1a',
    border: '1px solid #2a2a2a',
    borderRadius: '8px',
    padding: '16px',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    textAlign: 'left',
  },
  fileCardActive: {
    background: '#2a2a2a',
    borderColor: '#3a3a3a',
  },
  fileName: {
    fontSize: '14px',
    fontWeight: '500',
    color: '#e5e5e5',
    marginBottom: '8px',
    wordBreak: 'break-all',
  },
  fileStats: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '13px',
    color: '#888888',
  },
  fileQuality: {},
  fileSeparator: {},
  fileIssues: {},

  currentFileHeader: {
    marginBottom: '24px',
  },
  currentFileTitle: {
    fontSize: '20px',
    fontWeight: '600',
    color: '#ffffff',
    margin: 0,
    fontFamily: 'monospace',
  },

  purposeText: {
    fontSize: '14px',
    lineHeight: '1.6',
    color: '#b3b3b3',
    margin: '0 0 16px 0',
  },
  featureSection: {
    marginTop: '16px',
    paddingTop: '16px',
    borderTop: '1px solid #2a2a2a',
  },
  featureTitle: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#888888',
    marginBottom: '8px',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  featureList: {
    margin: 0,
    paddingLeft: '20px',
  },
  featureItem: {
    fontSize: '14px',
    lineHeight: '1.6',
    color: '#b3b3b3',
    marginBottom: '4px',
  },

  alertCard: {
    background: '#2a1a1a',
    border: '1px solid #3a2a2a',
    borderRadius: '8px',
    padding: '20px',
    marginBottom: '32px',
  },
  alertHeader: {
    marginBottom: '12px',
  },
  alertTitle: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#ff6b6b',
    margin: 0,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  alertList: {
    margin: 0,
    paddingLeft: '20px',
  },
  alertItem: {
    fontSize: '14px',
    lineHeight: '1.6',
    color: '#ffb3b3',
    marginBottom: '8px',
  },

  successCard: {
    background: '#1a2a1a',
    border: '1px solid #2a3a2a',
    borderRadius: '8px',
    padding: '20px',
    marginBottom: '32px',
  },
  successText: {
    fontSize: '14px',
    color: '#7ed07e',
    textAlign: 'center',
    fontWeight: '500',
  },
  strengthList: {
    margin: '16px 0 0 0',
    paddingLeft: '20px',
  },
  strengthItem: {
    fontSize: '14px',
    lineHeight: '1.6',
    color: '#b3d9b3',
    marginBottom: '8px',
  },

  issueList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  issueCard: {
    background: '#1a1a1a',
    border: '1px solid #2a2a2a',
    borderRadius: '8px',
    padding: '16px',
    transition: 'border-color 0.15s ease',
  },
  issueHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px',
    cursor: 'pointer',
  },
  issueHeaderLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    flexWrap: 'wrap',
  },
  severityBadge: {
    padding: '4px 10px',
    borderRadius: '4px',
    fontSize: '12px',
    fontWeight: '500',
  },
  issueLocation: {
    fontSize: '13px',
    color: '#888888',
    fontFamily: 'monospace',
  },
  expandIcon: {
    fontSize: '18px',
    color: '#666666',
    fontWeight: '300',
  },
  issueTitle: {
    fontSize: '14px',
    lineHeight: '1.5',
    color: '#e5e5e5',
    marginBottom: '8px',
  },
  impactBadge: {
    display: 'inline-block',
    padding: '4px 10px',
    borderRadius: '4px',
    fontSize: '12px',
    background: '#2a1a1a',
    color: '#ff9999',
    border: '1px solid #3a2a2a',
  },
  issueBody: {
    marginTop: '16px',
    paddingTop: '16px',
    borderTop: '1px solid #2a2a2a',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },

  codeSection: {
    marginBottom: '12px',
  },
  codeSectionHeader: {
    marginBottom: '8px',
  },
  codeLabel: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#888888',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  codeBlock: {
    margin: 0,
    borderRadius: '6px',
    fontSize: '13px',
    border: '1px solid #2a2a2a',
  },

  explanationSection: {
    padding: '12px',
    background: '#1f1f1f',
    borderRadius: '6px',
    border: '1px solid #2a2a2a',
  },
  explanationLabel: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#888888',
    marginBottom: '8px',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  explanationText: {
    fontSize: '14px',
    lineHeight: '1.6',
    color: '#b3b3b3',
    margin: 0,
  },

  architectureList: {
    margin: '16px 0 0 0',
    paddingLeft: '20px',
  },
  architectureItem: {
    fontSize: '14px',
    lineHeight: '1.6',
    color: '#b3b3b3',
    marginBottom: '8px',
  },

  emptyState: {
    textAlign: 'center',
    padding: '80px 20px',
  },
  emptyTitle: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#ffffff',
    marginBottom: '8px',
  },
  emptyText: {
    fontSize: '14px',
    color: '#888888',
  },
};

export default AnalysisResults;