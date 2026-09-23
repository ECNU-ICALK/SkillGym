import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:3001";

export function useCountryDetails(countryCode) {
  const [state, setState] = useState({
    loading: false,
    error: "",
    detail: null
  });

  useEffect(() => {
    if (!countryCode) {
      return;
    }

    setState((current) => ({
      ...current,
      loading: true,
      error: ""
    }));

    fetch(`${API_BASE}/api/countries/${countryCode}`)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Failed to load details (${response.status})`);
        }
        return response.json();
      })
      .then((detail) => {
        setState({
          loading: false,
          error: "",
          detail
        });
      })
      .catch((error) => {
        setState({
          loading: false,
          error: error instanceof Error ? error.message : "Failed to load details",
          detail: null
        });
      });
  }, [countryCode]);

  return state;
}
