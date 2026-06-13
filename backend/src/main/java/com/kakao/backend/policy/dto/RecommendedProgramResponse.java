package com.kakao.backend.policy.dto;

import java.time.LocalDate;
import java.util.List;

public record RecommendedProgramResponse(
        Long programId,
        String title,
        String source,
        String summary,
        String regionCondition,
        String supportAmount,
        String requiredDocuments,
        String organization,
        String supportType,
        String status,
        int matchScore,
        List<String> matchReasons,
        List<String> cautionReasons,
        LocalDate applicationEndDate,
        String applyUrl
) {
}
