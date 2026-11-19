package com.esmhub.common.security;

import org.springframework.core.MethodParameter;
import org.springframework.web.bind.support.WebDataBinderFactory;
import org.springframework.web.context.request.NativeWebRequest;
import org.springframework.web.method.support.HandlerMethodArgumentResolver;
import org.springframework.web.method.support.ModelAndViewContainer;

/** Lets controllers declare a {@link CurrentUser} parameter. */
public class CurrentUserArgumentResolver implements HandlerMethodArgumentResolver {
    private final CurrentUserProvider provider;

    public CurrentUserArgumentResolver(CurrentUserProvider provider) { this.provider = provider; }

    @Override
    public boolean supportsParameter(MethodParameter parameter) {
        return CurrentUser.class.equals(parameter.getParameterType());
    }

    @Override
    public Object resolveArgument(MethodParameter parameter, ModelAndViewContainer mav, NativeWebRequest req,
                                  WebDataBinderFactory binder) {
        return provider.get();
    }
}
