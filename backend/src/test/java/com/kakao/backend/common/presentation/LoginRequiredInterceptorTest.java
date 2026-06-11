package com.kakao.backend.common.presentation;

import static org.assertj.core.api.Assertions.assertThat;

import jakarta.servlet.DispatcherType;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

class LoginRequiredInterceptorTest {

    private final LoginRequiredInterceptor interceptor = new LoginRequiredInterceptor();

    @Test
    void loginAndSignupRequestsPassWithoutSession() throws Exception {
        assertThat(preHandle(HttpMethod.POST, "/api/auth/login")).isTrue();
        assertThat(preHandle(HttpMethod.POST, "/api/auth/signup")).isTrue();
    }

    @Test
    void publicAuthRequestsPassWhenContextPathIsRoot() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest(HttpMethod.POST.name(), "/api/auth/login");
        request.setContextPath("/");
        MockHttpServletResponse response = new MockHttpServletResponse();

        assertThat(interceptor.preHandle(request, response, new Object())).isTrue();
    }

    @Test
    void errorDispatchPassesWithoutOverwritingOriginalError() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest(HttpMethod.GET.name(), "/api/error");
        request.setDispatcherType(DispatcherType.ERROR);
        MockHttpServletResponse response = new MockHttpServletResponse();

        assertThat(interceptor.preHandle(request, response, new Object())).isTrue();
    }

    @Test
    void protectedApiRequiresLoginSession() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest(HttpMethod.GET.name(), "/api/profile");
        MockHttpServletResponse response = new MockHttpServletResponse();

        boolean result = interceptor.preHandle(request, response, new Object());

        assertThat(result).isFalse();
        assertThat(response.getStatus()).isEqualTo(HttpStatus.UNAUTHORIZED.value());
        assertThat(response.getContentAsString()).contains("로그인이 필요합니다.");
    }

    private boolean preHandle(HttpMethod method, String path) throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest(method.name(), path);
        MockHttpServletResponse response = new MockHttpServletResponse();

        return interceptor.preHandle(request, response, new Object());
    }
}
