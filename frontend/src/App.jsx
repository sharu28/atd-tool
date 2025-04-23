import { useState } from "react";

export default function App() {
  const [file, setFile]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [data, setData]       = useState(null);
  const [error, setError]     = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) return;

    setLoading(true); setError(""); setData(null);

    try {
      const fd = new FormData();
      fd.append("file", file);

      const res  = await fetch("/validate", { method: "POST", body: fd });
      if (!res.ok) throw new Error(`Server ${res.status}`);
      const json = await res.json();
      setData(json);
    } catch (err) {
      console.error(err);
      setError("Something went wrong!");
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
          onChange={e => setFile(e.target.files[0])}
        />
        <button disabled={loading}>{loading ? "Checking…" : "Validate"}</button>
      </form>

      {error && <p style={{ color: "red" }}>{error}</p>}

      {data && (
        <>
          <Section
            title="Client information"
            list={data.CLIENT_INFORMATION}
          />
          <Section title="Figures & values" list={data.FIGURES_AND_VALUES} />
          <Section
            title="Typography & language"
            list={data.TYPOGRAPHY_AND_LANGUAGE}
          />
        </>
      )}
    </div>
  );
}
