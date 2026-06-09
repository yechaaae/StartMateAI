package com.kakao.backend.chat.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.when;

import com.kakao.backend.chat.domain.ChatRoom;
import com.kakao.backend.chat.dto.ChatStreamEventResponse;
import com.kakao.backend.chat.infrastructure.ChatRoomRepository;
import com.kakao.backend.user.domain.User;
import com.kakao.backend.user.infrastructure.UserRepository;
import com.kakao.backend.workspace.domain.Workspace;
import java.util.Optional;
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
        User user = User.create("test@example.com", "tester", "USER");
        user.setId(2L);

        Workspace workspace = Workspace.create("워크스페이스", "ACTIVE");
        workspace.setUser(user);

        ChatRoom room = ChatRoom.create(workspace, "자유 상담", "FREE_DISCUSSION", null);
        room.setId(10L);

        when(chatRoomRepository.findById(10L)).thenReturn(Optional.of(room));
        when(userRepository.findById(2L)).thenReturn(Optional.of(user));
        when(chatStreamEventFactory.connectedEvent(10L)).thenReturn(
                new ChatStreamEventResponse("event-1", "CONNECTED", 10L, "2026-06-09T20:00:00", null, null)
        );

        SseEmitter emitter = chatSseService.subscribe(10L, 2L);

        assertThat(emitter).isNotNull();
    }

    @Test
    void rejectsSubscriptionFromAnotherUser() {
        User owner = User.create("owner@example.com", "owner", "USER");
        owner.setId(2L);

        User anotherUser = User.create("other@example.com", "other", "USER");
        anotherUser.setId(3L);

        Workspace workspace = Workspace.create("워크스페이스", "ACTIVE");
        workspace.setUser(owner);

        ChatRoom room = ChatRoom.create(workspace, "자유 상담", "FREE_DISCUSSION", null);
        room.setId(10L);

        when(chatRoomRepository.findById(10L)).thenReturn(Optional.of(room));
        when(userRepository.findById(3L)).thenReturn(Optional.of(anotherUser));

        assertThatThrownBy(() -> chatSseService.subscribe(10L, 3L))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessage("User cannot subscribe to this room.");
    }
}
