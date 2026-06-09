package com.kakao.backend.chat.application;

import com.kakao.backend.chat.domain.ChatMessage;
import com.kakao.backend.chat.domain.ChatRequestStatus;
import com.kakao.backend.chat.dto.ChatStreamEventResponse;
import com.kakao.backend.chat.dto.ChatStreamMessagePayload;
import com.kakao.backend.chat.dto.ChatRequestStatusPayload;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.UUID;
import org.springframework.stereotype.Component;

@Component
public class ChatStreamEventFactory {

    private static final DateTimeFormatter FORMATTER = DateTimeFormatter.ISO_LOCAL_DATE_TIME;

    public ChatStreamEventResponse connectedEvent(Long roomId) {
        return new ChatStreamEventResponse(
                UUID.randomUUID().toString(),
                "CONNECTED",
                roomId,
                now(),
                null,
                null
        );
    }

    public ChatStreamEventResponse messageEvent(ChatMessage message) {
        return new ChatStreamEventResponse(
                UUID.randomUUID().toString(),
                "CHAT_MESSAGE",
                message.getChatRoom().getId(),
                format(message.getCreatedAt()),
                new ChatStreamMessagePayload(
                        message.getId(),
                        message.getUser() != null ? message.getUser().getId() : null,
                        message.getAgent() != null ? message.getAgent().getId() : null,
                        message.getSenderType(),
                        message.getContent(),
                        message.getMetadata(),
                        format(message.getCreatedAt())
                ),
                null
        );
    }

    public ChatStreamEventResponse statusEvent(ChatRequestStatus status) {
        return new ChatStreamEventResponse(
                UUID.randomUUID().toString(),
                "CHAT_STATUS",
                status.getRoomId(),
                format(status.getUpdatedAt()),
                null,
                new ChatRequestStatusPayload(
                        status.getRequestId(),
                        status.getMessageId(),
                        status.getStatus(),
                        status.getErrorMessage(),
                        format(status.getUpdatedAt())
                )
        );
    }

    private String now() {
        return LocalDateTime.now().format(FORMATTER);
    }

    private String format(LocalDateTime value) {
        return value == null ? now() : value.format(FORMATTER);
    }
}
