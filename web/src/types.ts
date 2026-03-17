/**
 * OpenAI Apps SDK Types
 * Based on: https://developers.openai.com/apps-sdk/build/custom-ux
 */

export type Theme = "light" | "dark";
export type DisplayMode = "pip" | "inline" | "fullscreen";
export type DeviceType = "mobile" | "tablet" | "desktop" | "unknown";

export interface SafeAreaInsets {
  top: number;
  bottom: number;
  left: number;
  right: number;
}

export interface SafeArea {
  insets: SafeAreaInsets;
}

export interface UserAgent {
  device: { type: DeviceType };
  capabilities: {
    hover: boolean;
    touch: boolean;
  };
}

export interface CallToolResponse {
  content: Array<{
    type: string;
    text?: string;
  }>;
  isError?: boolean;
}

export interface OpenAiGlobals<
  ToolInput = any,
  ToolOutput = any,
  ToolResponseMetadata = any,
  WidgetState = any
> {
  theme: Theme;
  userAgent: UserAgent;
  locale: string;
  maxHeight: number;
  displayMode: DisplayMode;
  safeArea: SafeArea;
  toolInput: ToolInput;
  toolOutput: ToolOutput | null;
  toolResponseMetadata: ToolResponseMetadata | null;
  widgetState: WidgetState | null;
}

export interface OpenAiAPI<WidgetState = any> {
  callTool: (name: string, args: Record<string, unknown>) => Promise<CallToolResponse>;
  sendFollowUpMessage: (args: { prompt: string }) => Promise<void>;
  openExternal: (payload: { href: string }) => void;
  requestDisplayMode: (args: { mode: DisplayMode }) => Promise<{ mode: DisplayMode }>;
  setWidgetState: (state: WidgetState) => Promise<void>;
}

export const SET_GLOBALS_EVENT_TYPE = "openai:set_globals";

export class SetGlobalsEvent extends CustomEvent<{
  globals: Partial<OpenAiGlobals>;
}> {
  readonly type = SET_GLOBALS_EVENT_TYPE;
}

declare global {
  interface Window {
    openai: OpenAiAPI & OpenAiGlobals;
  }

  interface WindowEventMap {
    [SET_GLOBALS_EVENT_TYPE]: SetGlobalsEvent;
  }
}

// ---------------------------------------------------------------------------
// Rayna Tours domain types
// ---------------------------------------------------------------------------

export interface TourCard {
  id: string;
  title: string;
  slug?: string;
  image: string;
  location: string;
  category: string;
  originalPrice?: number | null;
  currentPrice: number | null;
  currency: string;
  discount?: number;
  discountPercentage?: number;
  isRecommended?: boolean;
  isNew?: boolean;
  rPoints?: number;
  rating?: number;
  reviewCount?: number;
  duration?: string;
  highlights?: string[];
  url: string;
  priceLabel?: string;
  dataSource?: "api" | "static" | "rag";
}

export interface TourListOutput {
  tours: TourCard[];
  title: string;
  subtitle?: string;
  totalResults: number;
  dataSource: "api" | "static" | "rag";
}

export interface TourDetailOutput {
  title: string;
  description: string;
  image: string;
  location: string;
  category: string;
  currentPrice: number | null;
  originalPrice?: number | null;
  currency: string;
  duration?: string;
  highlights?: string[];
  inclusions?: string[];
  exclusions?: string[];
  rating?: number;
  reviewCount?: number;
  url: string;
  rPoints?: number;
}

export interface TourComparisonOutput {
  tours: TourCard[];
  comparison: {
    stats: Array<{
      name: string;
      values: (string | number)[];
      better?: string;
    }>;
  };
}

export interface TourListWidgetState {
  favorites: string[];
}

export interface TourCompareWidgetState {
  favorites: string[];
}
