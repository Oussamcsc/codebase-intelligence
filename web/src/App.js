import React, { useState } from 'react';
import axios from 'axios';
import './App.css';
import GitHubAnalyzer from './components/GitHubAnalyzer';
import AnalysisResults from './components/AnalysisResults';
import ProgressTracker from './components/ProgressTracker';
import { Github, Code2, Zap, Shield } from 'lucide-react';

// Configure axios base URL
axios.defaults.baseURL = 'http://localhost:8000';
console.log('🌐 Axios configured with baseURL:', axios.defaults.baseURL);

function App() {
  const [currentView, setCurrentView] = useState('home');
  const [analysisJob, setAnalysisJob] = useState(null);
  const [analysisResults, setAnalysisResults] = useState(null);

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