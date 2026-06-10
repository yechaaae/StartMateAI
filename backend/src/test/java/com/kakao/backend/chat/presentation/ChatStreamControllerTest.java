package com.kakao.backend.chat.presentation;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import com.kakao.backend.chat.application.ChatSseService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@ExtendWith(MockitoExtension.class)
class ChatStreamControllerTest {

    @Mock
    private ChatSseService chatSseService;

    @InjectMocks
    private ChatStreamController chatStreamController;

    @Test
    void subscribesToRoomStream() {
        SseEmitter emitter = new SseEmitter();
        when(chatSseService.subscribe(10L, 2L)).thenReturn(emitter);

        SseEmitter response = chatStreamController.subscribe(10L, 2L);

        assertThat(response).isSameAs(emitter);
    }
}
