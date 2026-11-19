package com.esmhub.gateway;

import static org.assertj.core.api.Assertions.assertThat;

import jakarta.servlet.http.HttpServletRequest;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

class RequestIdFilterTest {
    GatewayApplication.RequestIdFilter filter = new GatewayApplication.RequestIdFilter();

    String run(String incoming, MockHttpServletResponse res) throws Exception {
        MockHttpServletRequest req = new MockHttpServletRequest("GET", "/api/v1/incidents");
        if (incoming != null) req.addHeader("X-Request-ID", incoming);
        AtomicReference<String> downstream = new AtomicReference<>();
        filter.doFilter(req, res, (rq, rs) -> downstream.set(((HttpServletRequest) rq).getHeader("X-Request-ID")));
        return downstream.get();
    }

    @Test
    void keepsSafeIncomingId() throws Exception {
        var res = new MockHttpServletResponse();
        assertThat(run("abc-123", res)).isEqualTo("abc-123");
        assertThat(res.getHeader("X-Request-ID")).isEqualTo("abc-123");
    }

    @Test
    void replacesMissingOrUnsafeId() throws Exception {
        var res = new MockHttpServletResponse();
        String id = run("bad id <script>", res);
        assertThat(id).matches("[a-f0-9]{32}").isEqualTo(res.getHeader("X-Request-ID"));
        assertThat(run(null, new MockHttpServletResponse())).matches("[a-f0-9]{32}");
    }
}
