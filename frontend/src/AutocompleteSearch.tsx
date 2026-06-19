import { useEffect, useRef, useState } from "react";
import type { SearchResponse, SelectedEntity } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

type AutocompleteSearchProps = {
  label: string;
  placeholder: string;
  endpoint: string;
  extraParams?: Record<string, string>;
  value: SelectedEntity | null;
  onChange: (item: SelectedEntity | null) => void;
  initialQuery?: string;
  disabled?: boolean;
};

export function AutocompleteSearch({
  label,
  placeholder,
  endpoint,
  extraParams = {},
  value,
  onChange,
  initialQuery = "",
  disabled = false,
}: AutocompleteSearchProps) {
  const [query, setQuery] = useState(value?.label ?? initialQuery);
  const [results, setResults] = useState<SearchResponse["results"]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (value) setQuery(value.label);
  }, [value]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  useEffect(() => {
    if (query.trim().length < 2) {
      setResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams({ q: query, ...extraParams });
        const res = await fetch(`${API_BASE}${endpoint}?${params}`);
        const json: SearchResponse = await res.json();
        setResults(json.results ?? []);
        setOpen(true);
        if (json.error && !json.available) setError(json.error);
      } catch {
        setError("Search unavailable");
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [query, endpoint, JSON.stringify(extraParams)]);

  return (
    <div className="autocompleteWrap" ref={wrapRef}>
      <label>{label}</label>
      <input
        type="text"
        value={query}
        placeholder={placeholder}
        disabled={disabled}
        onChange={(e) => {
          setQuery(e.target.value);
          if (value && e.target.value !== value.label) onChange(null);
        }}
        onFocus={() => query.length >= 2 && setOpen(true)}
      />
      {loading && <span className="searchStatus">Searching…</span>}
      {value && <span className="selectedChip">{value.label}</span>}
      {open && results.length > 0 && (
        <ul className="autocompleteList" role="listbox">
          {results.map((item) => (
            <li key={`${item.id}-${item.label}`}>
              <button
                type="button"
                onClick={() => {
                  onChange({ id: item.id, label: item.label, meta: item.meta });
                  setQuery(item.label);
                  setOpen(false);
                }}
              >
                <strong>{item.label}</strong>
                {item.subtitle && <span className="optionSubtitle">{item.subtitle}</span>}
                <span className="optionSource">{item.source}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {error && <span className="searchError">{error}</span>}
    </div>
  );
}
