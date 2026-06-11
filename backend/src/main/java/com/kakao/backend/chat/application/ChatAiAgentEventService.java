package com.kakao.backend.chat.application;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.kakao.backend.agent.domain.Agent;
import com.kakao.backend.agent.infrastructure.AgentRepository;
import com.kakao.backend.aichat.dto.AiChatResponseMessage;
import com.kakao.backend.chat.domain.ChatMessage;
import com.kakao.backend.chat.domain.ChatRoom;
import com.kakao.backend.chat.dto.ChatAgentDescriptorPayload;
import com.kakao.backend.chat.dto.ChatAgentProgressPayload;
import com.kakao.backend.chat.infrastructure.ChatMessageRepository;
import com.kakao.backend.chat.infrastructure.ChatRoomRepository;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional
public class ChatAiAgentEventService {

    private static final Set<String> PERSISTED_VIEW_TYPES = Set.of(
            "discussion",
            "result",
            "argument",
            "challenge",
            "revision",
            "consensus"
    );

    private final ChatSseService chatSseService;
    private final ChatRoomRepository chatRoomRepository;
    private final ChatMessageRepository chatMessageRepository;
    private final AgentRepository agentRepository;
    private final ObjectMapper objectMapper;

    public ChatAiAgentEventService(
            ChatSseService chatSseService,
            ChatRoomRepository chatRoomRepository,
            ChatMessageRepository chatMessageRepository,
            AgentRepository agentRepository,
            ObjectMapper objectMapper
    ) {
        this.chatSseService = chatSseService;
        this.chatRoomRepository = chatRoomRepository;
        this.chatMessageRepository = chatMessageRepository;
        this.agentRepository = agentRepository;
        this.objectMapper = objectMapper;
    }

    public void handle(AiChatResponseMessage response) {
        if (response == null || response.roomId() == null) {
            return;
        }

        ChatAgentProgressPayload payload = buildPayload(response);
        persistIfNeeded(response, payload);
        chatSseService.publishAgentProgress(response.roomId(), payload);
    }

    private ChatAgentProgressPayload buildPayload(AiChatResponseMessage response) {
        String type = normalizedType(response.payload());
        String viewType = normalizedViewType(response.payload(), type);

        return new ChatAgentProgressPayload(
                response.requestId(),
                response.status(),
                response.targetFeature(),
                textAt(response.payload(), "eventType"),
                type,
                viewType,
                textAt(response.payload(), "orchestrator"),
                integerAt(response.payload(), "sequence"),
                textAt(response.payload(), "message"),
                descriptorAt(mapAt(response.payload(), "agent")),
                descriptorsAt(listAt(response.payload(), "selectedAgents")),
                mapAt(response.payload(), "detail")
        );
    }

    private void persistIfNeeded(AiChatResponseMessage response, ChatAgentProgressPayload payload) {
        if (payload == null || !shouldPersist(payload)) {
            return;
        }

        ChatRoom room = chatRoomRepository.findById(response.roomId()).orElse(null);
        if (room == null) {
            return;
        }

        String content = firstNonBlank(payload.message(), response.summary());
        if (content == null) {
            return;
        }

        Agent agent = resolveAgent(
                payload.agent() != null ? payload.agent().agentKey() : null,
                response.agent(),
                textAt(response.payload(), "agent")
        ).orElse(null);

        ChatMessage message = ChatMessage.agentMessage(room, agent, content, buildMetadata(response, payload));
        chatMessageRepository.save(message);
    }

    private boolean shouldPersist(ChatAgentProgressPayload payload) {
        return PERSISTED_VIEW_TYPES.contains(lower(payload.viewType()));
    }

    private Optional<Agent> resolveAgent(String... candidates) {
        for (String candidate : candidates) {
            if (candidate == null || candidate.isBlank()) {
                continue;
            }

            Optional<Agent> agent = agentRepository.findByName(candidate);
            if (agent.isPresent()) {
                return agent;
            }
        }
        return Optional.empty();
    }

