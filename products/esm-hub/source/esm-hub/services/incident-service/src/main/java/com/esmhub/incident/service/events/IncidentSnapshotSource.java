package com.esmhub.incident.service.events;

import com.esmhub.common.events.OutboxPublisher;
import com.esmhub.common.events.SnapshotSource;
import com.esmhub.incident.service.incident.IncidentRepository;
import com.esmhub.incident.service.problem.ProblemRepository;
import org.springframework.stereotype.Component;

/** Republishes every incident and problem on first start and after the demo seed (reporting bootstrap). */
@Component
public class IncidentSnapshotSource implements SnapshotSource {
    private final IncidentEvents events;
    private final IncidentRepository incidents;
    private final ProblemRepository problems;

    public IncidentSnapshotSource(IncidentEvents events, IncidentRepository incidents, ProblemRepository problems) {
        this.events = events;
        this.incidents = incidents;
        this.problems = problems;
    }

    @Override public String name() { return "incident"; }
    @Override public int version() { return 1; }

    @Override
    public void publishAll(OutboxPublisher publisher) {
        incidents.findAll().forEach(events::snapshot);
        problems.findAll().forEach(events::snapshot);
    }
}
