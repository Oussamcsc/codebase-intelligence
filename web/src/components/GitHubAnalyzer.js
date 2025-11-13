import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Github, ArrowLeft, Play, AlertCircle, LogOut, RefreshCw } from 'lucide-react';

const GitHubAnalyzer = ({ onAnalysisStart, onBack, githubUser, onLogout }) => {
  const [analysisMode, setAnalysisMode] = useState('url'); // 'url' or 'oauth'
  const [formData, setFormData] = useState({
    repo_url: '',
    branch: 'main',
    files_pattern: '*.py'
  });
  const [repos, setRepos] = useState([]);
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isFetchingRepos, setIsFetchingRepos] = useState(false);
  const [error, setError] = useState('');

  // Fetch repos if user is authenticated
  useEffect(() => {
    if (githubUser && analysisMode === 'oauth') {
      fetchUserRepos();
    }
  }, [githubUser, analysisMode]);

  const fetchUserRepos = async () => {
    console.log('📦 Fetching user repos...');
    setIsFetchingRepos(true);
    setError('');

    try {
      const token = localStorage.getItem('github_token');
      const response = await axios.get('/github/repos', {
        params: { access_token: token, page: 1 }
      });

      console.log('✅ Repos fetched:', response.data);
      setRepos(response.data.repos);
    } catch (err) {
      console.error('❌ Error fetching repos:', err);
      setError(err.response?.data?.detail || 'Failed to fetch repositories');
    } finally {
      setIsFetchingRepos(false);
    }
  };

  const startOAuth = async () => {
    console.log('🚀 Starting GitHub OAuth...');

    try {
      const response = await axios.get('/auth/github');
      const { oauth_url } = response.data;

      console.log('📍 Redirecting to:', oauth_url);
      window.location.href = oauth_url;
    } catch (err) {
      console.error('❌ OAuth init error:', err);
      setError('Failed to start GitHub authentication');
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const validateGitHubUrl = (url) => {
    const githubRegex = /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+(?:\.git)?(?:\/)?$/;
    return githubRegex.test(url);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    let repoUrl;
    let branch;

    if (analysisMode === 'oauth' && selectedRepo) {
      // Using OAuth - analyze selected repo
      repoUrl = selectedRepo.clone_url;
      branch = selectedRepo.default_branch;
    } else if (analysisMode === 'url') {
      // Using manual URL
      if (!formData.repo_url.trim()) {
        setError('Please enter a GitHub repository URL');
        return;
      }

      if (!validateGitHubUrl(formData.repo_url)) {
        setError('Please enter a valid GitHub repository URL (e.g., https://github.com/user/repo)');
        return;
      }

      repoUrl = formData.repo_url.trim();
      branch = formData.branch.trim() || 'main';
    } else {
      setError('Please select a repository');
      return;
    }

    console.log('🚀 Starting analysis...');
    console.log('📦 Repo URL:', repoUrl);
    console.log('🌿 Branch:', branch);

    setIsLoading(true);

    try {
      const response = await axios.post('/github/analyze', {
        repo_url: repoUrl,
        branch: branch,
        files_pattern: formData.files_pattern.trim() || '*.py'
      });

      console.log('✅ Analysis started:', response.data);
      onAnalysisStart(response.data);

    } catch (error) {
      console.error('❌ Analysis error:', error);
      if (error.response?.data?.detail) {
        setError(error.response.data.detail);
      } else {
        setError('Failed to start analysis. Please check your repository URL and try again.');
      }
    } finally {
      setIsLoading(false);
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
            <Github size={24} />
            <h2 className="card-title">Analyze GitHub Repository</h2>
          </div>
          {githubUser && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <img
                src={githubUser.avatar_url}
                alt="avatar"
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  border: '2px solid #64ffda'
                }}
              />
              <span style={{ fontSize: '0.875rem' }}>{githubUser.username}</span>
              <button
                onClick={onLogout}
                style={{
                  background: 'none',
                  border: '1px solid rgba(255,255,255,0.2)',
                  color: 'white',
                  cursor: 'pointer',
                  padding: '0.25rem 0.5rem',
                  borderRadius: '4px',
                  fontSize: '0.75rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.25rem'
                }}
              >
                <LogOut size={12} />
                Logout
              </button>
            </div>
          )}
        </div>

        <div className="card-content">
          {/* Mode Selection */}
          <div style={{ marginBottom: '2rem' }}>
            <div style={{
              display: 'flex',
              gap: '1rem',
              background: 'rgba(255,255,255,0.05)',
              padding: '0.5rem',
              borderRadius: '8px'
            }}>
              <button
                onClick={() => setAnalysisMode('url')}
                style={{
                  flex: 1,
                  padding: '0.75rem',
                  background: analysisMode === 'url' ? '#667eea' : 'transparent',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  fontWeight: analysisMode === 'url' ? '600' : '400'
                }}
              >
                📝 Paste URL
              </button>
              <button
                onClick={() => setAnalysisMode('oauth')}
                style={{
                  flex: 1,
                  padding: '0.75rem',
                  background: analysisMode === 'oauth' ? '#667eea' : 'transparent',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  fontWeight: analysisMode === 'oauth' ? '600' : '400'
                }}
              >
                🔗 Connect GitHub
              </button>
            </div>
          </div>

          {/* URL Mode */}
          {analysisMode === 'url' && (
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label className="form-label">Repository URL *</label>
                <input
                  type="url"
                  name="repo_url"
                  value={formData.repo_url}
                  onChange={handleInputChange}
                  className="form-input"
                  placeholder="https://github.com/username/repository"
                  disabled={isLoading}
                />
                <small style={{ color: 'rgba(255, 255, 255, 0.7)', fontSize: '0.875rem' }}>
                  Enter the full GitHub repository URL
                </small>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Branch</label>
                  <input
                    type="text"
                    name="branch"
                    value={formData.branch}
                    onChange={handleInputChange}
                    className="form-input"
                    placeholder="main"
                    disabled={isLoading}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">File Pattern</label>
                  <input
                    type="text"
                    name="files_pattern"
                    value={formData.files_pattern}
                    onChange={handleInputChange}
                    className="form-input"
                    placeholder="*.py"
                    disabled={isLoading}
                  />
                </div>
              </div>

              {error && (
                <div style={{
                  background: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.2)',
                  borderRadius: '8px',
                  padding: '1rem',
                  marginBottom: '1rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  color: '#fca5a5'
                }}>
                  <AlertCircle size={20} />
                  {error}
                </div>
              )}

              <button
                type="submit"
                className="btn-primary"
                disabled={isLoading}
                style={{
                  width: '100%',
                  justifyContent: 'center',
                  opacity: isLoading ? 0.7 : 1,
                  cursor: isLoading ? 'not-allowed' : 'pointer'
                }}
              >
                {isLoading ? (
                  <>
                    <div className="loading-spinner" />
                    Starting Analysis...
                  </>
                ) : (
                  <>
                    <Play size={20} />
                    Start Analysis
                  </>
                )}
              </button>
            </form>
          )}

          {/* OAuth Mode */}
          {analysisMode === 'oauth' && (
            <div>
              {!githubUser ? (
                <div style={{ textAlign: 'center', padding: '3rem 1rem' }}>
                  <Github size={64} style={{ marginBottom: '1rem', opacity: 0.5 }} />
                  <h3 style={{ marginBottom: '1rem' }}>Connect Your GitHub Account</h3>
                  <p style={{
                    color: 'rgba(255,255,255,0.7)',
                    marginBottom: '2rem',
                    maxWidth: '500px',
                    margin: '0 auto 2rem'
                  }}>
                    Authenticate with GitHub to select repositories from your account
                  </p>
                  <button
                    onClick={startOAuth}
                    className="btn-primary"
                    style={{ display: 'inline-flex' }}
                  >
                    <Github size={20} />
                    Connect GitHub Account
                  </button>
                </div>
              ) : (
                <div>
                  {/* Repository Selector */}
                  <div style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h3 style={{ fontSize: '1.1rem' }}>
                      Select Repository ({repos.length})
                    </h3>
                    <button
                      onClick={fetchUserRepos}
                      disabled={isFetchingRepos}
                      style={{
                        background: 'none',
                        border: '1px solid rgba(255,255,255,0.2)',
                        color: 'white',
                        cursor: isFetchingRepos ? 'not-allowed' : 'pointer',
                        padding: '0.5rem 1rem',
                        borderRadius: '6px',
                        fontSize: '0.875rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem'
                      }}
                    >
                      <RefreshCw size={14} className={isFetchingRepos ? 'spin' : ''} />
                      Refresh
                    </button>
                  </div>

                  {isFetchingRepos ? (
                    <div style={{ textAlign: 'center', padding: '2rem' }}>
                      <div className="loading-spinner" style={{ margin: '0 auto' }} />
                      <p style={{ marginTop: '1rem' }}>Loading repositories...</p>
                    </div>
                  ) : (
                    <>
                      <div style={{
                        maxHeight: '400px',
                        overflowY: 'auto',
                        marginBottom: '1rem',
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: '8px'
                      }}>
                        {repos.map(repo => (
                          <div
                            key={repo.id}
                            onClick={() => setSelectedRepo(repo)}
                            style={{
                              padding: '1rem',
                              cursor: 'pointer',
                              background: selectedRepo?.id === repo.id
                                ? 'rgba(102, 126, 234, 0.2)'
                                : 'transparent',
                              borderBottom: '1px solid rgba(255,255,255,0.05)',
                              transition: 'all 0.2s'
                            }}
                            onMouseEnter={(e) => {
                              if (selectedRepo?.id !== repo.id) {
                                e.target.style.background = 'rgba(255,255,255,0.05)';
                              }
                            }}
                            onMouseLeave={(e) => {
                              if (selectedRepo?.id !== repo.id) {
                                e.target.style.background = 'transparent';
                              }
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                              <input
                                type="radio"
                                checked={selectedRepo?.id === repo.id}
                                onChange={() => {}}
                                style={{ cursor: 'pointer' }}
                              />
                              <strong style={{ fontSize: '0.95rem' }}>{repo.name}</strong>
                              {repo.language && (
                                <span style={{
                                  fontSize: '0.75rem',
                                  background: 'rgba(100,255,218,0.2)',
                                  padding: '0.125rem 0.5rem',
                                  borderRadius: '12px',
                                  color: '#64ffda'
                                }}>
                                  {repo.language}
                                </span>
                              )}
                            </div>
                            {repo.description && (
                              <p style={{
                                fontSize: '0.8rem',
                                color: 'rgba(255,255,255,0.6)',
                                margin: '0.25rem 0 0 1.5rem'
                              }}>
                                {repo.description}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>

                      {error && (
                        <div style={{
                          background: 'rgba(239, 68, 68, 0.1)',
                          border: '1px solid rgba(239, 68, 68, 0.2)',
                          borderRadius: '8px',
                          padding: '1rem',
                          marginBottom: '1rem',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.5rem',
                          color: '#fca5a5'
                        }}>
                          <AlertCircle size={20} />
                          {error}
                        </div>
                      )}

                      <button
                        onClick={handleSubmit}
                        className="btn-primary"
                        disabled={!selectedRepo || isLoading}
                        style={{
                          width: '100%',
                          justifyContent: 'center',
                          opacity: !selectedRepo || isLoading ? 0.5 : 1,
                          cursor: !selectedRepo || isLoading ? 'not-allowed' : 'pointer'
                        }}
                      >
                        {isLoading ? (
                          <>
                            <div className="loading-spinner" />
                            Starting Analysis...
                          </>
                        ) : (
                          <>
                            <Play size={20} />
                            Analyze Selected Repository
                          </>
                        )}
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default GitHubAnalyzer;