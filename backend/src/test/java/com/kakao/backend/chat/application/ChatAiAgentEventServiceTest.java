package com.kakao.backend.chat.application;

import static org.mockito.Mockito.verify;

import com.kakao.backend.aichat.dto.AiChatResponseMessage;
import com.kakao.backend.chat.dto.ChatAgentProgressPayload;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class ChatAiAgentEventServiceTest {

    @Mock
    private ChatSseService chatSseService;

    @InjectMocks
    private ChatAiAgentEventService chatAiAgentEventService;

    @Test
    void publishesAgentProgressEventToSse() {
        AiChatResponseMessage response = new AiChatResponseMessage(
                "req-123",
                10L,
                "idea",
                "IdeaAgent",
                null,
                java.util.Map.of(),
                java.util.List.of(),
                java.util.List.of(),
                null,
                "v1",
                "AGENT_EVENT",
                2L,
                "IDEA",
                "PROCESSING",
                java.util.Map.of(
                        "eventType", "AGENT_STARTED",
                        "orchestrator", "FreeDiscussionOrchestrator",
                        "sequence", 2,
                        "message", "Policy agent is analyzing support programs.",
                        "agent", java.util.Map.of(
                                "agentKey", "policy_agent",
                                "label", "Policy Agent",
                                "role", "Support program discovery",
                                "status", "running"
                        ),
                        "selectedAgents", java.util.List.of(
                                java.util.Map.of(
                                        "agentKey", "idea_agent",
                                        "label", "Idea Agent",
                                        "role", "Idea exploration",
                                        "status", "completed"
                                ),
                                java.util.Map.of(
                                        "agentKey", "policy_agent",
                                        "label", "Policy Agent",
                                        "role", "Support program discovery",
                                        "status", "running"
                                )
                        )
                )
        );

        chatAiAgentEventService.handle(response);

        ArgumentCaptor<ChatAgentProgressPayload> payloadCaptor = ArgumentCaptor.forClass(ChatAgentProgressPayload.class);
        verify(chatSseService).publishAgentProgress(org.mockito.ArgumentMatchers.eq(10L), payloadCaptor.capture());

        ChatAgentProgressPayload payload = payloadCaptor.getValue();
        org.assertj.core.api.Assertions.assertThat(payload.requestId()).isEqualTo("req-123");
        org.assertj.core.api.Assertions.assertThat(payload.eventType()).isEqualTo("AGENT_STARTED");
        org.assertj.core.api.Assertions.assertThat(payload.orchestrator()).isEqualTo("FreeDiscussionOrchestrator");
        org.assertj.core.api.Assertions.assertThat(payload.sequence()).isEqualTo(2);
        org.assertj.core.api.Assertions.assertThat(payload.agent()).isNotNull();
        org.assertj.core.api.Assertions.assertThat(payload.agent().agentKey()).isEqualTo("policy_agent");
        org.assertj.core.api.Assertions.assertThat(payload.selectedAgents()).hasSize(2);
    }
}
