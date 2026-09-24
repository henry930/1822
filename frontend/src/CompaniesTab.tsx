import { useEffect, useMemo, useState } from "react";
import {
  deleteCompanyCorrection,
  fetchBoardMap,
  fetchCompanies,
  saveCompanyCorrection,
  type CompaniesData,
  type CompanyEntry,
  type MapCity,
} from "./api";

// Setup tab for every major/minor company's home (and, for majors,
// destination) hex - lists every company at once instead of having to hunt
// through the map tab's ~84 catalogued hexes to find which ones reference
// a given company. A correction here is a proposed override collected
// server-side (same staging pattern as the map tab's region corrections),
// not something applied to live gameplay - merging it into the real
// app.data source files is a separate step.
type RowEdit = { homeHex: string; destinationHex: string };

function rowEditFor(c: CompanyEntry): RowEdit {
  return {
    homeHex: c.correction_home_hex ?? c.current_home_hex ?? "",
    destinationHex: c.correction_destination_hex ?? c.current_destination_hex ?? "",
  };
}

export default function CompaniesTab() {
  const [data, setData] = useState<CompaniesData | null>(null);
  const [cities, setCities] = useState<MapCity[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [edits, setEdits] = useState<Record<string, RowEdit>>({});
  const [saving, setSaving] = useState<Record<string, boolean>>({});
  const [savedMessage, setSavedMessage] = useState<Record<string, string>>({});
  const [rowError, setRowError] = useState<Record<string, string>>({});

  function load() {
    fetchCompanies()
      .then((d) => {
        setData(d);
        setEdits((prev) => {
          const next = { ...prev };
          for (const c of [...d.majors, ...d.minors]) {
            if (!(c.id in next)) next[c.id] = rowEditFor(c);
          }
          return next;
        });
      })
      .catch((e) => setLoadError((e as Error).message));
    fetchBoardMap()
      .then((d) => setCities(d.cities))
      .catch(() => {
        // Name lookup is a nice-to-have - the tab still works without it.
      });
  }

  useEffect(load, []);

  const nameByHexId = useMemo(() => {
    const map = new Map<string, string>();
    for (const c of cities) map.set(c.id, c.name);
    return map;
  }, [cities]);

  function hexHint(hexId: string): string {
    const trimmed = hexId.trim().toUpperCase();
    if (!trimmed) return "";
    const name = nameByHexId.get(trimmed);
    return name ? `→ ${name}` : "→ not a catalogued hex";
  }

  async function saveRow(c: CompanyEntry) {
    const edit = edits[c.id] ?? rowEditFor(c);
    const homeHex = edit.homeHex.trim().toUpperCase();
    if (!homeHex) {
      setRowError({ ...rowError, [c.id]: "Home hex is required." });
      return;
    }
    const payload: Record<string, unknown> = { homeHex };
    if (c.kind === "major") {
      const destinationHex = edit.destinationHex.trim().toUpperCase();
      if (!destinationHex) {
        setRowError({ ...rowError, [c.id]: "Destination hex is required for a major." });
        return;
      }
      payload.destinationHex = destinationHex;
    }
    setSaving({ ...saving, [c.id]: true });
    setRowError({ ...rowError, [c.id]: "" });
    try {
      await saveCompanyCorrection(c.id, payload);
      setSavedMessage({ ...savedMessage, [c.id]: "Saved." });
      load();
    } catch (e) {
      setRowError({ ...rowError, [c.id]: (e as Error).message });
    } finally {
      setSaving({ ...saving, [c.id]: false });
    }
  }

  async function discardRow(c: CompanyEntry) {
    setSaving({ ...saving, [c.id]: true });
    try {
      await deleteCompanyCorrection(c.id);
      setEdits({ ...edits, [c.id]: { homeHex: c.current_home_hex ?? "", destinationHex: c.current_destination_hex ?? "" } });
      setSavedMessage({ ...savedMessage, [c.id]: "Reverted to the live default." });
      load();
    } catch (e) {
      setRowError({ ...rowError, [c.id]: (e as Error).message });
    } finally {
      setSaving({ ...saving, [c.id]: false });
    }
  }

  function renderRow(c: CompanyEntry) {
    const edit = edits[c.id] ?? rowEditFor(c);
    const hasCorrection = c.correction_home_hex != null || c.correction_destination_hex != null;
    return (
      <tr key={c.id} className={hasCorrection ? "company-row-corrected" : undefined}>
        <td>
          <strong>{c.id}</strong>
          {c.abbr && c.abbr !== c.id && <span className="hint"> ({c.abbr})</span>}
        </td>
        <td>{c.name}</td>
        <td>
          <div className="company-hex-cell">
            <input
              value={edit.homeHex}
              onChange={(e) => setEdits({ ...edits, [c.id]: { ...edit, homeHex: e.target.value } })}
              placeholder="e.g. H5"
            />
            <span className="hint company-hex-hint">{hexHint(edit.homeHex)}</span>
          </div>
          {c.current_home_hex && (
            <p className="hint company-current-note">
              Live default: {c.current_home_hex}
              {nameByHexId.get(c.current_home_hex) ? ` (${nameByHexId.get(c.current_home_hex)})` : ""}
            </p>
          )}
        </td>
        {c.kind === "major" && (
          <td>
            <div className="company-hex-cell">
              <input
                value={edit.destinationHex}
                onChange={(e) => setEdits({ ...edits, [c.id]: { ...edit, destinationHex: e.target.value } })}
                placeholder="e.g. H1"
              />
              <span className="hint company-hex-hint">{hexHint(edit.destinationHex)}</span>
            </div>
            {c.current_destination_hex && (
              <p className="hint company-current-note">
                Live default: {c.current_destination_hex}
                {nameByHexId.get(c.current_destination_hex) ? ` (${nameByHexId.get(c.current_destination_hex)})` : ""}
              </p>
            )}
          </td>
        )}
        <td>
          <div className="company-row-actions">
            <button onClick={() => saveRow(c)} disabled={saving[c.id]}>
              {saving[c.id] ? "Saving..." : "Save"}
            </button>
            {hasCorrection && (
              <button onClick={() => discardRow(c)} disabled={saving[c.id]}>
                Revert
              </button>
            )}
          </div>
          {rowError[c.id] && <p className="error">{rowError[c.id]}</p>}
          {!rowError[c.id] && savedMessage[c.id] && <p className="place-confirmed">✓ {savedMessage[c.id]}</p>}
        </td>
      </tr>
    );
  }

  return (
    <div className="panel companies-panel">
      <h3>Companies: home & destination setup</h3>
      <p className="hint">
        Every major and minor company's home hex (majors also have a destination hex) - the "live default" is what
        the engine actually uses right now, read from the catalogued map data. Saving here records a proposed
        correction alongside it for review, the same way the map tab's region corrections work - it doesn't change
        live gameplay by itself.
      </p>
      {loadError && <p className="error">{loadError}</p>}
      {!data && !loadError && <p className="hint">Loading...</p>}

      {data && (
        <>
          <h4>Major companies ({data.majors.length})</h4>
          <table className="companies-table">
            <thead>
              <tr>
                <th>Abbr</th>
                <th>Name</th>
                <th>Home hex</th>
                <th>Destination hex</th>
                <th></th>
              </tr>
            </thead>
            <tbody>{data.majors.map(renderRow)}</tbody>
          </table>

          <h4>Minor companies ({data.minors.length})</h4>
          <table className="companies-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Home hex</th>
                <th></th>
              </tr>
            </thead>
            <tbody>{data.minors.map(renderRow)}</tbody>
          </table>
        </>
      )}
    </div>
  );
}
