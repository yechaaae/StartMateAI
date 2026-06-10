package com.kakao.backend.chat.application;

import com.kakao.backend.agent.domain.Agent;
import com.kakao.backend.agent.infrastructure.AgentRepository;
import com.kakao.backend.aichat.application.AiChatResponsePayloadReader;
import com.kakao.backend.aichat.dto.AiChatResponseMessage;
import com.kakao.backend.aichat.dto.AiChatResultPayload;
import com.kakao.backend.chat.domain.ChatMessage;
import com.kakao.backend.chat.domain.ChatRoom;
import com.kakao.backend.chat.infrastructure.ChatMessageRepository;
import com.kakao.backend.chat.infrastructure.ChatRoomRepository;
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

    public ChatAiResponseCommandService(
            ChatRoomRepository chatRoomRepository,
            ChatMessageRepository chatMessageRepository,
            AgentRepository agentRepository,
            AiChatResponsePayloadReader responsePayloadReader,
            ChatSseService chatSseService,
            ChatRequestStatusService chatRequestStatusService
    ) {
        this.chatRoomRepository = chatRoomRepository;
        this.chatMessageRepository = chatMessageRepository;
        this.agentRepository = agentRepository;
        this.responsePayloadReader = responsePayloadReader;
        this.chatSseService = chatSseService;
        this.chatRequestStatusService = chatRequestStatusService;
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
        String metadata = buildMetadata(response);

        ChatMessage message = ChatMessage.agentMessage(room, agent, content, metadata);
        ChatMessage savedMessage = chatMessageRepository.save(message);
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

    private String buildMetadata(AiChatResponseMessage response) {
        StringBuilder metadata = new StringBuilder("{");
        appendField(metadata, "requestId", response.requestId());
        appendField(metadata, "intent", responsePayloadReader.extractIntent(response));
        appendField(metadata, "agent", responsePayloadReader.extractAgent(response));
        AiChatResultPayload result = responsePayloadReader.extractResult(response);
        if (result != null) {
            appendField(metadata, "resultType", result.resultType());
        }
        if (metadata.length() > 1 && metadata.charAt(metadata.length() - 1) == ',') {
            metadata.deleteCharAt(metadata.length() - 1);
        }
        metadata.append('}');
        return metadata.toString();
    }

    private void appendField(StringBuilder metadata, String key, String value) {
        if (value == null || value.isBlank()) {
            return;
        }
        metadata.append('"')
                .append(key)
                .append("\":\"")
                .append(escape(value))
                .append("\",");
    }

    private String escape(String value) {
        return value.replace("\\", "\\\\").replace("\"", "\\\"");
    }
}
