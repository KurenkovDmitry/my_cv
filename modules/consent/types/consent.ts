import type {
  AnalyticsConsentContent,
  ConsentStateSnapshot,
  LocaleCode,
} from "@portfolio/shared-types";

export interface ConsentModalProps {
  localeCode: LocaleCode;
  content: AnalyticsConsentContent;
  onAccept: () => void;
  onReject: () => void;
}

export type ConsentStateRecord = ConsentStateSnapshot;
