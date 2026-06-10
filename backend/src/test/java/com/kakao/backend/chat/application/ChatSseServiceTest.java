package com.kakao.backend.chat.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.when;

import com.kakao.backend.chat.dto.ChatStreamEventResponse;
import com.kakao.backend.chat.infrastructure.ChatRoomRepository;
import com.kakao.backend.user.repository.UserRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@ExtendWith(MockitoExtension.class)
class ChatSseServiceTest {

    @Mock
    private ChatRoomRepository chatRoomRepository;

    @Mock
    private UserRepository userRepository;

    @Mock
    private ChatStreamEventFactory chatStreamEventFactory;

    @InjectMocks
    private ChatSseService chatSseService;

    @Test
    void subscribesOwnerToRoomStream() {
        when(userRepository.existsById(2L)).thenReturn(true);
        when(chatRoomRepository.existsById(10L)).thenReturn(true);
        when(chatRoomRepository.existsByIdAndWorkspaceUserId(10L, 2L)).thenReturn(true);
        when(chatStreamEventFactory.connectedEvent(10L)).thenReturn(
                new ChatStreamEventResponse("event-1", "CONNECTED", 10L, "2026-06-09T20:00:00", null, null, null)
        );

        SseEmitter emitter = chatSseService.subscribe(10L, 2L);

        assertThat(emitter).isNotNull();
    }

    @Test
    void rejectsSubscriptionFromAnotherUser() {
        when(userRepository.existsById(3L)).thenReturn(true);
        when(chatRoomRepository.existsById(10L)).thenReturn(true);
        when(chatRoomRepository.existsByIdAndWorkspaceUserId(10L, 3L)).thenReturn(false);

        assertThatThrownBy(() -> chatSseService.subscribe(10L, 3L))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessage("User cannot subscribe to this room.");
    }
}
