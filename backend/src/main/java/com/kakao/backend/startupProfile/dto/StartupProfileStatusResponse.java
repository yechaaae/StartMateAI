package com.kakao.backend.startupProfile.dto;

import java.util.List;

// 로그인한 사용자가 온보딩 프로필을 입력해야 하는지 알려줍니다.
public record StartupProfileStatusResponse(
        boolean profileExists,
        boolean profileCompleted,
        boolean requiresOnboarding,
        List<String> missingFields
) {

    public static StartupProfileStatusResponse of(boolean profileExists, List<String> missingFields) {
        boolean profileCompleted = missingFields.isEmpty();
        return new StartupProfileStatusResponse(
                profileExists,
                profileCompleted,
                !profileCompleted,
                missingFields);
    }
}
