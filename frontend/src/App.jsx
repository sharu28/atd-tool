import React, { useState, useEffect } from 'react';

const isAdmin = window.location.pathname.includes('admin');
const basicAuthHeader = {
  Authorization: 'Basic ' + btoa('admin:secret123') // replace with actual password later
};

function App() {
  const [file, setFile] = useState(null);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [prompt, setPrompt] = useState(null);
  const [promptText, setPromptText] = useState('');

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    setLoading(true);
    setResults([]);

    try {
      const res = await fetch('http://127.0.0.1:8000/validate', {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      setResults(data);
    } catch (err) {
      alert('Something went wrong!');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAdmin) {
      fetch('http://127.0.0.1:8000/prompt', { headers: basicAuthHeader })
        .then((res) => res.json())
        .then((data) => {
          setPrompt(data);
          setPromptText(JSON.stringify(data, null, 2));
        })
        .catch(() => alert('Failed to load prompt'));
    }
  }, []);

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1>ATD Validator</h1>

      <form onSubmit={handleUpload}>
        <input
          type="file"
          accept=".docx"
          onChange={(e) => setFile(e.target.files[0])}
        />
        <button type="submit" disabled={!file || loading}>
          {loading ? 'Checking...' : 'Validate'}
        </button>
      </form>

      <hr />

      {results.length > 0 && (
  <div style={{ marginTop: '2rem' }}>
    {results.map((row, idx) => (
      <div key={idx} style={{ marginBottom: '1rem' }}>
        <strong>• {row.item}</strong>
        <ul>
          {row.points && row.points.length > 0 ? (
            row.points.map((point, i) => <li key={i}>– {point}</li>)
          ) : (
            <li style={{ color: 'gray' }}>No issues found</li>
          )}
        </ul>
      </div>
    ))}
  </div>
)}


      {isAdmin && (
        <div style={{ marginTop: '2rem' }}>
          <h2>Admin: Prompt Editor</h2>

          <textarea
            rows={15}
            cols={80}
            value={promptText}
            onChange={(e) => setPromptText(e.target.value)}
          />

          <br />

          <button
            onClick={() => {
              fetch('http://127.0.0.1:8000/prompt', {
                method: 'PUT',
                headers: {
                  ...basicAuthHeader,
                  'Content-Type': 'application/json',
                },
                body: promptText,
              })
                .then((res) => res.json())
                .then(() => alert('Saved!'))
                .catch(() => alert('Failed to save'));
            }}
          >
            Save Prompt
          </button>
        </div>
      )}
    </div>
  );
}

export default App;
