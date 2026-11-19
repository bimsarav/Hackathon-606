package com.esmhub.gateway;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletRequestWrapper;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.Collections;
import java.util.Enumeration;
import java.util.UUID;
import java.util.regex.Pattern;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.core.Ordered;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Edge router: forwards /api/v1/** to the owning service (routes in application.yml). Authentication is enforced by
 * each service (JWT resource server); the gateway only guarantees an X-Request-ID on every request and response.
 */
@SpringBootApplication
public class GatewayApplication {
    public static void main(String[] args) {
        SpringApplication.run(GatewayApplication.class, args);
    }

    @Bean
    FilterRegistrationBean<RequestIdFilter> requestIdFilter() {
        FilterRegistrationBean<RequestIdFilter> reg = new FilterRegistrationBean<>(new RequestIdFilter());
        reg.setOrder(Ordered.HIGHEST_PRECEDENCE);
        return reg;
    }

    /** Ensures a safe X-Request-ID, passes it downstream and echoes it to the client. */
    static final class RequestIdFilter extends OncePerRequestFilter {
        static final String HEADER = "X-Request-ID";
        private static final Pattern SAFE = Pattern.compile("^[A-Za-z0-9._-]{1,64}$");

        @Override
        protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
                throws ServletException, IOException {
            String incoming = req.getHeader(HEADER);
            String id = incoming != null && SAFE.matcher(incoming).matches() ? incoming : UUID.randomUUID().toString().replace("-", "");
            res.setHeader(HEADER, id);
            chain.doFilter(new HttpServletRequestWrapper(req) {
                @Override public String getHeader(String name) { return HEADER.equalsIgnoreCase(name) ? id : super.getHeader(name); }
                @Override public Enumeration<String> getHeaders(String name) {
                    return HEADER.equalsIgnoreCase(name) ? Collections.enumeration(java.util.List.of(id)) : super.getHeaders(name);
                }
                @Override public Enumeration<String> getHeaderNames() {
                    java.util.List<String> names = Collections.list(super.getHeaderNames());
                    if (names.stream().noneMatch(HEADER::equalsIgnoreCase)) names.add(HEADER);
                    return Collections.enumeration(names);
                }
            }, res);
        }
    }
}
