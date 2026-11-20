package com.esmhub.incident.service.jobs;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/** Runs the SLA scan and the auto-close on their schedules (disabled with esm.incident.jobs-enabled=false). */
@Component
@ConditionalOnProperty(name = "esm.incident.jobs-enabled", havingValue = "true", matchIfMissing = true)
public class SlaScheduler {
    private static final Logger log = LoggerFactory.getLogger(SlaScheduler.class);
    private final SlaJobs jobs;

    public SlaScheduler(SlaJobs jobs) { this.jobs = jobs; }

    @Scheduled(fixedDelayString = "${esm.incident.sla-scan-ms:60000}", initialDelayString = "${esm.incident.sla-scan-ms:60000}")
    void scan() {
        try {
            int n = jobs.scanSla();
            if (n > 0) log.info("sla_scan flagged={}", n);
        } catch (RuntimeException e) {
            log.error("sla_scan failed", e);
        }
    }

    @Scheduled(fixedDelayString = "${esm.incident.auto-close-ms:900000}", initialDelayString = "${esm.incident.auto-close-ms:900000}")
    void autoClose() {
        try {
            int n = jobs.autoClose();
            if (n > 0) log.info("auto_close closed={}", n);
        } catch (RuntimeException e) {
            log.error("auto_close failed", e);
        }
    }
}
