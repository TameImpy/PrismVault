"use client";

import { createContext, useContext, useEffect, ReactNode } from "react";
import { usePathname } from "next/navigation";
import mixpanel from "mixpanel-browser";

interface AnalyticsContext {
  track: (event: string, properties?: Record<string, unknown>) => void;
  identify: (
    userId: string,
    traits?: { email?: string; name?: string; created?: string }
  ) => void;
}

const AnalyticsCtx = createContext<AnalyticsContext>({
  track: () => {},
  identify: () => {},
});

const MIXPANEL_TOKEN = process.env.NEXT_PUBLIC_MIXPANEL_TOKEN;

export function AnalyticsProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    if (MIXPANEL_TOKEN) {
      mixpanel.init(MIXPANEL_TOKEN, {
        track_pageview: false,
        persistence: "localStorage",
        api_host: "https://api-eu.mixpanel.com",
      });
    }
  }, []);

  const pathname = usePathname();

  useEffect(() => {
    if (MIXPANEL_TOKEN) {
      mixpanel.track("Page Viewed", { page: pathname });
    }
  }, [pathname]);

  function track(event: string, properties?: Record<string, unknown>) {
    if (MIXPANEL_TOKEN) {
      mixpanel.track(event, properties);
    }
  }

  function identify(
    userId: string,
    traits?: { email?: string; name?: string; created?: string }
  ) {
    if (MIXPANEL_TOKEN) {
      mixpanel.identify(userId);
      if (traits) {
        mixpanel.people.set({
          ...(traits.email && { $email: traits.email }),
          ...(traits.name && { $name: traits.name }),
          ...(traits.created && { $created: traits.created }),
        });
      }
    }
  }

  return (
    <AnalyticsCtx.Provider value={{ track, identify }}>
      {children}
    </AnalyticsCtx.Provider>
  );
}

export function useAnalytics() {
  return useContext(AnalyticsCtx);
}
