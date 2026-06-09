package com.kakao.backend.user.controller;

import com.kakao.backend.user.dto.AuthUserResponse;
import com.kakao.backend.user.dto.LoginRequest;
import com.kakao.backend.user.dto.SignupRequest;
import com.kakao.backend.user.service.AuthException;
import com.kakao.backend.user.service.AuthService;
import com.kakao.backend.user.service.AuthSession;
import jakarta.servlet.http.HttpSession;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/auth")
@RequiredArgsConstructor
// 회원가입, 로그인, 로그아웃처럼 인증과 직접 연결된 API를 담당합니다.
public class AuthController {

    private final AuthService authService;

    // 신규 사용자를 생성하고 바로 로그인 세션을 저장합니다.
    @PostMapping("/signup")
    public ResponseEntity<AuthUserResponse> signup(
            @RequestBody SignupRequest request,
            HttpSession session
    ) {
        AuthUserResponse response = authService.signup(request);
        session.setAttribute(AuthSession.LOGIN_USER_ID, response.id());
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    // 이메일과 비밀번호를 확인한 뒤 로그인 세션을 저장합니다.
    @PostMapping("/login")
    public AuthUserResponse login(
            @RequestBody LoginRequest request,
            HttpSession session
    ) {
        AuthUserResponse response = authService.login(request);
        session.setAttribute(AuthSession.LOGIN_USER_ID, response.id());
        return response;
    }

    // 현재 브라우저에 연결된 서버 세션을 만료시킵니다.
    @PostMapping("/logout")
    public ResponseEntity<Void> logout(HttpSession session) {
        session.invalidate();
        return ResponseEntity.noContent().build();
    }

    // 저장된 세션을 기준으로 현재 로그인한 사용자 정보를 반환합니다.
    @GetMapping("/me")
    public AuthUserResponse me(HttpSession session) {
        Object userId = session.getAttribute(AuthSession.LOGIN_USER_ID);
        if (!(userId instanceof Long id)) {
            throw new AuthException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다.");
        }
        return authService.getCurrentUser(id);
    }
}
