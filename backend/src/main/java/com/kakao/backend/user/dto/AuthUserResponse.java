package com.kakao.backend.user.dto;

import com.kakao.backend.user.model.User;
import org.springframework.web.util.HtmlUtils;

// 인증 API 응답에서 비밀번호를 제외한 사용자 기본 정보만 전달합니다.
public record AuthUserResponse(
        Long id,
        String email,
        String nickname,
        String role
) {

    // 엔티티를 외부 응답 형태로 변환합니다.
    public static AuthUserResponse from(User user) {
        return new AuthUserResponse(
                user.getId(),
                escape(user.getEmail()),
                escape(user.getNickname()),
                escape(user.getRole()));
    }

    private static String escape(String value) {
        return value == null ? null : HtmlUtils.htmlEscape(value);
    }
}
