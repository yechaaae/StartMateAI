package com.kakao.backend.common.presentation;

import com.kakao.backend.auth.service.AuthException;
import com.kakao.backend.auth.service.AuthSession;
import jakarta.servlet.http.HttpSession;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;

@Component
public class LoginUserSessionResolver {

    public Long resolve(HttpSession session) {
        Object userId = session.getAttribute(AuthSession.LOGIN_USER_ID);
        if (!(userId instanceof Long id)) {
            throw new AuthException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다.");
        }
        return id;
    }
}
