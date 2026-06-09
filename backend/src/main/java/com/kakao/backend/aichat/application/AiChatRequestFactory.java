package com.kakao.backend.aichat.application;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.kakao.backend.aichat.dto.AiChatRequestMessage;
import com.kakao.backend.aichat.dto.AiChatUserProfilePayload;
import com.kakao.backend.aichat.dto.AiRecentMessagePayload;
import com.kakao.backend.chat.domain.ChatMessage;
import com.kakao.backend.startupProfile.model.StartupProfile;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

@Component
public class AiChatRequestFactory {

    private final ObjectMapper objectMapper;

    public AiChatRequestFactory(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public AiChatRequestMessage create(AiChatDispatchCommand command) {
        return new AiChatRequestMessage(
                "v1",
                "CHAT_REQUEST",
                command.requestId(),
                command.workspace() != null ? command.workspace().getId() : null,
                command.room() != null ? command.room().getId() : null,
                command.message() != null ? command.message().getId() : null,
                command.user() != null ? command.user().getId() : null,
                command.room() != null ? command.room().getRoomType() : null,
                command.room() != null ? command.room().getTargetFeature() : null,
                command.sessionType(),
                command.intent(),
                toPayload(command)
        );
    }

    private ObjectNode toPayload(AiChatDispatchCommand command) {
        ObjectNode payload = objectMapper.createObjectNode();

        ObjectNode common = payload.putObject("common");
        putText(common, "message", command.message() != null ? command.message().getContent() : null);
        putText(common, "metadata", command.message() != null ? command.message().getMetadata() : null);

        payload.set("profile", objectMapper.valueToTree(toProfile(command.startupProfile())));

        ObjectNode conversation = payload.putObject("conversation");
        putText(conversation, "roomType", command.room() != null ? command.room().getRoomType() : null);
        putText(conversation, "targetFeature", command.room() != null ? command.room().getTargetFeature() : null);
        conversation.set("recentMessages", objectMapper.valueToTree(toRecentMessages(command)));

        ObjectNode resultContext = payload.putObject("resultContext");
        putText(resultContext, "currentResultType", command.currentResultType());
        putLong(resultContext, "currentResultId", command.currentResultId());
        putLong(resultContext, "selectedIdeaId", command.selectedIdeaId());
        resultContext.set("currentResult", objectMapper.valueToTree(command.currentResult() == null ? Map.of() : command.currentResult()));

        ObjectNode options = payload.putObject("options");
        options.set("candidateAgents", objectMapper.valueToTree(
                command.candidateAgents() == null ? List.of() : command.candidateAgents()
        ));
        putText(options, "sessionType", command.sessionType());
        putText(options, "intent", command.intent());

        if (command.referenceData() != null && !command.referenceData().isEmpty()) {
            payload.set("reference", objectMapper.valueToTree(command.referenceData()));
        }

        return payload;
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
                profile.getPreferredBusinessType() == null
                        ? List.of()
                        : List.of(profile.getPreferredBusinessType().getLabel()),
                "예비창업",
                "medium",
                profile.getDiagnosisSummary()
        );
    }

    private List<AiRecentMessagePayload> toRecentMessages(AiChatDispatchCommand command) {
        return command.recentMessages() == null
                ? List.of()
                : command.recentMessages().stream()
                        .map(this::toRecentMessage)
                        .toList();
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

    private void putText(ObjectNode node, String fieldName, String value) {
        if (value != null && !value.isBlank()) {
            node.put(fieldName, value);
        }
    }

    private void putLong(ObjectNode node, String fieldName, Long value) {
        if (value != null) {
            node.put(fieldName, value);
        }
    }
}
