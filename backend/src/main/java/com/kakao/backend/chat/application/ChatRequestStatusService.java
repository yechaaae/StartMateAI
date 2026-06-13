package com.kakao.backend.chat.application;

import com.kakao.backend.chat.domain.ChatRequestStatus;
import com.kakao.backend.chat.infrastructure.ChatRequestStatusRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional
public class ChatRequestStatusService {

    private final ChatRequestStatusRepository chatRequestStatusRepository;
    private final ChatSseService chatSseService;

    public ChatRequestStatusService(
            ChatRequestStatusRepository chatRequestStatusRepository,
            ChatSseService chatSseService
    ) {
        this.chatRequestStatusRepository = chatRequestStatusRepository;
        this.chatSseService = chatSseService;
    }

    public ChatRequestStatus createQueued(String requestId, Long roomId, Long messageId) {
        ChatRequestStatus status = ChatRequestStatus.create(requestId, roomId, messageId, "QUEUED");
        ChatRequestStatus saved = chatRequestStatusRepository.save(status);
        chatSseService.publishStatus(saved);
        return saved;
    }

    public boolean exists(String requestId) {
        return requestId != null
                && !requestId.isBlank()
                && chatRequestStatusRepository.findByRequestId(requestId).isPresent();
    }

    public ChatRequestStatus markProcessing(String requestId) {
        ChatRequestStatus status = getByRequestId(requestId);
        status.markProcessing();
        chatSseService.publishStatus(status);
        return status;
    }

    public ChatRequestStatus markCompleted(String requestId) {
        ChatRequestStatus status = getByRequestId(requestId);
        status.markCompleted();
        chatSseService.publishStatus(status);
        return status;
    }

    public ChatRequestStatus markFailed(String requestId, String errorMessage) {
        ChatRequestStatus status = getByRequestId(requestId);
        status.markFailed(errorMessage);
        chatSseService.publishStatus(status);
        return status;
    }

    private ChatRequestStatus getByRequestId(String requestId) {
        return chatRequestStatusRepository.findByRequestId(requestId)
                .orElseThrow(() -> new IllegalArgumentException("Chat request status not found."));
    }
}
