package com.kakao.backend.startupProfile.dto;

import com.kakao.backend.startupProfile.model.StartupProfile;
import org.springframework.web.util.HtmlUtils;

// 저장된 창업 프로필 정보를 프론트에서 사용할 수 있는 형태로 전달합니다.
public record StartupProfileResponse(
        Long id,
        String stage,
        String stageLabel,
        String major,
        String career,
        String interestField,
        String residenceRegion,
        String businessRegion,
        Integer initialBudget,
        String teamStatus,
        String teamStatusLabel,
        String preferredBusinessType,
        String preferredBusinessTypeLabel,
        String strengthTags,
        String currentItemName,
        String currentIndustry,
        String operatingPeriod,
        String operatingPeriodLabel,
        Integer suitabilityScore,
        String diagnosisSummary
) {

    // 엔티티 값을 응답 DTO로 변환하면서 문자열은 HTML escape 처리합니다.
    public static StartupProfileResponse from(StartupProfile profile) {
        return new StartupProfileResponse(
                profile.getId(),
                profile.getStage() == null ? null : profile.getStage().getCode(),
                profile.getStage() == null ? null : profile.getStage().getLabel(),
                escape(profile.getMajor()),
                escape(profile.getCareer()),
                escape(profile.getInterestField()),
                escape(profile.getResidenceRegion()),
                escape(profile.getBusinessRegion()),
                profile.getInitialBudget(),
                profile.getTeamStatus() == null ? null : profile.getTeamStatus().getCode(),
                profile.getTeamStatus() == null ? null : profile.getTeamStatus().getLabel(),
                profile.getPreferredBusinessType() == null ? null : profile.getPreferredBusinessType().getCode(),
                profile.getPreferredBusinessType() == null ? null : profile.getPreferredBusinessType().getLabel(),
                escape(profile.getStrengthTags()),
                escape(profile.getCurrentItemName()),
                escape(profile.getCurrentIndustry()),
                profile.getOperatingPeriod() == null ? null : profile.getOperatingPeriod().getCode(),
                profile.getOperatingPeriod() == null ? null : profile.getOperatingPeriod().getLabel(),
                profile.getSuitabilityScore(),
                escape(profile.getDiagnosisSummary()));
    }

    private static String escape(String value) {
        return value == null ? null : HtmlUtils.htmlEscape(value);
    }
}
