package com.kakao.backend.aichat.infrastructure;

import static org.mockito.Mockito.verify;

import com.kakao.backend.aichat.dto.AiChatResponseMessage;
import com.kakao.backend.chat.application.ChatAiAgentEventService;
import com.kakao.backend.chat.application.ChatAiResponseCommandService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class AiChatResponseListenerTest {

    @Mock
    private ChatAiResponseCommandService chatAiResponseCommandService;

    @Mock
    private ChatAiAgentEventService chatAiAgentEventService;

    @InjectMocks
    private AiChatResponseListener aiChatResponseListener;

    @Test
    void delegatesIncomingResponseToChatService() {
        AiChatResponseMessage response = new AiChatResponseMessage(
                "req-123",
                10L,
                "idea",
                "IdeaAgent",
                "summary",
                java.util.Map.of(),
                java.util.List.of(),
                java.util.List.of(),
                null
        );

        aiChatResponseListener.consume(response);

        verify(chatAiResponseCommandService).handle(response);
    }

    @Test
    void delegatesAgentEventToProgressService() {
        AiChatResponseMessage response = new AiChatResponseMessage(
                "req-123",
                10L,
                "idea",
                "IdeaAgent",
                "progress",
                java.util.Map.of(),
                java.util.List.of(),
                java.util.List.of(),
                null,
                "v1",
                "AGENT_EVENT",
                2L,
                "IDEA",
                "PROCESSING",
                java.util.Map.of("eventType", "AGENT_STARTED")
        );

        aiChatResponseListener.consume(response);

        verify(chatAiAgentEventService).handle(response);
    }
}