    private String buildMetadata(AiChatResponseMessage response, ChatAgentProgressPayload payload) {
        Map<String, Object> metadata = new LinkedHashMap<>();
        putText(metadata, "requestId", response.requestId());
        putText(metadata, "targetFeature", response.targetFeature());
        putText(metadata, "eventType", payload.eventType());
        putText(metadata, "type", payload.type());
        putText(metadata, "viewType", payload.viewType());
        putText(metadata, "orchestrator", payload.orchestrator());
        if (payload.sequence() != null) {
            metadata.put("sequence", payload.sequence());
        }
        metadata.put("progressMessage", true);

        if (payload.agent() != null) {
            putText(metadata, "agent", payload.agent().agentKey());
            putText(metadata, "agentKey", payload.agent().agentKey());
            putText(metadata, "agentLabel", payload.agent().label());
            putText(metadata, "progressRole", payload.agent().role());
            putText(metadata, "progressStatus", payload.agent().status());
        } else {
            putText(metadata, "agent", response.agent());
        }

        if (payload.selectedAgents() != null && !payload.selectedAgents().isEmpty()) {
            metadata.put("selectedAgents", payload.selectedAgents().stream()
                    .map(this::descriptorMetadata)
                    .toList());
        }

        if (payload.detail() != null && !payload.detail().isEmpty()) {
            metadata.put("detail", payload.detail());
        }

        Map<String, Object> requestMetadata = mapAt(response.payload(), "requestMetadata");
        if (requestMetadata != null && !requestMetadata.isEmpty()) {
            metadata.putAll(requestMetadata);
        }

        try {
            return objectMapper.writeValueAsString(metadata);
        } catch (JsonProcessingException exception) {
            return "{}";
        }
    }

    private Map<String, Object> descriptorMetadata(ChatAgentDescriptorPayload payload) {
        Map<String, Object> metadata = new LinkedHashMap<>();
        putText(metadata, "agentKey", payload.agentKey());
        putText(metadata, "label", payload.label());
        putText(metadata, "role", payload.role());
        putText(metadata, "status", payload.status());
        return metadata;
    }

    private String normalizedType(Map<String, Object> payload) {
        String explicitType = firstNonBlank(textAt(payload, "type"), textAt(payload, "viewType"));
        if (explicitType != null) {
            return explicitType;
        }

        String eventType = lower(textAt(payload, "eventType"));
        if ("agent.completed".equals(eventType)) {
            return "result";
        }
        if ("orchestrator.synthesizing".equals(eventType)) {
            return "discussion";
        }
        return "status";
    }

    private String normalizedViewType(Map<String, Object> payload, String fallbackType) {
        return firstNonBlank(textAt(payload, "viewType"), textAt(payload, "type"), fallbackType);
    }

    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value;
            }
        }
        return null;
    }

    private String lower(String value) {
        return value == null ? null : value.toLowerCase();
    }

    private void putText(Map<String, Object> metadata, String key, String value) {
        if (value == null || value.isBlank()) {
            return;
        }
        metadata.put(key, value);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> mapAt(Map<String, Object> payload, String key) {
        if (payload == null) {
            return null;
        }
        Object value = payload.get(key);
        return value instanceof Map<?, ?> ? (Map<String, Object>) value : null;
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> listAt(Map<String, Object> payload, String key) {
        if (payload == null) {
            return List.of();
        }
        Object value = payload.get(key);
        if (!(value instanceof List<?> list)) {
            return List.of();
        }

        List<Map<String, Object>> results = new ArrayList<>();
        for (Object item : list) {
            if (item instanceof Map<?, ?> map) {
                results.add((Map<String, Object>) map);
            }
        }
        return results;
    }

    private ChatAgentDescriptorPayload descriptorAt(Map<String, Object> payload) {
        if (payload == null || payload.isEmpty()) {
            return null;
        }
        return new ChatAgentDescriptorPayload(
                text(payload, "agentKey"),
                text(payload, "label"),
                text(payload, "role"),
                text(payload, "status")
        );
    }

    private List<ChatAgentDescriptorPayload> descriptorsAt(List<Map<String, Object>> payloads) {
        if (payloads == null || payloads.isEmpty()) {
            return List.of();
        }
        return payloads.stream()
                .map(this::descriptorAt)
                .filter(item -> item != null)
                .toList();
    }

    private String textAt(Map<String, Object> payload, String key) {
        return text(payload, key);
    }

    private String text(Map<String, Object> payload, String key) {
        if (payload == null) {
            return null;
        }
        Object value = payload.get(key);
        if (value == null) {
            return null;
        }
        String text = String.valueOf(value);
        return text.isBlank() ? null : text;
    }

    private Integer integerAt(Map<String, Object> payload, String key) {
        if (payload == null) {
            return null;
        }
        Object value = payload.get(key);
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value instanceof String text && !text.isBlank()) {
            try {
                return Integer.parseInt(text);
            } catch (NumberFormatException ignored) {
                return null;
            }
        }
        return null;
    }
}
