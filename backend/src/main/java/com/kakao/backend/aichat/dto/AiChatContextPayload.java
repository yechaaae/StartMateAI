package com.kakao.backend.aichat.dto;

import java.util.List;
import java.util.Map;

public record AiChatContextPayload(
        String currentResultType,
        Long currentResultId,
        Long selectedIdeaId,
        List<AiRecentMessagePayload> recentMessages,
        Map<String, Object> currentResult,
        List<String> candidateAgents
) {
}
