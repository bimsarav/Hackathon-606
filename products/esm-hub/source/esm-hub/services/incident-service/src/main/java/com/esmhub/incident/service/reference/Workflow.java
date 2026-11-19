package com.esmhub.incident.service.reference;

import com.esmhub.common.web.BusinessRuleException;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.springframework.stereotype.Component;

/** Status lookups and the status_transitions workflow table (FR-3). Tables are tiny, so they are read on demand. */
@Component
public class Workflow {
    private final TicketStatusRepository statuses;
    private final StatusTransitionRepository transitions;
    private final PriorityRepository priorities;

    public Workflow(TicketStatusRepository statuses, StatusTransitionRepository transitions, PriorityRepository priorities) {
        this.statuses = statuses;
        this.transitions = transitions;
        this.priorities = priorities;
    }

    public TicketStatus status(String name) {
        return statuses.findByName(name).orElseThrow(() -> new IllegalStateException("Status " + name + " is not configured."));
    }

    public TicketStatus status(int id) {
        return statuses.findById(id).orElseThrow(() -> new IllegalStateException("Status " + id + " is not configured."));
    }

    public Map<Integer, TicketStatus> statusesById() {
        return statuses.findAll().stream().collect(Collectors.toMap(TicketStatus::getId, Function.identity()));
    }

    public Map<Integer, Priority> prioritiesById() {
        return priorities.findAll().stream().collect(Collectors.toMap(Priority::getId, Function.identity()));
    }

    public boolean allowed(int from, int to) {
        return transitions.existsById(new StatusTransition.Key(from, to));
    }

    public void check(TicketStatus from, TicketStatus to) {
        if (!allowed(from.getId(), to.getId())) {
            throw new BusinessRuleException("Transition " + from.getName() + " → " + to.getName() + " is not allowed.");
        }
    }

    /** Names of the statuses reachable from {@code from}, in status order. */
    public List<String> allowedFrom(int from) {
        Map<Integer, TicketStatus> byId = statusesById();
        return transitions.findAll().stream().map(StatusTransition::getId).filter(k -> k.fromStatusId() == from)
                .map(k -> byId.get(k.toStatusId())).sorted(Comparator.comparing(TicketStatus::getId))
                .map(TicketStatus::getName).toList();
    }
}
