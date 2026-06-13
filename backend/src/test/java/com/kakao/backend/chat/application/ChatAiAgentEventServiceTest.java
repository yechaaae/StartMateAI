package com.kakao.backend.chat.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.kakao.backend.agent.domain.Agent;
import com.kakao.backend.agent.infrastructure.AgentRepository;
import com.kakao.backend.aichat.dto.AiChatResponseMessage;
import com.kakao.backend.chat.domain.ChatMessage;
import com.kakao.backend.chat.domain.ChatRoom;
import com.kakao.backend.chat.dto.ChatAgentProgressPayload;
import com.kakao.backend.chat.infrastructure.ChatMessageRepository;
import com.kakao.backend.chat.infrastructure.ChatRoomRepository;
import java.util.Optional;
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

    @Mock
    private ChatRoomRepository chatRoomRepository;

    @Mock
    private ChatMessageRepository chatMessageRepository;

    @Mock
    private AgentRepository agentRepository;

    @Mock
    private ObjectMapper objectMapper;

    @Mock
    private ChatRequestStatusService chatRequestStatusService;

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
                        "type", "status",
                        "viewType", "status",
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

        when(chatRequestStatusService.exists("req-123")).thenReturn(true);
        chatAiAgentEventService.handle(response);

        ArgumentCaptor<ChatAgentProgressPayload> payloadCaptor = ArgumentCaptor.forClass(ChatAgentProgressPayload.class);
        verify(chatSseService).publishAgentProgress(eq(10L), payloadCaptor.capture());
        verify(chatMessageRepository, never()).save(any(ChatMessage.class));

        ChatAgentProgressPayload payload = payloadCaptor.getValue();
        assertThat(payload.requestId()).isEqualTo("req-123");
        assertThat(payload.eventType()).isEqualTo("AGENT_STARTED");
        assertThat(payload.type()).isEqualTo("status");
        assertThat(payload.viewType()).isEqualTo("status");
        assertThat(payload.orchestrator()).isEqualTo("FreeDiscussionOrchestrator");
        assertThat(payload.sequence()).isEqualTo(2);
        assertThat(payload.agent()).isNotNull();
        assertThat(payload.agent().agentKey()).isEqualTo("policy_agent");
        assertThat(payload.selectedAgents()).hasSize(2);
    }

    @Test
    void persistsDiscussionStyleAgentEventForHistoryRestore() throws Exception {
        ChatRoom room = ChatRoom.create(null, "room", "FREE_DISCUSSION", null);
        room.setId(10L);

        Agent agent = Agent.reference(1L);
        agent.setName("FinanceAgent");

        when(chatRoomRepository.findById(10L)).thenReturn(Optional.of(room));
        when(agentRepository.findByName("FinanceAgent")).thenReturn(Optional.of(agent));
        when(objectMapper.writeValueAsString(any())).thenReturn("{\"progressMessage\":true}");
        when(chatRequestStatusService.exists("req-999")).thenReturn(true);

        AiChatResponseMessage response = new AiChatResponseMessage(
                "req-999",
                10L,
                "idea",
                "FinanceAgent",
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
                        "eventType", "agent.challenge",
                        "type", "challenge",
                        "viewType", "challenge",
                        "orchestrator", "OrchestratorAgent",
                        "sequence", 4,
                        "message", "Finance Agent -> Idea Agent: margin assumption needs revision.",
                        "agent", java.util.Map.of(
                                "agentKey", "FinanceAgent",
                                "label", "Finance Agent",
                                "role", "Cost and profit review",
                                "status", "running"
                        ),
                        "selectedAgents", java.util.List.of(
                                java.util.Map.of(
                                        "agentKey", "IdeaAgent",
                                        "label", "Idea Agent",
                                        "role", "Idea exploration",
                                        "status", "completed"
                                )
                        ),
                        "detail", java.util.Map.of(
                                "target_intent", "idea",
                                "basis", "margin is negative"
                        )
                )
        );

        chatAiAgentEventService.handle(response);

        ArgumentCaptor<ChatMessage> messageCaptor = ArgumentCaptor.forClass(ChatMessage.class);
        verify(chatMessageRepository).save(messageCaptor.capture());
        verify(chatSseService).publishAgentProgress(eq(10L), any(ChatAgentProgressPayload.class));

        ChatMessage savedMessage = messageCaptor.getValue();
        assertThat(savedMessage.getChatRoom()).isSameAs(room);
        assertThat(savedMessage.getAgent()).isSameAs(agent);
        assertThat(savedMessage.getSenderType()).isEqualTo("AGENT");
        assertThat(savedMessage.getContent()).isEqualTo("Finance Agent -> Idea Agent: margin assumption needs revision.");
        assertThat(savedMessage.getMetadata()).contains("progressMessage");
    }

    @Test
    void ignoresAgentEventWhenRequestStatusDoesNotExist() {
        AiChatResponseMessage response = new AiChatResponseMessage(
                "req-stale-event",
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
                        "eventType", "agent.challenge",
                        "message", "stale progress"
                )
        );

        when(chatRequestStatusService.exists("req-stale-event")).thenReturn(false);

        chatAiAgentEventService.handle(response);

        verify(chatRequestStatusService).exists("req-stale-event");
        verifyNoInteractions(chatSseService, chatRoomRepository, chatMessageRepository);
    }
}
