package com.kakao.backend.chat.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import com.kakao.backend.chat.domain.ChatMessage;
import com.kakao.backend.chat.domain.ChatRoom;
import com.kakao.backend.chat.infrastructure.ChatMessageRepository;
import com.kakao.backend.chat.infrastructure.ChatRoomRepository;
import com.kakao.backend.user.model.User;
import com.kakao.backend.user.repository.UserRepository;
import com.kakao.backend.workspace.domain.Workspace;
import com.kakao.backend.workspace.infrastructure.WorkspaceRepository;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class ChatRoomQueryServiceTest {

    @Mock
    private ChatRoomRepository chatRoomRepository;

    @Mock
    private ChatMessageRepository chatMessageRepository;

    @Mock
    private UserRepository userRepository;

    @Mock
    private WorkspaceRepository workspaceRepository;

    @InjectMocks
    private ChatRoomQueryService chatRoomQueryService;

    @Test
    void returnsExistingFreeDiscussionRoom() {
        User user = User.create("test@example.com", "tester", "USER");
        user.setId(2L);

        Workspace workspace = Workspace.create("워크스페이스", "ACTIVE");
        workspace.setId(1L);
        workspace.setUser(user);

        ChatRoom room = ChatRoom.create(workspace, "자유 상담실", "FREE_DISCUSSION", null);
        room.setId(10L);

        when(userRepository.findById(2L)).thenReturn(Optional.of(user));
        when(chatRoomRepository.findFirstByWorkspaceUserIdAndRoomTypeOrderByIdAsc(2L, "FREE_DISCUSSION"))
                .thenReturn(Optional.of(room));

        FreeChatRoomResult result = chatRoomQueryService.getOrCreateFreeRoom(2L);

        assertThat(result.roomId()).isEqualTo(10L);
        assertThat(result.workspaceId()).isEqualTo(1L);
        assertThat(result.created()).isFalse();
    }

    @Test
    void createsFreeDiscussionRoomUsingExistingWorkspace() {
        User user = User.create("test@example.com", "tester", "USER");
        user.setId(2L);

        Workspace workspace = Workspace.create("워크스페이스", "ACTIVE");
        workspace.setId(1L);
        workspace.setUser(user);

        ChatRoom createdRoom = ChatRoom.create(workspace, "자유 상담실", "FREE_DISCUSSION", null);
        createdRoom.setId(10L);

        when(userRepository.findById(2L)).thenReturn(Optional.of(user));
        when(chatRoomRepository.findFirstByWorkspaceUserIdAndRoomTypeOrderByIdAsc(2L, "FREE_DISCUSSION"))
                .thenReturn(Optional.empty());
        when(workspaceRepository.findFirstByUserIdAndStatusOrderByIdAsc(2L, "ACTIVE"))
                .thenReturn(Optional.of(workspace));
        when(chatRoomRepository.save(any(ChatRoom.class))).thenReturn(createdRoom);

        FreeChatRoomResult result = chatRoomQueryService.getOrCreateFreeRoom(2L);

        assertThat(result.roomId()).isEqualTo(10L);
        assertThat(result.workspaceId()).isEqualTo(1L);
        assertThat(result.created()).isTrue();
    }

    @Test
    void returnsMessageHistoryInAscendingOrder() {
        User user = User.create("test@example.com", "tester", "USER");
        user.setId(2L);

        Workspace workspace = Workspace.create("워크스페이스", "ACTIVE");
        workspace.setUser(user);

        ChatRoom room = ChatRoom.create(workspace, "자유 상담실", "FREE_DISCUSSION", null);
        room.setId(10L);

        ChatMessage first = ChatMessage.userMessage(room, user, "안녕", null);
        first.setId(100L);
        ChatMessage second = ChatMessage.agentMessage(room, null, "무엇을 도와줄까?", "{\"requestId\":\"req-1\"}");
        second.setId(101L);

        when(chatRoomRepository.findById(10L)).thenReturn(Optional.of(room));
        when(userRepository.findById(2L)).thenReturn(Optional.of(user));
        when(chatMessageRepository.findByChatRoomIdOrderByIdAsc(10L)).thenReturn(List.of(first, second));

        ChatMessageHistoryResult result = chatRoomQueryService.getMessageHistory(10L, 2L);

        assertThat(result.roomId()).isEqualTo(10L);
        assertThat(result.messages()).hasSize(2);
        assertThat(result.messages().get(0).messageId()).isEqualTo(100L);
        assertThat(result.messages().get(1).messageId()).isEqualTo(101L);
        assertThat(result.messages().get(1).senderType()).isEqualTo("AGENT");
    }

    @Test
    void rejectsHistoryRequestFromAnotherUser() {
        User owner = User.create("owner@example.com", "owner", "USER");
        owner.setId(2L);

        User anotherUser = User.create("other@example.com", "other", "USER");
        anotherUser.setId(3L);

        Workspace workspace = Workspace.create("워크스페이스", "ACTIVE");
        workspace.setUser(owner);

        ChatRoom room = ChatRoom.create(workspace, "자유 상담실", "FREE_DISCUSSION", null);
        room.setId(10L);

        when(chatRoomRepository.findById(10L)).thenReturn(Optional.of(room));
        when(userRepository.findById(3L)).thenReturn(Optional.of(anotherUser));

        assertThatThrownBy(() -> chatRoomQueryService.getMessageHistory(10L, 3L))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessage("User cannot access this room.");
    }
}
