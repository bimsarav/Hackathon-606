package com.esmhub.common.web;

import org.springframework.http.HttpStatus;

/** 404. Also used for records of another company, so existence is not leaked. */
public class NotFoundException extends EsmException {
    public NotFoundException(String detail) { super(HttpStatus.NOT_FOUND, "Not found", detail); }
    public static NotFoundException of(String what, Object id) { return new NotFoundException(what + " " + id + " not found."); }
}
