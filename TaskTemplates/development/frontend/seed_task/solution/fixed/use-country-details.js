import { useEffect, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:3001";

export function useCountryDetails(countryCode) {
  const requestRef = useRef(0);
  const [state, setState] = useState({
    loading: false,
    error: "",
    detail: null
  });

  useEffect(() => {
    if (!countryCode) {
      setState({
        loading: false,
        error: "",
        detail: null
      });
      return undefined;
    }

    const requestId = requestRef.current + 1;
    requestRef.current = requestId;
    const controller = new AbortController();

    setState({
      loading: true,
      error: "",
      detail: null
    });

    fetch(`${API_BASE}/api/countries/${countryCode}`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Failed to load details (${response.status})`);
        }
        return response.json();
      })
      .then((detail) => {
        if (requestRef.current !== requestId) {
          return;
        }
        setState({
          loading: false,
          error: "",
          detail
        });
      })
      .catch((error) => {
        if (controller.signal.aborted || requestRef.current !== requestId) {
          return;
        }
        setState({
          loading: false,
          error: error instanceof Error ? error.message : "Failed to load details",
          detail: null
        });
      });

    return () => {
      controller.abort();
    };
  }, [countryCode]);

  return state;
}
