package com.kakao.backend.chat.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.kakao.backend.agent.domain.Agent;
import com.kakao.backend.agent.infrastructure.AgentRepository;
import com.kakao.backend.aichat.application.AiChatResponsePayloadReader;
import com.kakao.backend.aichat.dto.AiChatResponseMessage;
import com.kakao.backend.chat.domain.ChatMessage;
import com.kakao.backend.chat.domain.ChatRoom;
import com.kakao.backend.chat.infrastructure.ChatMessageRepository;
import com.kakao.backend.chat.infrastructure.ChatRoomRepository;
import com.kakao.backend.user.model.User;
import com.kakao.backend.workspace.domain.Workspace;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class ChatAiResponseCommandServiceTest {

    @Mock
    private ChatRoomRepository chatRoomRepository;

    @Mock
    private ChatMessageRepository chatMessageRepository;

    @Mock
    private AgentRepository agentRepository;

    @Spy
    private AiChatResponsePayloadReader responsePayloadReader = new AiChatResponsePayloadReader(new ObjectMapper());

    @Mock
    private ChatSseService chatSseService;

    @Mock
    private ChatRequestStatusService chatRequestStatusService;

    @InjectMocks
    private ChatAiResponseCommandService chatAiResponseCommandService;

    @Test
    void savesAiResponseAsAgentMessage() {
        User user = User.create("test@example.com", "tester", "USER");
        user.setId(2L);

        Workspace workspace = Workspace.create("workspace", "ACTIVE");
        workspace.setId(1L);
        workspace.setUser(user);

        ChatRoom room = ChatRoom.create(workspace, "idea room", "FEATURE", "IDEA");
        room.setId(10L);

        Agent agent = Agent.reference(5L);
        agent.setName("IdeaAgent");

        ChatMessage persisted = ChatMessage.agentMessage(room, agent, "summary", null);
        persisted.setId(200L);

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
                "CHAT_RESPONSE",
                2L,
                "IDEA",
                "COMPLETED",
                new ObjectMapper().valueToTree(java.util.Map.of(
                        "common", java.util.Map.of("message", "summary"),
                        "result", java.util.Map.of("resultType", "BUSINESS_IDEA_RESULT")
                ))
        );

        when(chatRoomRepository.findById(10L)).thenReturn(Optional.of(room));
        when(agentRepository.findByName("IdeaAgent")).thenReturn(Optional.of(agent));
        when(chatMessageRepository.save(any(ChatMessage.class))).thenReturn(persisted);
        when(chatRequestStatusService.markProcessing("req-123"))
                .thenReturn(com.kakao.backend.chat.domain.ChatRequestStatus.create("req-123", 10L, 100L, "PROCESSING"));
        when(chatRequestStatusService.markCompleted("req-123"))
                .thenReturn(com.kakao.backend.chat.domain.ChatRequestStatus.create("req-123", 10L, 100L, "COMPLETED"));

        ChatMessage savedMessage = chatAiResponseCommandService.handle(response);

        assertThat(savedMessage.getId()).isEqualTo(200L);
        assertThat(savedMessage.getAgent()).isEqualTo(agent);
        assertThat(savedMessage.getSenderType()).isEqualTo("AGENT");
        assertThat(savedMessage.getContent()).isEqualTo("summary");
        verify(chatSseService).publish(persisted);
    }

    @Test
    void marksFailedResponseWithoutPersistingMessage() {
        AiChatResponseMessage response = new AiChatResponseMessage(
                "req-failed",
                10L,
                "idea",
                "IdeaAgent",
                null,
                java.util.Map.of(),
                java.util.List.of(),
                java.util.List.of(),
                null,
                "v1",
                "CHAT_RESPONSE",
                2L,
                "IDEA",
                "FAILED",
                new ObjectMapper().valueToTree(java.util.Map.of(
                        "error", java.util.Map.of("message", "agent error")
                ))
        );

        ChatMessage savedMessage = chatAiResponseCommandService.handle(response);

        assertThat(savedMessage).isNull();
        verify(chatRequestStatusService).markFailed("req-failed", "agent error");
    }

    @Test
    void rejectsResponseWhenRoomDoesNotExist() {
        AiChatResponseMessage response = new AiChatResponseMessage(
                "req-missing",
                999L,
                "idea",
                "IdeaAgent",
                "summary",
                java.util.Map.of(),
                java.util.List.of(),
                java.util.List.of(),
                null
        );

        when(chatRoomRepository.findById(999L)).thenReturn(Optional.empty());
        when(chatRequestStatusService.markProcessing("req-missing"))
                .thenReturn(com.kakao.backend.chat.domain.ChatRequestStatus.create("req-missing", 999L, 1L, "PROCESSING"));

        assertThatThrownBy(() -> chatAiResponseCommandService.handle(response))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessage("Chat room not found.");
    }
}
