import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const GitHubAuthTest = () => {
  const [authStatus, setAuthStatus] = useState('Not authenticated');
  const [user, setUser] = useState(null);
  const [repos, setRepos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleOAuthCallback = useCallback(async (code, state) => {
    console.log('🔄 Handling OAuth callback...');
    console.log('Code:', code);
    console.log('State:', state);

    try {
      setLoading(true);
      setAuthStatus('Exchanging code for token...');

      const response = await axios.post('/auth/github/callback', null, {
        params: { code, state }
      });

      console.log('✅ OAuth callback response:', response.data);

      const userData = response.data.user;
      setUser(userData);
      setAuthStatus('Authenticated!');

      // Store token in localStorage
      localStorage.setItem('github_token', userData.access_token);
      localStorage.setItem('github_user', JSON.stringify(userData));

      // Clean up URL
      window.history.replaceState({}, document.title, "/test-auth");

      // Fetch repos automatically
      fetchRepos(userData.access_token);

    } catch (err) {
      console.error('❌ OAuth callback error:', err);
      setError(err.response?.data?.detail || err.message);
      setAuthStatus('Authentication failed');
    } finally {
      setLoading(false);
    }
  }, []); // Empty dependency array since it doesn't depend on anything

  // Check for OAuth callback
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const state = urlParams.get('state');

    if (code && state) {
      handleOAuthCallback(code, state);
    }
  }, [handleOAuthCallback]);

  const startOAuth = async () => {
    console.log('🚀 Starting OAuth flow...');

    try {
      setLoading(true);
      setError('');

      const response = await axios.get('/auth/github');
      console.log('✅ OAuth URL response:', response.data);

      const { oauth_url } = response.data;
      console.log('📍 Redirecting to:', oauth_url);

      // Redirect to GitHub
      window.location.href = oauth_url;

    } catch (err) {
      console.error('❌ Error starting OAuth:', err);
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchRepos = async (token = null) => {
    console.log('📦 Fetching repos...');

    const accessToken = token || localStorage.getItem('github_token');

    if (!accessToken) {
      setError('No access token available');
      return;
    }

    try {
      setLoading(true);
      setError('');

      const response = await axios.get('/github/repos', {
        params: { access_token: accessToken, page: 1 }
      });

      console.log('✅ Repos response:', response.data);

      setRepos(response.data.repos);

    } catch (err) {
      console.error('❌ Error fetching repos:', err);
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('github_token');
    localStorage.removeItem('github_user');
    setUser(null);
    setRepos([]);
    setAuthStatus('Not authenticated');
  };

  // Check if already authenticated
  useEffect(() => {
    const storedToken = localStorage.getItem('github_token');
    const storedUser = localStorage.getItem('github_user');

    if (storedToken && storedUser) {
      setUser(JSON.parse(storedUser));
      setAuthStatus('Authenticated (from storage)');
    }
  }, []);

  return (
    <div style={{
      padding: '2rem',
      maxWidth: '1200px',
      margin: '0 auto',
      fontFamily: 'monospace'
    }}>
      <h1>🧪 GitHub OAuth Test</h1>

      {/* Status */}
      <div style={{
        background: '#1e1e1e',
        padding: '1rem',
        borderRadius: '8px',
        marginBottom: '1rem'
      }}>
        <p><strong>Status:</strong> {authStatus}</p>
        {user && (
          <div style={{ marginTop: '1rem' }}>
            <p><strong>Username:</strong> {user.username}</p>
            <p><strong>Avatar:</strong></p>
            <img
              src={user.avatar_url}
              alt="avatar"
              style={{ width: '50px', borderRadius: '50%' }}
            />
          </div>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div style={{
          background: '#ff000020',
          border: '1px solid #ff0000',
          padding: '1rem',
          borderRadius: '8px',
          marginBottom: '1rem',
          color: '#ff6b6b'
        }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Actions */}
      <div style={{ marginBottom: '2rem', display: 'flex', gap: '1rem' }}>
        {!user ? (
          <button
            onClick={startOAuth}
            disabled={loading}
            style={{
              padding: '0.75rem 1.5rem',
              background: '#667eea',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: '1rem'
            }}
          >
            {loading ? '⏳ Loading...' : '🔗 Connect GitHub'}
          </button>
        ) : (
          <>
            <button
              onClick={() => fetchRepos()}
              disabled={loading}
              style={{
                padding: '0.75rem 1.5rem',
                background: '#10b981',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: '1rem'
              }}
            >
              {loading ? '⏳ Loading...' : '📦 Fetch Repos'}
            </button>

            <button
              onClick={logout}
              style={{
                padding: '0.75rem 1.5rem',
                background: '#ef4444',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '1rem'
              }}
            >
              🚪 Logout
            </button>
          </>
        )}
      </div>

      {/* Repos List */}
      {repos.length > 0 && (
        <div>
          <h2>📦 Your Repositories ({repos.length})</h2>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
            gap: '1rem'
          }}>
            {repos.map(repo => (
              <div
                key={repo.id}
                style={{
                  background: '#2a2a2a',
                  padding: '1rem',
                  borderRadius: '8px',
                  border: '1px solid #444'
                }}
              >
                <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1rem' }}>
                  {repo.name}
                </h3>
                {repo.description && (
                  <p style={{
                    fontSize: '0.875rem',
                    color: '#aaa',
                    margin: '0 0 0.5rem 0'
                  }}>
                    {repo.description}
                  </p>
                )}
                <div style={{ fontSize: '0.75rem', color: '#888' }}>
                  {repo.language && <span>📝 {repo.language}</span>}
                  <span style={{ marginLeft: '1rem' }}>⭐ {repo.stars}</span>
                </div>
                <div style={{ marginTop: '0.5rem' }}>
                  <a
                    href={repo.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: '#64ffda', fontSize: '0.875rem' }}
                  >
                    View on GitHub →
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Debug Info */}
      <details style={{ marginTop: '2rem' }}>
        <summary style={{ cursor: 'pointer', userSelect: 'none' }}>
          🐛 Debug Info
        </summary>
        <pre style={{
          background: '#1a1a1a',
          padding: '1rem',
          borderRadius: '8px',
          overflow: 'auto',
          fontSize: '0.875rem'
        }}>
          {JSON.stringify({
            authStatus,
            hasUser: !!user,
            reposCount: repos.length,
            hasToken: !!localStorage.getItem('github_token')
          }, null, 2)}
        </pre>
      </details>
    </div>
  );
};

export default GitHubAuthTest;