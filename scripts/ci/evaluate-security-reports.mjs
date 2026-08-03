import { appendFile, readFile } from "node:fs/promises";

function safeNumber(value) {
  return Number.isFinite(value) ? value : 0;
}

async function readJsonOrDefault(filePath, fallbackValue) {
  try {
    const rawContent = await readFile(filePath, "utf8");
    return JSON.parse(rawContent);
  } catch {
    return fallbackValue;
  }
}

function summarizeNpmAudit(report) {
  const vulnerabilities = report?.metadata?.vulnerabilities ?? {};
  const high = safeNumber(vulnerabilities.high);
  const critical = safeNumber(vulnerabilities.critical);

  return {
    label: "npm audit",
    high,
    critical,
    total: safeNumber(vulnerabilities.total),
    blockingFindings: high + critical,
  };
}

function summarizePipAudit(report) {
  const dependencies = Array.isArray(report) ? report : [];
  const total = dependencies.reduce((accumulator, dependencyItem) => {
    const currentVulnerabilities = Array.isArray(dependencyItem?.vulns) ? dependencyItem.vulns.length : 0;
    return accumulator + currentVulnerabilities;
  }, 0);

  return {
    label: "pip-audit",
    high: total,
    critical: 0,
    total,
    blockingFindings: total,
  };
}

function summarizeTrivy(report) {
  const results = Array.isArray(report?.Results) ? report.Results : [];

  let vulnerabilityHigh = 0;
  let vulnerabilityCritical = 0;
  let misconfigurationHigh = 0;
  let misconfigurationCritical = 0;

  for (const resultItem of results) {
    for (const vulnerabilityItem of resultItem?.Vulnerabilities ?? []) {
      if (vulnerabilityItem?.Severity === "HIGH") {
        vulnerabilityHigh += 1;
      }

      if (vulnerabilityItem?.Severity === "CRITICAL") {
        vulnerabilityCritical += 1;
      }
    }

    for (const misconfigurationItem of resultItem?.Misconfigurations ?? []) {
      if (misconfigurationItem?.Severity === "HIGH") {
        misconfigurationHigh += 1;
      }

      if (misconfigurationItem?.Severity === "CRITICAL") {
        misconfigurationCritical += 1;
      }
    }
  }

  return {
    label: "Trivy filesystem scan",
    high: vulnerabilityHigh + misconfigurationHigh,
    critical: vulnerabilityCritical + misconfigurationCritical,
    total:
      vulnerabilityHigh +
      vulnerabilityCritical +
      misconfigurationHigh +
      misconfigurationCritical,
    blockingFindings:
      vulnerabilityHigh +
      vulnerabilityCritical +
      misconfigurationHigh +
      misconfigurationCritical,
  };
}

async function writeSummary(lines) {
  if (!process.env.GITHUB_STEP_SUMMARY) {
    return;
  }

  await appendFile(process.env.GITHUB_STEP_SUMMARY, `${lines.join("\n")}\n`, "utf8");
}

const npmAuditReport = await readJsonOrDefault("artifacts/security/npm-audit.json", {});
const pipAuditReport = await readJsonOrDefault("artifacts/security/pip-audit.json", []);
const trivyReport = await readJsonOrDefault("artifacts/security/trivy-report.json", {});

const summaries = [
  summarizeNpmAudit(npmAuditReport),
  summarizePipAudit(pipAuditReport),
  summarizeTrivy(trivyReport),
];

const blockingFindings = summaries.reduce(
  (accumulator, currentSummary) => accumulator + currentSummary.blockingFindings,
  0,
);

await writeSummary([
  "## Security Scan Summary",
  "",
  "| Scanner | High | Critical | Total | Blocking findings |",
  "| --- | ---: | ---: | ---: | ---: |",
  ...summaries.map(
    (summaryItem) =>
      `| ${summaryItem.label} | ${summaryItem.high} | ${summaryItem.critical} | ${summaryItem.total} | ${summaryItem.blockingFindings} |`,
  ),
  "",
  blockingFindings > 0
    ? `Security gate failed: found ${blockingFindings} blocking findings.`
    : "Security gate passed: no blocking findings were detected.",
]);

if (blockingFindings > 0) {
  process.exit(1);
}
