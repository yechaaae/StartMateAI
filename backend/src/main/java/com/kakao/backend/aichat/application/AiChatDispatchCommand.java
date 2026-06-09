package com.kakao.backend.aichat.application;

import com.kakao.backend.domain.ChatMessage;
import com.kakao.backend.domain.ChatRoom;
import com.kakao.backend.domain.StartupProfile;
import com.kakao.backend.domain.User;
import com.kakao.backend.domain.Workspace;
import java.util.List;
import java.util.Map;

public record AiChatDispatchCommand(
        String requestId,
        Workspace workspace,
        ChatRoom room,
        User user,
        StartupProfile startupProfile,
        ChatMessage message,
        String intent,
        String sessionType,
        String currentResultType,
        Long currentResultId,
        Long selectedIdeaId,
        List<String> candidateAgents,
        List<ChatMessage> recentMessages,
        Map<String, Object> currentResult
) {
}
