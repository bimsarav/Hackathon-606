package com.esmhub.common.web;

import org.springframework.http.HttpStatus;

/** 422: the request is well-formed but violates a business rule or workflow transition. */
public class BusinessRuleException extends EsmException {
    public BusinessRuleException(String detail) { super(HttpStatus.UNPROCESSABLE_CONTENT, "Business rule violated", detail); }
}
