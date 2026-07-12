"use client";

import { useEffect, useState } from "react";

export type DevCoreEvent = {
  type: string;
  payload: unknown;
};

export function useDevCoreEvents() {
  const [events, setEvents] = useState<DevCoreEvent[]>([]);

  useEffect(() => {
    const source = new EventSource("/api/v1/events");
    source.onmessage = (message) => {
      setEvents((current) => [...current.slice(-19), JSON.parse(message.data) as DevCoreEvent]);
    };
    return () => source.close();
  }, []);

  return events;
}
