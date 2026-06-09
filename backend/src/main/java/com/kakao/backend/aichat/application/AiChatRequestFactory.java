package com.kakao.backend.aichat.application;

import com.kakao.backend.aichat.dto.AiChatContextPayload;
import com.kakao.backend.aichat.dto.AiChatRequestMessage;
import com.kakao.backend.aichat.dto.AiChatUserProfilePayload;
import com.kakao.backend.aichat.dto.AiRecentMessagePayload;
import com.kakao.backend.domain.ChatMessage;
import com.kakao.backend.domain.StartupProfile;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

@Component
public class AiChatRequestFactory {

    public AiChatRequestMessage create(AiChatDispatchCommand command) {
        return new AiChatRequestMessage(
                command.requestId(),
                command.workspace() != null ? command.workspace().getId() : null,
                command.room() != null ? command.room().getId() : null,
                command.message() != null ? command.message().getId() : null,
                command.user() != null ? command.user().getId() : null,
                command.room() != null ? command.room().getRoomType() : null,
                command.room() != null ? command.room().getTargetFeature() : null,
                command.sessionType(),
                command.intent(),
                command.message() != null ? command.message().getContent() : null,
                toProfile(command.startupProfile()),
                toContext(command)
        );
    }

    private AiChatUserProfilePayload toProfile(StartupProfile profile) {
        if (profile == null) {
            return new AiChatUserProfilePayload(
                    null,
                    List.of(),
                    null,
                    null,
                    List.of(),
                    List.of(),
                    "예비창업",
                    "medium",
                    null
            );
        }

        return new AiChatUserProfilePayload(
                profile.getMajor(),
                merge(split(profile.getCareer()), split(profile.getStrengthTags())),
                firstNonBlank(profile.getBusinessRegion(), profile.getResidenceRegion()),
                profile.getInitialBudget(),
                split(profile.getInterestField()),
                split(profile.getPreferredBusinessType()),
                "예비창업",
                "medium",
                profile.getDiagnosisSummary()
        );
    }

    private AiChatContextPayload toContext(AiChatDispatchCommand command) {
        List<AiRecentMessagePayload> recentMessages = command.recentMessages() == null
                ? List.of()
                : command.recentMessages().stream()
                        .map(this::toRecentMessage)
                        .toList();

        Map<String, Object> currentResult = command.currentResult() == null
                ? Map.of()
                : command.currentResult();

        List<String> candidateAgents = command.candidateAgents() == null
                ? List.of()
                : List.copyOf(command.candidateAgents());

        return new AiChatContextPayload(
                command.currentResultType(),
                command.currentResultId(),
                command.selectedIdeaId(),
                recentMessages,
                currentResult,
                candidateAgents
        );
    }

    private AiRecentMessagePayload toRecentMessage(ChatMessage message) {
        return new AiRecentMessagePayload(
                message.getId(),
                message.getSenderType(),
                message.getUser() != null ? message.getUser().getId() : null,
                message.getAgent() != null ? message.getAgent().getId() : null,
                message.getContent()
        );
    }

    private List<String> split(String raw) {
        if (raw == null || raw.isBlank()) {
            return List.of();
        }

        List<String> parts = new ArrayList<>();
        for (String token : raw.split("[,/]")) {
            String trimmed = token.trim();
            if (!trimmed.isEmpty()) {
                parts.add(trimmed);
            }
        }
        return parts;
    }

    private List<String> merge(List<String> first, List<String> second) {
        if (first.isEmpty() && second.isEmpty()) {
            return List.of();
        }
        List<String> merged = new ArrayList<>(first);
        for (String item : second) {
            if (!merged.contains(item)) {
                merged.add(item);
            }
        }
        return Collections.unmodifiableList(merged);
    }

    private String firstNonBlank(String primary, String fallback) {
        if (primary != null && !primary.isBlank()) {
            return primary;
        }
        if (fallback != null && !fallback.isBlank()) {
            return fallback;
        }
        return null;
    }
}
