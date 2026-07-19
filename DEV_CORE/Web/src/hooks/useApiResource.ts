"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type ResourceState<T> =
  | { status: "loading"; data: null; error: null }
  | { status: "empty"; data: null; error: null }
  | { status: "ready"; data: T; error: null }
  | { status: "error"; data: null; error: string };

export function useApiResource<T>(load: (signal: AbortSignal) => Promise<T | null>) {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<ResourceState<T>>({ status: "loading", data: null, error: null });

  const loadRef = useRef(load);
  loadRef.current = load;

  const retry = useCallback(() => setAttempt((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading", data: null, error: null });

    loadRef.current(controller.signal)
      .then((data) => {
        if (controller.signal.aborted) return;
        setState(data ? { status: "ready", data, error: null } : { status: "empty", data: null, error: null });
      })
      .catch((error: Error) => {
        if (controller.signal.aborted) return;
        const offline = typeof navigator !== "undefined" && !navigator.onLine;
        setState({
          status: "error",
          data: null,
          error: offline ? "Réseau indisponible. Reconnexion automatique au retour en ligne." : error.message,
        });
      });

    return () => controller.abort();
  }, [attempt]);

  useEffect(() => {
    const retryWhenOnline = () => retry();
    window.addEventListener("online", retryWhenOnline);
    return () => window.removeEventListener("online", retryWhenOnline);
  }, [retry]);

  return { ...state, retry };
}
