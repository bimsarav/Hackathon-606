package com.esmhub.common.web;

import org.springframework.http.HttpStatus;

/** Base type for expected business errors. Mapped to RFC 9457 problem+json by {@link GlobalExceptionHandler}. */
public abstract class EsmException extends RuntimeException {
    private final HttpStatus status;
    private final String title;

    protected EsmException(HttpStatus status, String title, String detail) {
        super(detail);
        this.status = status;
        this.title = title;
    }

    public HttpStatus status() { return status; }
    public String title() { return title; }
}
