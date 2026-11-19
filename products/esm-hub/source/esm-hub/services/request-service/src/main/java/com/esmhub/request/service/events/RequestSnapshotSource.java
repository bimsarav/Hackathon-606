package com.esmhub.request.service.events;

import com.esmhub.request.service.request.ServiceRequestRepository;
import com.esmhub.common.events.OutboxPublisher;
import com.esmhub.common.events.SnapshotSource;
import org.springframework.stereotype.Component;

/** Republishes all requests to request.requests on first start / after the demo seed. */
@Component
public class RequestSnapshotSource implements SnapshotSource {
    private final ServiceRequestRepository requests;
    private final RequestEvents events;

    public RequestSnapshotSource(ServiceRequestRepository requests, RequestEvents events) {
        this.requests = requests;
        this.events = events;
    }

    @Override public String name() { return "request"; }
    @Override public int version() { return 1; }

    @Override
    public void publishAll(OutboxPublisher publisher) {
        requests.findAll().forEach(r -> events.snapshot(publisher, r));
    }
}
