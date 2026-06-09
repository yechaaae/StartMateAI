package com.kakao.backend.user.dto;

import com.fasterxml.jackson.annotation.JsonAlias;

// 회원가입 요청에 필요한 계정 정보와 닉네임을 받습니다.
public record SignupRequest(
        String email,
        String password,
        @JsonAlias({"confirmPassword", "passwordConfirmation"})
        String passwordConfirm,
        String nickname
) {
}
