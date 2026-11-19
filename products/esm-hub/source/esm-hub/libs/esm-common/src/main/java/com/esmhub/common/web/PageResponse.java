package com.esmhub.common.web;

import java.util.List;
import java.util.function.Function;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;

/** Standard list envelope: {items,total,page,size} with 1-based page numbers. */
public record PageResponse<T>(List<T> items, long total, int page, int size) {
    public static final int MAX_SIZE = 200;

    public static <E, T> PageResponse<T> of(Page<E> page, Function<E, T> mapper) {
        return new PageResponse<>(page.getContent().stream().map(mapper).toList(), page.getTotalElements(),
                page.getNumber() + 1, page.getSize());
    }

    /** Validates 1-based page and size (1..200) and builds a Pageable. */
    public static Pageable pageable(int page, int size, Sort sort) {
        if (page < 1 || size < 1 || size > MAX_SIZE) {
            throw new BusinessRuleException("page must be ≥ 1 and size between 1 and " + MAX_SIZE + ".");
        }
        return PageRequest.of(page - 1, size, sort);
    }
}
