package com.esmhub.common.web;

import org.springframework.http.HttpStatus;

public class ForbiddenException extends EsmException {
    public ForbiddenException(String detail) { super(HttpStatus.FORBIDDEN, "Forbidden", detail); }
}
