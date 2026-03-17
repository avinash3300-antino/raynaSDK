/**
 * React hooks for OpenAI Apps SDK
 * Based on: https://developers.openai.com/apps-sdk/build/custom-ux
 */

import { useCallback, useEffect, useSyncExternalStore, useState, SetStateAction } from "react";
import type { OpenAiGlobals, SetGlobalsEvent } from "./types";

/**
 * Subscribe to a single global value from window.openai
 */
export function useOpenAiGlobal<K extends keyof OpenAiGlobals>(
  key: K
): OpenAiGlobals[K] {
  return useSyncExternalStore(
    (onChange) => {
      const handleSetGlobal = (event: CustomEvent) => {
        const globals = (event as SetGlobalsEvent).detail.globals;
        const value = globals[key];
        if (value === undefined) {
          return;
        }
        onChange();
      };

      window.addEventListener("openai:set_globals", handleSetGlobal as EventListener, {
        passive: true,
      });

      return () => {
        window.removeEventListener("openai:set_globals", handleSetGlobal as EventListener);
      };
    },
    () => window.openai?.[key]
  );
}

export function useToolInput<T = any>(): T {
  return useOpenAiGlobal("toolInput") as T;
}

export function useToolOutput<T = any>(): T | null {
  return useOpenAiGlobal("toolOutput") as T | null;
}

export function useToolResponseMetadata<T = any>(): T | null {
  return useOpenAiGlobal("toolResponseMetadata") as T | null;
}

export function useTheme() {
  return useOpenAiGlobal("theme");
}

export function useDisplayMode() {
  return useOpenAiGlobal("displayMode");
}

/**
 * Widget state hook that syncs with window.openai
 */
export function useWidgetState<T extends Record<string, any>>(
  defaultState: T | (() => T)
): readonly [T, (state: SetStateAction<T>) => void];

export function useWidgetState<T extends Record<string, any>>(
  defaultState?: T | (() => T | null) | null
): readonly [T | null, (state: SetStateAction<T | null>) => void];

export function useWidgetState<T extends Record<string, any>>(
  defaultState?: T | (() => T | null) | null
): readonly [T | null, (state: SetStateAction<T | null>) => void] {
  const widgetStateFromWindow = useOpenAiGlobal("widgetState") as T;

  const [widgetState, _setWidgetState] = useState<T | null>(() => {
    if (widgetStateFromWindow != null) {
      return widgetStateFromWindow;
    }
    return typeof defaultState === "function"
      ? defaultState()
      : defaultState ?? null;
  });

  useEffect(() => {
    _setWidgetState(widgetStateFromWindow);
  }, [widgetStateFromWindow]);

  const setWidgetState = useCallback(
    (state: SetStateAction<T | null>) => {
      _setWidgetState((prevState) => {
        const newState = typeof state === "function" ? state(prevState) : state;
        if (newState != null && window.openai?.setWidgetState) {
          window.openai.setWidgetState(newState);
        }
        return newState;
      });
    },
    []
  );

  return [widgetState, setWidgetState] as const;
}
