package com.kakao.backend.user.dto;

// 로그인 요청에 필요한 이메일과 비밀번호를 받습니다.
public record LoginRequest(
        String email,
        String password
) {
}
