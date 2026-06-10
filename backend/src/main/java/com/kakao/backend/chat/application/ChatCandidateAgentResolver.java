package com.kakao.backend.chat.application;

import com.kakao.backend.chat.domain.ChatRoom;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import org.springframework.stereotype.Service;

@Service
public class ChatCandidateAgentResolver {

    private static final List<String> FREE_CHAT_AGENTS = List.of(
            "ProfileAgent",
            "IdeaAgent",
            "FinanceAgent",
            "PolicyAgent",
            "PlanAgent",
            "OperationAgent",
            "MarketingAgent"
    );

    public List<String> resolve(String sessionType, ChatRoom room, List<String> requestedAgents) {
        List<String> normalizedRequested = normalize(requestedAgents);
        if (!normalizedRequested.isEmpty()) {
            return normalizedRequested;
        }

        String normalizedSessionType = normalizeText(sessionType);
        String targetFeature = room == null ? null : normalizeText(room.getTargetFeature());

        if ("FREE_CHAT".equals(normalizedSessionType)) {
            return FREE_CHAT_AGENTS;
        }

        if ("FEATURE_CHAT".equals(normalizedSessionType)) {
            return switch (targetFeature) {
                case "ITEM" -> List.of("IdeaAgent", "ProfileAgent", "FinanceAgent");
                case "SIMULATOR" -> List.of("FinanceAgent", "IdeaAgent");
                case "SUPPORT" -> List.of("PolicyAgent", "PlanAgent");
                case "PLAN" -> List.of("PlanAgent", "IdeaAgent", "PolicyAgent");
                case "OPERATION" -> List.of("OperationAgent", "FinanceAgent");
                case "SNS" -> List.of("MarketingAgent", "ProfileAgent");
                default -> List.of("ProfileAgent");
            };
        }

        return targetFeature == null || targetFeature.isBlank()
                ? FREE_CHAT_AGENTS
                : List.of("ProfileAgent");
    }

    private List<String> normalize(List<String> requestedAgents) {
        if (requestedAgents == null || requestedAgents.isEmpty()) {
            return List.of();
        }

        Set<String> ordered = new LinkedHashSet<>();
        for (String agent : requestedAgents) {
            String normalized = normalizeText(agent);
            if (normalized != null && !normalized.isBlank()) {
                ordered.add(agent.trim());
            }
        }
        return List.copyOf(ordered);
    }

    private String normalizeText(String value) {
        if (value == null) {
            return null;
        }
        String normalized = value.trim();
        return normalized.isBlank() ? null : normalized.toUpperCase();
    }
}
