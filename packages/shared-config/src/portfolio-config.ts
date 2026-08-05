import previewPortfolioContentJson from "../../../content/generated/portfolio.preview.json";
import type { PortfolioContent } from "@portfolio/shared-types";

/**
 * Единый preview-контент, собранный из резюме и используемый web/admin fallback-режимами.
 */
export const portfolioPreviewContent: PortfolioContent = previewPortfolioContentJson as PortfolioContent;
