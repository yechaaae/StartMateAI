package com.kakao.backend.aichat.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.kakao.backend.aichat.dto.AiChatContextPayload;
import com.kakao.backend.aichat.dto.AiChatRequestMessage;
import com.kakao.backend.aichat.dto.AiChatUserProfilePayload;
import com.kakao.backend.chat.domain.ChatMessage;
import com.kakao.backend.chat.domain.ChatRoom;
import com.kakao.backend.user.model.StartupProfile;
import com.kakao.backend.user.model.User;
import com.kakao.backend.workspace.domain.Workspace;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class AiChatDispatchServiceTest {

    @Mock
    private AiChatGateway gateway;

    @Mock
    private AiChatRequestFactory factory;

    @InjectMocks
    private AiChatDispatchService dispatchService;

    @Test
    void dispatchPublishesFactoryOutputAndReturnsRequestId() {
        Workspace workspace = Workspace.create("워크스페이스", "ACTIVE");
        ChatRoom room = ChatRoom.create(workspace, "자유 상담", "FREE_DISCUSSION", null);
        User user = User.create("test@example.com", "tester", "USER");
        StartupProfile profile = StartupProfile.create();
        ChatMessage message = ChatMessage.userMessage(room, user, "알바를 더 뽑아야 하나?", null);

        AiChatDispatchCommand command = new AiChatDispatchCommand(
                "req-123",
                workspace,
                room,
                user,
                profile,
                message,
                "auto",
                "FREE_CHAT",
                null,
                null,
                null,
                List.of(),
                List.of(),
                Map.of()
        );

        AiChatRequestMessage request = new AiChatRequestMessage(
                "req-123",
                null,
                null,
                null,
                null,
                "FREE_DISCUSSION",
                null,
                "FREE_CHAT",
                "auto",
                "알바를 더 뽑아야 하나?",
                new AiChatUserProfilePayload(null, List.of(), null, null, List.of(), List.of(), "예비창업", "medium", null),
                new AiChatContextPayload(null, null, null, List.of(), Map.of(), List.of())
        );

        when(factory.create(command)).thenReturn(request);

        String requestId = dispatchService.dispatch(command);

        assertThat(requestId).isEqualTo("req-123");
        verify(factory).create(command);
        verify(gateway).publish(request);
    }
}
