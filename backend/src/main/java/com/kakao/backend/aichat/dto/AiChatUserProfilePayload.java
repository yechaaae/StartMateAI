package com.kakao.backend.aichat.dto;

import java.util.List;

public record AiChatUserProfilePayload(
        String major,
        List<String> experiences,
        String region,
        Integer budgetKrw,
        List<String> interests,
        List<String> preferredChannels,
        String startupStage,
        String riskTolerance,
        String memo
) {
}
