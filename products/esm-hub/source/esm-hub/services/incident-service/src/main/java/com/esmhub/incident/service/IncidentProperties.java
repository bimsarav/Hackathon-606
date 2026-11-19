package com.esmhub.incident.service;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Business-rule settings (requirements-analysis §5, BQ-4 defaults pending PO approval).
 *
 * @param reopenWindowDays resolved incidents can be reopened within this many days
 * @param autoCloseDays    resolved incidents are closed automatically after this many days
 * @param atRiskPct        share of the resolution target after which RESOLUTION_AT_RISK escalates
 * @param exportMaxRows    cap for CSV exports
 * @param jobsEnabled      runs the SLA scan and auto-close on their schedules
 */
@ConfigurationProperties("esm.incident")
public record IncidentProperties(int reopenWindowDays, int autoCloseDays, int atRiskPct, int exportMaxRows,
                                 boolean jobsEnabled) {
    public IncidentProperties {
        if (reopenWindowDays <= 0) reopenWindowDays = 7;
        if (autoCloseDays <= 0) autoCloseDays = 3;
        if (atRiskPct <= 0) atRiskPct = 80;
        if (exportMaxRows <= 0) exportMaxRows = 10_000;
    }
}
