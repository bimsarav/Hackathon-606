package com.esmhub.common.web;

import org.springframework.http.HttpStatus;

public class ConflictException extends EsmException {
    public ConflictException(String detail) { super(HttpStatus.CONFLICT, "Conflict", detail); }
}
