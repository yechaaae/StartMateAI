package com.kakao.backend.startupProfile.dto;

import com.kakao.backend.startupProfile.model.OperatingPeriod;
import com.kakao.backend.startupProfile.model.PreferredBusinessType;
import com.kakao.backend.startupProfile.model.StartupStage;
import com.kakao.backend.startupProfile.model.TeamStatus;

// 온보딩에서 사용자의 창업 준비 정보와 선호 조건을 입력받습니다.
// 창업 전이면 initialBudget을, 창업 후이면 현재 아이템 정보(currentItemName/currentIndustry/operatingPeriod)를 함께 받습니다.
public record StartupProfileRequest(
        StartupStage stage,
        String major,
        String career,
        String interestField,
        String residenceRegion,
        String businessRegion,
        Integer initialBudget,
        TeamStatus teamStatus,
        PreferredBusinessType preferredBusinessType,
        String strengthTags,
        String currentItemName,
        String currentIndustry,
        OperatingPeriod operatingPeriod
) {
}
