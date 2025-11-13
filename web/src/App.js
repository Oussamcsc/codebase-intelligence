import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import GitHubAnalyzer from './components/GitHubAnalyzer';
import AnalysisResults from './components/AnalysisResults';
import ProgressTracker from './components/ProgressTracker';
import GitHubAuthTest from './components/GitHubAuthTest';
import { Github, Code2, Zap, Shield } from 'lucide-react';

// Configure axios base URL
axios.defaults.baseURL = 'http://localhost:8000';
console.log('🌐 Axios configured with baseURL:', axios.defaults.baseURL);

function App() {
  const [currentView, setCurrentView] = useState('home');
  const [analysisJob, setAnalysisJob] = useState(null);
  const [analysisResults, setAnalysisResults] = useState(null);
  const [githubUser, setGithubUser] = useState(null);

  // Check for test mode
  const isTestMode = window.location.pathname === '/test-auth';

  // Handle OAuth callback
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const state = urlParams.get('state');

    if (code && state && window.location.pathname === '/auth/callback') {
      console.log('🔄 Handling OAuth callback in main app');
      handleOAuthCallback(code, state);
    }
  }, []);

  // Check for stored auth
  useEffect(() => {
    const storedToken = localStorage.getItem('github_token');
    const storedUser = localStorage.getItem('github_user');

    if (storedToken && storedUser) {
      console.log('✅ Found stored GitHub auth');
      setGithubUser(JSON.parse(storedUser));
    }
  }, []);

  const handleOAuthCallback = async (code, state) => {
    console.log('🔄 Exchanging code for token...');

    try {
      const response = await axios.post('/auth/github/callback', null, {
        params: { code, state }
      });

      console.log('✅ OAuth callback success:', response.data);

      const userData = response.data.user;
      setGithubUser(userData);

      // Store in localStorage
      localStorage.setItem('github_token', userData.access_token);
      localStorage.setItem('github_user', JSON.stringify(userData));

      // Clean URL and go to github analyzer
      window.history.replaceState({}, document.title, "/");
      setCurrentView('github');

    } catch (err) {
      console.error('❌ OAuth callback error:', err);
      alert('GitHub authentication failed. Please try again.');
      window.history.replaceState({}, document.title, "/");
      setCurrentView('home');
    }
  };

  const handleGitHubLogout = () => {
    console.log('🚪 Logging out of GitHub');
    localStorage.removeItem('github_token');
    localStorage.removeItem('github_user');
    setGithubUser(null);
  };

  // If in test mode, show test component
  if (isTestMode) {
    return <GitHubAuthTest />;
  }

  const handleAnalysisStart = (jobData) => {
    console.log('🎯 APP.JS - handleAnalysisStart called');
    console.log('📦 jobData:', jobData);
    console.log('🆔 job_id:', jobData?.job_id);

    setAnalysisJob(jobData);
    setCurrentView('progress');

    console.log('✅ State updated, switching to progress view');
  };

  const handleAnalysisComplete = (results) => {
    console.log('🎉 APP.JS - handleAnalysisComplete called');
    console.log('📊 Results:', results);

    setAnalysisResults(results);
    setCurrentView('results');

    console.log('✅ Switched to results view');
  };

  const resetToHome = () => {
    console.log('🏠 Resetting to home');
    setCurrentView('home');
    setAnalysisJob(null);
    setAnalysisResults(null);
  };

  const renderView = () => {
    console.log('🎨 Rendering view:', currentView);

    switch (currentView) {
      case 'github':
        return (
          <GitHubAnalyzer
            onAnalysisStart={handleAnalysisStart}
            onBack={() => setCurrentView('home')}
            githubUser={githubUser}
            onLogout={handleGitHubLogout}
          />
        );
      case 'progress':
        return (
          <ProgressTracker
            jobId={analysisJob?.job_id}
            onComplete={handleAnalysisComplete}
            onBack={resetToHome}
          />
        );
      case 'results':
        return (
          <AnalysisResults
            results={analysisResults}
            onBack={resetToHome}
            onNewAnalysis={() => setCurrentView('home')}
          />
        );
      default:
        return (
          <div className="home-container">
            <div className="hero-section">
              <div className="hero-content">
                <h1 className="hero-title">
                  <Code2 className="hero-icon" />
                  AI Code Review Assistant
                </h1>
                <p className="hero-subtitle">
                  Comprehensive code analysis with 4 specialized analyzers
                </p>

                <div className="features-grid">
                  <div className="feature-card">
                    <Zap className="feature-icon" />
                    <h3>Codebase Analyzer</h3>
                    <p>Dependencies, dead code, impact analysis</p>
                  </div>

                  <div className="feature-card">
                    <Shield className="feature-icon" />
                    <h3>Pattern Matcher</h3>
                    <p>AST antipatterns, complexity, bad practices</p>
                  </div>

                  <div className="feature-card">
                    <Code2 className="feature-icon" />
                    <h3>Type Analyzer</h3>
                    <p>Signature validation, type mismatches</p>
                  </div>

                  <div className="feature-card">
                    <Github className="feature-icon" />
                    <h3>Duplicate Detector</h3>
                    <p>Code duplication, copy-paste detection</p>
                  </div>
                </div>

                <div className="action-buttons">
                  <button
                    className="btn-primary"
                    onClick={() => setCurrentView('github')}
                  >
                    <Github className="btn-icon" />
                    Analyze GitHub Repository
                  </button>
                </div>

                <div className="stats-section">
                  <div className="stat-item">
                    <span className="stat-number">4</span>
                    <span className="stat-label">Specialized Analyzers</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-number">88%</span>
                    <span className="stat-label">Noise Reduction</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-number">Senior</span>
                    <span className="stat-label">Engineer Focus</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        );
    }
  };

  return (
    <div className="App">
      {renderView()}
    </div>
  );
}

export default App;