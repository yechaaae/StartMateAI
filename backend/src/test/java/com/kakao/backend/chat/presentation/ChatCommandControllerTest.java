package com.kakao.backend.chat.presentation;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import com.kakao.backend.chat.application.ChatMessageCommandService;
import com.kakao.backend.chat.application.ChatMessageSendResult;
import com.kakao.backend.chat.dto.ChatMessageSendResponse;
import com.kakao.backend.chat.dto.SendChatMessageRequest;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class ChatCommandControllerTest {

    @Mock
    private ChatMessageCommandService chatMessageCommandService;

    @InjectMocks
    private ChatCommandController chatCommandController;

    @Test
    void sendsMessageThroughCommandService() throws Exception {
        when(chatMessageCommandService.send(any())).thenReturn(
                new ChatMessageSendResult("req-123", 10L, 100L, "USER", "아이템 추천해줘")
        );

        SendChatMessageRequest request = new SendChatMessageRequest(
                2L,
                "아이템 추천해줘",
                "{\"source\":\"chat\"}",
                "idea",
                "FEATURE_CHAT",
                "BUSINESS_IDEA_RESULT",
                44L,
                9L,
                List.of("IdeaAgent", "FinanceAgent"),
                Map.of("selectedOption", "A")
        );

        ChatMessageSendResponse response = chatCommandController.sendMessage(10L, request).getBody();

        assertThat(response).isNotNull();
        assertThat(response.requestId()).isEqualTo("req-123");
        assertThat(response.roomId()).isEqualTo(10L);
        assertThat(response.messageId()).isEqualTo(100L);
        assertThat(response.senderType()).isEqualTo("USER");
        assertThat(response.content()).isEqualTo("아이템 추천해줘");
    }
}
