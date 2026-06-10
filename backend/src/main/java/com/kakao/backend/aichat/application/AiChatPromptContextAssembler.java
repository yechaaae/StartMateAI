package com.kakao.backend.aichat.application;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.kakao.backend.aichat.dto.AiChatUserProfilePayload;
import com.kakao.backend.aichat.dto.AiRecentMessagePayload;
import com.kakao.backend.chat.domain.ChatMessage;
import com.kakao.backend.startupProfile.model.StartupProfile;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

@Component
public class AiChatPromptContextAssembler {

    private final ObjectMapper objectMapper;
    private final AiChatFeaturePayloadResolver featurePayloadResolver;

    public AiChatPromptContextAssembler(
            ObjectMapper objectMapper,
            AiChatFeaturePayloadResolver featurePayloadResolver
    ) {
        this.objectMapper = objectMapper;
        this.featurePayloadResolver = featurePayloadResolver;
    }

    public Map<String, Object> assemble(AiChatDispatchCommand command) {
        Map<String, Object> payload = new LinkedHashMap<>();

        Map<String, Object> common = new LinkedHashMap<>();
        putText(common, "message", command.message() != null ? command.message().getContent() : null);
        putText(common, "metadata", command.message() != null ? command.message().getMetadata() : null);
        payload.put("common", common);

        payload.put("profile", objectMapper.convertValue(toProfile(command.startupProfile()), Map.class));

        Map<String, Object> conversation = new LinkedHashMap<>();
        putText(conversation, "roomType", command.room() != null ? command.room().getRoomType() : null);
        putText(conversation, "targetFeature", command.room() != null ? command.room().getTargetFeature() : null);
        putText(conversation, "sessionType", command.sessionType());
        conversation.put("recentMessages", objectMapper.convertValue(toRecentMessages(command), List.class));
        payload.put("conversation", conversation);

        Map<String, Object> resultContext = new LinkedHashMap<>();
        putText(resultContext, "currentResultType", command.currentResultType());
        putLong(resultContext, "currentResultId", command.currentResultId());
        putLong(resultContext, "selectedIdeaId", command.selectedIdeaId());
        resultContext.put("currentResult", command.currentResult() == null ? Map.of() : command.currentResult());
        payload.put("resultContext", resultContext);

        Map<String, Object> options = new LinkedHashMap<>();
        options.put("candidateAgents", command.candidateAgents() == null ? List.of() : command.candidateAgents());
        putText(options, "sessionType", command.sessionType());
        putText(options, "intent", command.intent());
        payload.put("options", options);

        payload.put("featureContext", buildFeatureContext(command));

        if (command.referenceData() != null && !command.referenceData().isEmpty()) {
            payload.put("reference", command.referenceData());
        }

        return payload;
    }

    private Map<String, Object> buildFeatureContext(AiChatDispatchCommand command) {
        Map<String, Object> featureContext = new LinkedHashMap<>(featurePayloadResolver.resolve(
                command.room() != null ? command.room().getTargetFeature() : null,
                command.currentResultType(),
                command.currentResultId(),
                command.selectedIdeaId(),
                command.currentResult()
        ));
        putText(featureContext, "sessionType", command.sessionType());
        return featureContext;
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
                    "pre_founder",
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
                "pre_founder",
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

    private void putText(Map<String, Object> node, String fieldName, String value) {
        if (value != null && !value.isBlank()) {
            node.put(fieldName, value);
        }
    }

    private void putLong(Map<String, Object> node, String fieldName, Long value) {
        if (value != null) {
            node.put(fieldName, value);
        }
    }
}
