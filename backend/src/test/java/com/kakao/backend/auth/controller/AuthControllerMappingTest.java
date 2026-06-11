package com.kakao.backend.auth.controller;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.web.servlet.mvc.method.annotation.RequestMappingHandlerMapping;

@SpringBootTest
class AuthControllerMappingTest {

    @Autowired
    private RequestMappingHandlerMapping handlerMapping;

    @Test
    void registersAuthLoginAndSignupRoutes() {
        String mappings = handlerMapping.getHandlerMethods().keySet().toString();

        assertThat(mappings).contains("/auth/login");
        assertThat(mappings).contains("/auth/signup");
    }
}
