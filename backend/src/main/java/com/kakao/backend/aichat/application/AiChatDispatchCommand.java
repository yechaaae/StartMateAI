package com.kakao.backend.aichat.application;

import com.kakao.backend.chat.domain.ChatMessage;
import com.kakao.backend.chat.domain.ChatRoom;
import com.kakao.backend.user.domain.StartupProfile;
import com.kakao.backend.user.domain.User;
import com.kakao.backend.workspace.domain.Workspace;
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
        Map<String, Object> currentResult,
        Map<String, Object> referenceData
) {
}
