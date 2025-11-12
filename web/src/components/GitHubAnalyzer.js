import React, { useState } from 'react';
import axios from 'axios';
import { Github, ArrowLeft, Play, AlertCircle } from 'lucide-react';

const GitHubAnalyzer = ({ onAnalysisStart, onBack }) => {
  const [formData, setFormData] = useState({
    repo_url: '',
    branch: 'main',
    files_pattern: '*.py'
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

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

    console.log('🚀 STARTING GITHUB ANALYSIS');
    console.log('📦 Form data:', formData);

    if (!formData.repo_url.trim()) {
      setError('Please enter a GitHub repository URL');
      return;
    }

    if (!validateGitHubUrl(formData.repo_url)) {
      setError('Please enter a valid GitHub repository URL (e.g., https://github.com/user/repo)');
      return;
    }

    setIsLoading(true);

    try {
      console.log('📡 Sending POST to /github/analyze');
      console.log('🌐 Using baseURL:', axios.defaults.baseURL);

      const response = await axios.post('/github/analyze', {
        repo_url: formData.repo_url.trim(),
        branch: formData.branch.trim() || 'main',
        files_pattern: formData.files_pattern.trim() || '*.py'
      });

      console.log('✅ RESPONSE RECEIVED:', response.data);
      console.log('🆔 JOB ID:', response.data.job_id);
      console.log('📊 Status:', response.data.status);

      onAnalysisStart(response.data);
      console.log('✅ Called onAnalysisStart with job data');

    } catch (error) {
      console.error('❌ ANALYSIS ERROR:', error);
      console.error('Error details:', error.response?.data);

      if (error.response?.data?.detail) {
        setError(error.response.data.detail);
      } else {
        setError('Failed to start analysis. Please check your repository URL and try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const exampleRepos = [
    'https://github.com/pallets/flask',
    'https://github.com/django/django',
    'https://github.com/fastapi/fastapi'
  ];

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
        </div>

        <div className="card-content">
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">
                Repository URL *
              </label>
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
                <label className="form-label">
                  Branch
                </label>
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
                <label className="form-label">
                  File Pattern
                </label>
                <input
                  type="text"
                  name="files_pattern"
                  value={formData.files_pattern}
                  onChange={handleInputChange}
                  className="form-input"
                  placeholder="*.py"
                  disabled={isLoading}
                />
                <small style={{ color: 'rgba(255, 255, 255, 0.7)', fontSize: '0.875rem' }}>
                  Comma-separated patterns (e.g., *.py, *.js, *.ts)
                </small>
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

          <div style={{
            marginTop: '2rem',
            paddingTop: '2rem',
            borderTop: '1px solid rgba(255, 255, 255, 0.1)'
          }}>
            <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem' }}>
              Try these example repositories:
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {exampleRepos.map((repo, index) => (
                <button
                  key={index}
                  type="button"
                  onClick={() => setFormData(prev => ({ ...prev, repo_url: repo }))}
                  style={{
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '6px',
                    padding: '0.5rem',
                    color: '#64ffda',
                    cursor: 'pointer',
                    textAlign: 'left',
                    fontSize: '0.9rem',
                    transition: 'all 0.3s ease'
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.background = 'rgba(255, 255, 255, 0.1)';
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.background = 'rgba(255, 255, 255, 0.05)';
                  }}
                  disabled={isLoading}
                >
                  {repo}
                </button>
              ))}
            </div>
          </div>

          <div style={{
            marginTop: '2rem',
            padding: '1rem',
            background: 'rgba(100, 255, 218, 0.1)',
            borderRadius: '8px',
            border: '1px solid rgba(100, 255, 218, 0.2)'
          }}>
            <h4 style={{
              color: '#64ffda',
              marginBottom: '0.5rem',
              fontSize: '0.95rem'
            }}>
              What will be analyzed:
            </h4>
            <ul style={{
              fontSize: '0.875rem',
              lineHeight: '1.6',
              paddingLeft: '1rem',
              color: 'rgba(255, 255, 255, 0.9)'
            }}>
              <li>🔍 <strong>Codebase Analysis</strong> - Dependencies, dead code, impact assessment</li>
              <li>🎯 <strong>Pattern Matching</strong> - AST antipatterns, complexity analysis</li>
              <li>🔬 <strong>Type Analysis</strong> - Signature validation, type hint checking</li>
              <li>📋 <strong>Duplicate Detection</strong> - Code duplication and copy-paste issues</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GitHubAnalyzer;