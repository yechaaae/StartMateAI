package com.kakao.backend.chat.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.kakao.backend.chat.dto.CreateChatMessageRequest;
import com.kakao.backend.chat.dto.CreateChatRoomRequest;
import com.kakao.backend.chat.dto.ChatMessageResponse;
import com.kakao.backend.chat.dto.ChatRoomResponse;
import com.kakao.backend.chat.infrastructure.ChatMessageRepository;
import com.kakao.backend.chat.infrastructure.ChatRoomRepository;
import com.kakao.backend.domain.ChatMessage;
import com.kakao.backend.domain.ChatRoom;
import com.kakao.backend.domain.User;
import com.kakao.backend.domain.Workspace;
import com.kakao.backend.workspace.infrastructure.UserRepository;
import com.kakao.backend.workspace.infrastructure.WorkspaceRepository;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class ChatServiceTest {

    @Mock
    private ChatRoomRepository chatRoomRepository;

    @Mock
    private ChatMessageRepository chatMessageRepository;

    @Mock
    private WorkspaceRepository workspaceRepository;

    @Mock
    private UserRepository userRepository;

    @InjectMocks
    private ChatService chatService;

    private Workspace workspace;
    private User user;

    @BeforeEach
    void setUp() {
        workspace = Workspace.create("workspace", "ACTIVE");
        workspace.setId(1L);

        user = User.create("test@example.com", "tester", "USER");
        user.setId(2L);
    }

    @Test
    void createRoomBuildsReusableFeatureScopedChatRoom() {
        CreateChatRoomRequest request = new CreateChatRoomRequest(1L, "아이템 추천 채팅", "FEATURE", "IDEA");

        when(workspaceRepository.findById(1L)).thenReturn(Optional.of(workspace));
        when(chatRoomRepository.save(any(ChatRoom.class))).thenAnswer(invocation -> {
            ChatRoom room = invocation.getArgument(0);
            room.setId(10L);
            return room;
        });

        ChatRoomResponse response = chatService.createRoom(request);

        assertThat(response.id()).isEqualTo(10L);
        assertThat(response.workspaceId()).isEqualTo(1L);
        assertThat(response.roomType()).isEqualTo("FEATURE");
        assertThat(response.targetFeature()).isEqualTo("IDEA");
    }

    @Test
    void createUserMessageStoresSenderContextForOtherServices() {
        ChatRoom room = ChatRoom.create(workspace, "아이템 추천 채팅", "FEATURE", "IDEA");
        room.setId(10L);

        CreateChatMessageRequest request = new CreateChatMessageRequest(2L, "초기 자금 100만원 기준으로 다시 추천해줘", "{\"source\":\"workspace\"}");

        when(chatRoomRepository.findById(10L)).thenReturn(Optional.of(room));
        when(userRepository.findById(2L)).thenReturn(Optional.of(user));
        when(chatMessageRepository.save(any(ChatMessage.class))).thenAnswer(invocation -> {
            ChatMessage message = invocation.getArgument(0);
            message.setId(100L);
            return message;
        });

        ChatMessageResponse response = chatService.createUserMessage(10L, request);

        ArgumentCaptor<ChatMessage> captor = ArgumentCaptor.forClass(ChatMessage.class);
        verify(chatMessageRepository).save(captor.capture());
        ChatMessage saved = captor.getValue();

        assertThat(saved.getChatRoom()).isSameAs(room);
        assertThat(saved.getUser()).isSameAs(user);
        assertThat(saved.getSenderType()).isEqualTo("USER");
        assertThat(saved.getContent()).isEqualTo(request.content());
        assertThat(response.id()).isEqualTo(100L);
        assertThat(response.roomId()).isEqualTo(10L);
        assertThat(response.senderType()).isEqualTo("USER");
    }
}
