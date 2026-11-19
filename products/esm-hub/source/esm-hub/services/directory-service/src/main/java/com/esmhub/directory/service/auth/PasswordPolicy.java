package com.esmhub.directory.service.auth;

import com.esmhub.common.web.BusinessRuleException;
import java.nio.charset.StandardCharsets;

/** 12–72 bytes (bcrypt limit), upper and lower case and a digit. */
public final class PasswordPolicy {
    private PasswordPolicy() {}

    public static void check(String raw) {
        if (raw == null || raw.length() < 12 || raw.equals(raw.toLowerCase()) || raw.equals(raw.toUpperCase())
                || raw.chars().noneMatch(Character::isDigit)) {
            throw new BusinessRuleException("Password must be at least 12 characters with upper and lower case letters and a digit.");
        }
        if (raw.getBytes(StandardCharsets.UTF_8).length > 72) {
            throw new BusinessRuleException("Password must be at most 72 bytes.");
        }
    }
}
