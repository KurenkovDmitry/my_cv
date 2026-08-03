import type {
  AnalyticsSectionClickEventPayload,
  AnalyticsSectionViewEventPayload,
  AnalyticsSessionEventPayload,
} from "@portfolio/shared-types";

export interface RouteAnalyticsDescriptor {
  routeKey: string;
  sectionKeys: string[];
}

export type SessionEventRecord = AnalyticsSessionEventPayload;
export type SectionViewEventRecord = AnalyticsSectionViewEventPayload;
export type SectionClickEventRecord = AnalyticsSectionClickEventPayload;
