package com.kakao.backend.chat.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.kakao.backend.aichat.application.AiChatDispatchCommand;
import com.kakao.backend.aichat.application.AiChatDispatchService;
import com.kakao.backend.aichat.application.AiChatReferenceContextService;
import com.kakao.backend.chat.domain.ChatMessage;
import com.kakao.backend.chat.domain.ChatRoom;
import com.kakao.backend.chat.infrastructure.ChatMessageRepository;
import com.kakao.backend.chat.infrastructure.ChatRoomRepository;
import com.kakao.backend.startupProfile.model.StartupProfile;
import com.kakao.backend.user.model.User;
import com.kakao.backend.startupProfile.repository.StartupProfileRepository;
import com.kakao.backend.user.repository.UserRepository;
import com.kakao.backend.workspace.domain.Workspace;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class ChatMessageCommandServiceTest {

    @Mock
    private ChatRoomRepository chatRoomRepository;

    @Mock
    private ChatMessageRepository chatMessageRepository;

    @Mock
    private UserRepository userRepository;

    @Mock
    private StartupProfileRepository startupProfileRepository;

    @Mock
    private AiChatDispatchService aiChatDispatchService;

    @Mock
    private AiChatReferenceContextService aiChatReferenceContextService;

    @Mock
    private ChatSseService chatSseService;

    @Mock
    private ChatRequestStatusService chatRequestStatusService;

    @Mock
    private ChatCandidateAgentResolver chatCandidateAgentResolver;

    @InjectMocks
    private ChatMessageCommandService chatMessageCommandService;

    @Test
    void sendsUserMessageAndDispatchesAiRequest() {
        User user = User.create("test@example.com", "tester", "USER");
        user.setId(2L);

        Workspace workspace = Workspace.create("workspace", "ACTIVE");
        workspace.setId(1L);
        workspace.setUser(user);

        ChatRoom room = ChatRoom.create(workspace, "idea room", "FEATURE", "IDEA");
        room.setId(10L);

        StartupProfile profile = StartupProfile.create();
        profile.setId(30L);
        profile.setUser(user);

        ChatMessage previous = ChatMessage.userMessage(room, user, "previous", null);
        previous.setId(99L);

        ChatMessage persisted = ChatMessage.userMessage(room, user, "recommend", "{\"source\":\"chat\"}");
        persisted.setId(100L);

        when(chatRoomRepository.findById(10L)).thenReturn(Optional.of(room));
        when(userRepository.findById(2L)).thenReturn(Optional.of(user));
        when(startupProfileRepository.findByUserId(2L)).thenReturn(Optional.of(profile));
        when(chatMessageRepository.findTop20ByChatRoomIdOrderByIdDesc(10L)).thenReturn(List.of(previous));
        when(chatMessageRepository.save(any(ChatMessage.class))).thenReturn(persisted);
        when(aiChatDispatchService.dispatch(any(AiChatDispatchCommand.class))).thenReturn("req-123");
        when(chatCandidateAgentResolver.resolve("FEATURE_CHAT", room, List.of("IdeaAgent", "FinanceAgent")))
                .thenReturn(List.of("IdeaAgent", "FinanceAgent"));
        when(aiChatReferenceContextService.resolve(any(AiChatDispatchCommand.class)))
                .thenReturn(Map.of("referenceType", "BUSINESS_IDEA_RESULT", "referenceId", 44L));
        when(chatRequestStatusService.createQueued(any(), any(), any()))
                .thenReturn(com.kakao.backend.chat.domain.ChatRequestStatus.create("req-123", 10L, 100L, "QUEUED"));

        SendChatMessageCommand command = new SendChatMessageCommand(
                10L,
                2L,
                "recommend",
                "{\"source\":\"chat\"}",
                "idea",
                "FEATURE_CHAT",
                "BUSINESS_IDEA_RESULT",
                44L,
                9L,
                List.of("IdeaAgent", "FinanceAgent"),
                Map.of("selectedOption", "A")
        );

        ChatMessageSendResult result = chatMessageCommandService.send(command);

        assertThat(result.requestId()).isEqualTo("req-123");
        assertThat(result.roomId()).isEqualTo(10L);
        assertThat(result.messageId()).isEqualTo(100L);
        assertThat(result.senderType()).isEqualTo("USER");
        assertThat(result.content()).isEqualTo("recommend");

        ArgumentCaptor<AiChatDispatchCommand> captor = ArgumentCaptor.forClass(AiChatDispatchCommand.class);
        verify(aiChatDispatchService).dispatch(captor.capture());
        AiChatDispatchCommand dispatched = captor.getValue();
        assertThat(dispatched.workspace()).isEqualTo(workspace);
        assertThat(dispatched.room()).isEqualTo(room);
        assertThat(dispatched.user()).isEqualTo(user);
        assertThat(dispatched.startupProfile()).isEqualTo(profile);
        assertThat(dispatched.message()).isEqualTo(persisted);
        assertThat(dispatched.intent()).isEqualTo("idea");
        assertThat(dispatched.sessionType()).isEqualTo("FEATURE_CHAT");
        assertThat(dispatched.currentResultType()).isEqualTo("BUSINESS_IDEA_RESULT");
        assertThat(dispatched.currentResultId()).isEqualTo(44L);
        assertThat(dispatched.selectedIdeaId()).isEqualTo(9L);
        assertThat(dispatched.candidateAgents()).containsExactly("IdeaAgent", "FinanceAgent");
        assertThat(dispatched.recentMessages()).containsExactly(previous);
        assertThat(dispatched.currentResult()).containsEntry("selectedOption", "A");
        assertThat(dispatched.referenceData()).containsEntry("referenceId", 44L);
        verify(chatSseService).publish(persisted);
        verify(chatRequestStatusService).createQueued(any(), org.mockito.Mockito.eq(10L), org.mockito.Mockito.eq(100L));
    }

    @Test
    void resolvesDefaultAgentsForFreeChatWhenClientDidNotProvideAny() {
        User user = User.create("test@example.com", "tester", "USER");
        user.setId(2L);

        Workspace workspace = Workspace.create("workspace", "ACTIVE");
        workspace.setId(1L);
        workspace.setUser(user);

        ChatRoom room = ChatRoom.create(workspace, "free room", "FREE_DISCUSSION", null);
        room.setId(10L);

        ChatMessage persisted = ChatMessage.userMessage(room, user, "help", null);
        persisted.setId(100L);

        when(chatRoomRepository.findById(10L)).thenReturn(Optional.of(room));
        when(userRepository.findById(2L)).thenReturn(Optional.of(user));
        when(startupProfileRepository.findByUserId(2L)).thenReturn(Optional.empty());
        when(chatMessageRepository.findTop20ByChatRoomIdOrderByIdDesc(10L)).thenReturn(List.of());
        when(chatMessageRepository.save(any(ChatMessage.class))).thenReturn(persisted);
        when(chatCandidateAgentResolver.resolve("FREE_CHAT", room, List.of()))
                .thenReturn(List.of("ProfileAgent", "IdeaAgent", "FinanceAgent"));
        when(aiChatDispatchService.dispatch(any(AiChatDispatchCommand.class))).thenReturn("req-free");
        when(aiChatReferenceContextService.resolve(any(AiChatDispatchCommand.class))).thenReturn(Map.of());
        when(chatRequestStatusService.createQueued(any(), any(), any()))
                .thenReturn(com.kakao.backend.chat.domain.ChatRequestStatus.create("req-free", 10L, 100L, "QUEUED"));

        SendChatMessageCommand command = new SendChatMessageCommand(
                10L,
                2L,
                "help",
                null,
                "auto",
                null,
                null,
                null,
                null,
                List.of(),
                Map.of()
        );

        chatMessageCommandService.send(command);

        ArgumentCaptor<AiChatDispatchCommand> captor = ArgumentCaptor.forClass(AiChatDispatchCommand.class);
        verify(aiChatDispatchService).dispatch(captor.capture());
        assertThat(captor.getValue().sessionType()).isEqualTo("FREE_CHAT");
        assertThat(captor.getValue().candidateAgents())
                .containsExactly("ProfileAgent", "IdeaAgent", "FinanceAgent");
    }

    @Test
    void rejectsMessageWhenUserDoesNotOwnRoomWorkspace() {
        User owner = User.create("owner@example.com", "owner", "USER");
        owner.setId(2L);

        User anotherUser = User.create("other@example.com", "other", "USER");
        anotherUser.setId(3L);

        Workspace workspace = Workspace.create("workspace", "ACTIVE");
        workspace.setUser(owner);

        ChatRoom room = ChatRoom.create(workspace, "free room", "FREE_DISCUSSION", null);
        room.setId(10L);

        when(chatRoomRepository.findById(10L)).thenReturn(Optional.of(room));
        when(userRepository.findById(3L)).thenReturn(Optional.of(anotherUser));

        SendChatMessageCommand command = new SendChatMessageCommand(
                10L,
                3L,
                "unauthorized",
                null,
                "auto",
                null,
                null,
                null,
                null,
                List.of(),
                Map.of()
        );

        assertThatThrownBy(() -> chatMessageCommandService.send(command))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessage("User cannot send message to this room.");
    }
}
