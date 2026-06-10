package com.kakao.backend.chat.application;

import static org.assertj.core.api.Assertions.assertThat;

import com.kakao.backend.agent.domain.Agent;
import com.kakao.backend.chat.domain.ChatMessage;
import com.kakao.backend.chat.domain.ChatRequestStatus;
import com.kakao.backend.chat.domain.ChatRoom;
import com.kakao.backend.chat.dto.ChatAgentDescriptorPayload;
import com.kakao.backend.chat.dto.ChatAgentProgressPayload;
import com.kakao.backend.chat.dto.ChatStreamEventResponse;
import com.kakao.backend.user.model.User;
import com.kakao.backend.workspace.domain.Workspace;
import org.junit.jupiter.api.Test;

class ChatStreamEventFactoryTest {

    private final ChatStreamEventFactory chatStreamEventFactory = new ChatStreamEventFactory();

    @Test
    void buildsMessageEventEnvelope() {
        User user = User.create("test@example.com", "tester", "USER");
        user.setId(2L);

        Workspace workspace = Workspace.create("워크스페이스", "ACTIVE");
        workspace.setId(1L);
        workspace.setUser(user);

        ChatRoom room = ChatRoom.create(workspace, "자유 상담", "FREE_DISCUSSION", null);
        room.setId(10L);

        Agent agent = Agent.reference(5L);

        ChatMessage message = ChatMessage.agentMessage(room, agent, "응답입니다", "{\"requestId\":\"req-123\"}");
        message.setId(100L);

        ChatStreamEventResponse response = chatStreamEventFactory.messageEvent(message);

        assertThat(response.eventType()).isEqualTo("CHAT_MESSAGE");
        assertThat(response.roomId()).isEqualTo(10L);
        assertThat(response.message()).isNotNull();
        assertThat(response.status()).isNull();
        assertThat(response.message().messageId()).isEqualTo(100L);
        assertThat(response.message().senderType()).isEqualTo("AGENT");
        assertThat(response.message().agentId()).isEqualTo(5L);
        assertThat(response.message().content()).isEqualTo("응답입니다");
    }

    @Test
    void buildsConnectedEventEnvelope() {
        ChatStreamEventResponse response = chatStreamEventFactory.connectedEvent(10L);

        assertThat(response.eventType()).isEqualTo("CONNECTED");
        assertThat(response.roomId()).isEqualTo(10L);
        assertThat(response.message()).isNull();
        assertThat(response.status()).isNull();
        assertThat(response.eventId()).isNotBlank();
        assertThat(response.occurredAt()).isNotBlank();
    }

    @Test
    void buildsStatusEventEnvelope() {
        ChatRequestStatus status = ChatRequestStatus.create("req-123", 10L, 100L, "QUEUED");

        ChatStreamEventResponse response = chatStreamEventFactory.statusEvent(status);

        assertThat(response.eventType()).isEqualTo("CHAT_STATUS");
        assertThat(response.roomId()).isEqualTo(10L);
        assertThat(response.status()).isNotNull();
        assertThat(response.status().requestId()).isEqualTo("req-123");
        assertThat(response.status().status()).isEqualTo("QUEUED");
        assertThat(response.agentProgress()).isNull();
    }

    @Test
    void buildsAgentProgressEventEnvelope() {
        ChatAgentProgressPayload payload = new ChatAgentProgressPayload(
                "req-123",
                "PROCESSING",
                "IDEA",
                "AGENT_STARTED",
                "FreeDiscussionOrchestrator",
                2,
                "Policy agent is analyzing support programs.",
                new ChatAgentDescriptorPayload("policy_agent", "Policy Agent", "Support program discovery", "running"),
                java.util.List.of()
        );

        ChatStreamEventResponse response = chatStreamEventFactory.agentProgressEvent(10L, payload);

        assertThat(response.eventType()).isEqualTo("AGENT_PROGRESS");
        assertThat(response.roomId()).isEqualTo(10L);
        assertThat(response.agentProgress()).isNotNull();
        assertThat(response.agentProgress().eventType()).isEqualTo("AGENT_STARTED");
        assertThat(response.message()).isNull();
        assertThat(response.status()).isNull();
    }
}
