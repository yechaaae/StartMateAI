package com.kakao.backend.chat.application;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.kakao.backend.agent.domain.Agent;
import com.kakao.backend.agent.infrastructure.AgentRepository;
import com.kakao.backend.aichat.application.AiChatResponsePayloadReader;
import com.kakao.backend.aichat.dto.AiChatResponseMessage;
import com.kakao.backend.aichat.dto.AiChatResultPayload;
import com.kakao.backend.chat.domain.ChatMessage;
import com.kakao.backend.chat.domain.ChatRoom;
import com.kakao.backend.chat.infrastructure.ChatMessageRepository;
import com.kakao.backend.chat.infrastructure.ChatRoomRepository;
import com.kakao.backend.workspace.application.SavedResultService;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional
public class ChatAiResponseCommandService {

    private final ChatRoomRepository chatRoomRepository;
    private final ChatMessageRepository chatMessageRepository;
    private final AgentRepository agentRepository;
    private final AiChatResponsePayloadReader responsePayloadReader;
    private final ChatSseService chatSseService;
    private final ChatRequestStatusService chatRequestStatusService;
    private final ObjectMapper objectMapper;
    private final SavedResultService savedResultService;

    public ChatAiResponseCommandService(
            ChatRoomRepository chatRoomRepository,
            ChatMessageRepository chatMessageRepository,
            AgentRepository agentRepository,
            AiChatResponsePayloadReader responsePayloadReader,
            ChatSseService chatSseService,
            ChatRequestStatusService chatRequestStatusService,
            ObjectMapper objectMapper,
            SavedResultService savedResultService
    ) {
        this.chatRoomRepository = chatRoomRepository;
        this.chatMessageRepository = chatMessageRepository;
        this.agentRepository = agentRepository;
        this.responsePayloadReader = responsePayloadReader;
        this.chatSseService = chatSseService;
        this.chatRequestStatusService = chatRequestStatusService;
        this.objectMapper = objectMapper;
        this.savedResultService = savedResultService;
    }

    public ChatMessage handle(AiChatResponseMessage response) {
        if ("FAILED".equalsIgnoreCase(response.status())) {
            chatRequestStatusService.markFailed(response.requestId(), responsePayloadReader.extractErrorMessage(response));
            return null;
        }

        chatRequestStatusService.markProcessing(response.requestId());
        ChatRoom room = chatRoomRepository.findById(response.roomId())
                .orElseThrow(() -> new IllegalArgumentException("Chat room not found."));

        Agent agent = resolveAgent(responsePayloadReader.extractAgent(response)).orElse(null);
        String content = responsePayloadReader.extractContent(response);
        AiChatResultPayload result = responsePayloadReader.extractResult(response);
        String metadata = buildMetadata(response, result);

        ChatMessage message = ChatMessage.agentMessage(room, agent, content, metadata);
        ChatMessage savedMessage = chatMessageRepository.save(message);
        if (result != null && result.shouldCreateResult()) {
            savedResultService.saveAiResult(room, response, savedMessage, result);
        }
        chatSseService.publish(savedMessage);
        chatRequestStatusService.markCompleted(response.requestId());
        return savedMessage;
    }

    private Optional<Agent> resolveAgent(String agentName) {
        if (agentName == null || agentName.isBlank()) {
            return Optional.empty();
        }
        return agentRepository.findByName(agentName);
    }

    private String buildMetadata(AiChatResponseMessage response, AiChatResultPayload result) {
        Map<String, Object> metadata = new LinkedHashMap<>();
        putText(metadata, "requestId", response.requestId());
        putText(metadata, "intent", responsePayloadReader.extractIntent(response));
        putText(metadata, "agent", responsePayloadReader.extractAgent(response));
        metadata.putAll(requestMetadata(response));
        if (result != null) {
            putText(metadata, "resultType", result.resultType());
            metadata.put("result", objectMapper.convertValue(result, new TypeReference<Map<String, Object>>() {
            }));
        }

        try {
            return objectMapper.writeValueAsString(metadata);
        } catch (JsonProcessingException exception) {
            return "{}";
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> requestMetadata(AiChatResponseMessage response) {
        if (response.payload() == null) {
            return Map.of();
        }
        Object raw = response.payload().get("requestMetadata");
        if (raw instanceof Map<?, ?> map) {
            return new LinkedHashMap<>((Map<String, Object>) map);
        }
        return Map.of();
    }

    private void putText(Map<String, Object> metadata, String key, String value) {
        if (value == null || value.isBlank()) {
            return;
        }
        metadata.put(key, value);
    }
}
