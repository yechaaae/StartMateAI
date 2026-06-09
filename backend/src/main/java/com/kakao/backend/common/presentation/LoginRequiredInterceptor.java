package com.kakao.backend.common.presentation;

import com.kakao.backend.auth.service.AuthSession;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import java.io.IOException;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

@Component
// 보호된 API 요청 전에 로그인 세션이 있는지 확인합니다.
public class LoginRequiredInterceptor implements HandlerInterceptor {

    @Override
    public boolean preHandle(
            HttpServletRequest request,
            HttpServletResponse response,
            Object handler
    ) throws IOException {
        // 브라우저의 CORS 사전 요청은 로그인 검사 없이 통과시킵니다.
        if (HttpMethod.OPTIONS.matches(request.getMethod())) {
            return true;
        }

        HttpSession session = request.getSession(false);
        if (session != null && session.getAttribute(AuthSession.LOGIN_USER_ID) != null) {
            return true;
        }

        // 로그인 세션이 없으면 공통 JSON 에러 응답을 내려줍니다.
        response.setStatus(HttpStatus.UNAUTHORIZED.value());
        response.setHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE);
        response.getWriter().write("{\"message\":\"로그인이 필요합니다.\"}");
        return false;
    }
}
