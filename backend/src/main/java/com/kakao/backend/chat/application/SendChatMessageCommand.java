package com.kakao.backend.chat.application;

import java.util.List;
import java.util.Map;

public record SendChatMessageCommand(
        Long roomId,
        Long userId,
        String content,
        String metadata,
        String intent,
        String sessionType,
        String currentResultType,
        Long currentResultId,
        Long selectedIdeaId,
        List<String> candidateAgents,
        Map<String, Object> currentResult
) {
}
