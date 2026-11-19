package com.esmhub.common.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import org.slf4j.MDC;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.convert.converter.Converter;
import org.springframework.security.authentication.AbstractAuthenticationToken;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.security.oauth2.server.resource.web.authentication.BearerTokenAuthenticationFilter;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.web.filter.OncePerRequestFilter;
import tools.jackson.databind.json.JsonMapper;

/** Deny-by-default JWT resource server shared by all services. A service may define its own SecurityFilterChain. */
@Configuration(proxyBeanMethods = false)
@EnableWebSecurity
@EnableConfigurationProperties(EsmSecurityProperties.class)
public class EsmSecurityConfiguration {

    public static final String[] ALWAYS_PUBLIC = {"/actuator/health/**", "/actuator/info", "/actuator/prometheus",
            "/v3/api-docs/**", "/swagger-ui/**", "/swagger-ui.html", "/error"};

    @Bean
    @ConditionalOnMissingBean(SecurityFilterChain.class)
    SecurityFilterChain esmSecurityFilterChain(HttpSecurity http, EsmSecurityProperties props, JsonMapper mapper) throws Exception {
        List<String> open = new ArrayList<>(List.of(ALWAYS_PUBLIC));
        open.addAll(props.publicPaths());
        http.csrf(c -> c.disable())
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(a -> a.requestMatchers(open.toArray(String[]::new)).permitAll()
                        .anyRequest().authenticated())
                .oauth2ResourceServer(o -> o.jwt(j -> j.jwtAuthenticationConverter(jwtConverter()))
                        .authenticationEntryPoint(ProblemAuthHandlers.entryPoint(mapper)))
                .exceptionHandling(e -> e.authenticationEntryPoint(ProblemAuthHandlers.entryPoint(mapper))
                        .accessDeniedHandler(ProblemAuthHandlers.deniedHandler(mapper)))
                .addFilterAfter(new UserMdcFilter(), BearerTokenAuthenticationFilter.class);
        return http.build();
    }

    /** Claim {@code roles} → authorities {@code ROLE_<name>}. */
    public static Converter<Jwt, AbstractAuthenticationToken> jwtConverter() {
        return jwt -> {
            List<GrantedAuthority> auth = CurrentUserProvider.strings(jwt.getClaim("roles")).stream()
                    .map(r -> (GrantedAuthority) new SimpleGrantedAuthority("ROLE_" + r)).toList();
            return new JwtAuthenticationToken(jwt, auth, jwt.getSubject());
        };
    }

    /** Puts the authenticated user id into the MDC for structured logs. */
    static final class UserMdcFilter extends OncePerRequestFilter {
        @Override
        protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
                throws ServletException, IOException {
            if (SecurityContextHolder.getContext().getAuthentication() instanceof JwtAuthenticationToken t) {
                MDC.put("userId", t.getName());
            }
            chain.doFilter(req, res);
        }
    }
}
