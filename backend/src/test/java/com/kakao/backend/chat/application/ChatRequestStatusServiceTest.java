package com.kakao.backend.chat.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.kakao.backend.chat.domain.ChatRequestStatus;
import com.kakao.backend.chat.infrastructure.ChatRequestStatusRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class ChatRequestStatusServiceTest {

    @Mock
    private ChatRequestStatusRepository chatRequestStatusRepository;

    @Mock
    private ChatSseService chatSseService;

    @InjectMocks
    private ChatRequestStatusService chatRequestStatusService;

    @Test
    void createsQueuedStatusAndPublishesIt() {
        ChatRequestStatus saved = ChatRequestStatus.create("req-123", 10L, 100L, "QUEUED");
        when(chatRequestStatusRepository.save(any(ChatRequestStatus.class))).thenReturn(saved);

        ChatRequestStatus status = chatRequestStatusService.createQueued("req-123", 10L, 100L);

        assertThat(status.getRequestId()).isEqualTo("req-123");
        assertThat(status.getStatus()).isEqualTo("QUEUED");
        verify(chatSseService).publishStatus(saved);
    }

    @Test
    void marksStatusCompletedAndPublishesIt() {
        ChatRequestStatus existing = ChatRequestStatus.create("req-123", 10L, 100L, "QUEUED");

        when(chatRequestStatusRepository.findByRequestId("req-123")).thenReturn(java.util.Optional.of(existing));

        ChatRequestStatus status = chatRequestStatusService.markCompleted("req-123");

        assertThat(status.getStatus()).isEqualTo("COMPLETED");
        verify(chatSseService).publishStatus(existing);
    }

    @Test
    void checksWhetherStatusExists() {
        ChatRequestStatus existing = ChatRequestStatus.create("req-123", 10L, 100L, "QUEUED");

        when(chatRequestStatusRepository.findByRequestId("req-123")).thenReturn(java.util.Optional.of(existing));
        when(chatRequestStatusRepository.findByRequestId("req-missing")).thenReturn(java.util.Optional.empty());

        assertThat(chatRequestStatusService.exists("req-123")).isTrue();
        assertThat(chatRequestStatusService.exists("req-missing")).isFalse();
        assertThat(chatRequestStatusService.exists("")).isFalse();
        assertThat(chatRequestStatusService.exists(null)).isFalse();
    }
}
