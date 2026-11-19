package com.esmhub.common.security;

import com.esmhub.common.web.GlobalExceptionHandler;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.security.web.AuthenticationEntryPoint;
import org.springframework.security.web.access.AccessDeniedHandler;
import tools.jackson.databind.json.JsonMapper;

/** 401/403 from the security filter chain as problem+json. */
public final class ProblemAuthHandlers {
    private ProblemAuthHandlers() {}

    public static AuthenticationEntryPoint entryPoint(JsonMapper mapper) {
        return (req, res, ex) -> write(res, mapper, GlobalExceptionHandler.problem(HttpStatus.UNAUTHORIZED,
                "Unauthorized", "Missing, invalid or expired token."));
    }

    public static AccessDeniedHandler deniedHandler(JsonMapper mapper) {
        return (req, res, ex) -> write(res, mapper, GlobalExceptionHandler.problem(HttpStatus.FORBIDDEN,
                "Forbidden", "Your role does not allow this action."));
    }

    private static void write(HttpServletResponse res, JsonMapper mapper, ProblemDetail pd) throws IOException {
        res.setStatus(pd.getStatus());
        res.setContentType("application/problem+json");
        res.getWriter().write(mapper.writeValueAsString(pd));
    }
}
