package com.kakao.backend.policy.dto;

import java.time.LocalDate;
import java.util.List;

public record SupportProgramRecommendationRequest(
        Integer age,
        String residenceSido,
        String desiredSido,
        String desiredSigungu,
        String founderType,
        Boolean businessRegistered,
        LocalDate businessStartDate,
        String businessStage,
        String industryLarge,
        String industryMedium,
        String industrySmall,
        Long requiredFundingAmount,
        List<String> interestedSupportTypes
) {
}
