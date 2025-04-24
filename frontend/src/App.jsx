// src/App.jsx
import { useState } from "react";

export default function App() {
  const [file,    setFile]    = useState(null);
  const [loading, setLoading] = useState(false);
  const [data,    setData]    = useState(null);
  const [error,   setError]   = useState("");

  // Point directly at API:
  const API_BASE = "https://atd-tool.onrender.com";

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setError("");
    setData(null);

    try {
      const fd = new FormData();
      fd.append("file", file);

      // ← note the change here: full absolute URL instead of just "/validate"
      const res = await fetch(`${API_BASE}/validate`, {
        method: "POST",
        body: fd
      });

      const text = await res.text();
      console.log("🛰  /validate response", res.status, text);

      let json;
      try {
        json = JSON.parse(text);
      } catch (parseErr) {
        console.warn("Could not parse JSON:", parseErr);
        json = {};
      }

      if (!res.ok) {
        const msg = json.error || json.detail || `Server error ${res.status}`;
        setError(msg);
      } else {
        setData(json);
      }
    } catch (networkErr) {
      console.error("Network error:", networkErr);
      setError("Network error: " + networkErr.message);
    } finally {
      setLoading(false);
    }
  }

  const Section = ({ title, list }) =>
    list?.length ? (
      <>
        <h3>{title}</h3>
        <ul>
          {list.map((x, i) => (
            <li key={i}>
              <strong>{x.issue}</strong>: {x.details}
            </li>
          ))}
        </ul>
      </>
    ) : null;

  return (
    <div className="container">
      <h1>ATD Validator</h1>

      <form onSubmit={handleSubmit}>
        <input
          type="file"
          accept=".doc,.docx"
          onChange={(e) => setFile(e.target.files[0])}
        />
        <button disabled={loading}>
          {loading ? "Checking…" : "Validate"}
        </button>
      </form>

      {error && <p style={{ color: "red" }}>{error}</p>}

      {data && (
        <>
          <Section title="Client information" list={data.CLIENT_INFORMATION} />
          <Section title="Figures & values"    list={data.FIGURES_AND_VALUES} />
          <Section
            title="Typography & language"
            list={data.TYPOGRAPHY_AND_LANGUAGE}
          />
        </>
      )}
    </div>
  );
}
