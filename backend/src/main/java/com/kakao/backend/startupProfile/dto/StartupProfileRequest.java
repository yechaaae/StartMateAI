package com.kakao.backend.startupProfile.dto;

import com.kakao.backend.startupProfile.model.PreferredBusinessType;
import com.kakao.backend.startupProfile.model.TeamStatus;

// 온보딩에서 사용자의 창업 준비 정보와 선호 조건을 입력받습니다.
public record StartupProfileRequest(
        String major,
        String career,
        String interestField,
        String residenceRegion,
        String businessRegion,
        Integer initialBudget,
        TeamStatus teamStatus,
        PreferredBusinessType preferredBusinessType,
        String strengthTags
) {
}
