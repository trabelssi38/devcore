"use client";

import { useEffect, useState } from "react";

export type DevCoreEvent = {
  type: string;
  payload: unknown;
};

export function useDevCoreEvents() {
  const [events, setEvents] = useState<DevCoreEvent[]>([]);

  useEffect(() => {
    // Use the Next.js rewrite proxy — same-origin, no CORS issues
    const source = new EventSource("/proxy/dashboard/dashboard/stream");

    source.onmessage = (message) => {
      try {
        const parsed = JSON.parse(message.data) as DevCoreEvent;
        setEvents((current) => [...current.slice(-19), parsed]);
      } catch (e) {
        // Silently skip unparseable SSE frames
      }
    };

    source.onerror = () => {
      // Close on error to prevent browser infinite reconnect loop
      source.close();
    };

    return () => source.close();
  }, []);

  return events;
}

