package com.kakao.backend.chat.application;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.kakao.backend.aichat.application.AiChatDispatchCommand;
import com.kakao.backend.aichat.application.AiChatDispatchService;
import com.kakao.backend.aichat.application.AiChatExternalReferenceDataService;
import com.kakao.backend.aichat.application.AiChatReferenceContextService;
import com.kakao.backend.aichat.application.AiChatResponsePayloadReader;
import com.kakao.backend.aichat.dto.AiChatResponseMessage;
import com.kakao.backend.chat.domain.ChatMessage;
import com.kakao.backend.chat.domain.ChatRequestStatus;
import com.kakao.backend.chat.domain.ChatRoom;
import com.kakao.backend.chat.infrastructure.ChatMessageRepository;
import com.kakao.backend.chat.infrastructure.ChatRoomRepository;
import com.kakao.backend.startupProfile.model.StartupProfile;
import com.kakao.backend.user.model.User;
import com.kakao.backend.startupProfile.repository.StartupProfileRepository;
import com.kakao.backend.user.repository.UserRepository;
import com.kakao.backend.workspace.domain.Workspace;
import com.kakao.backend.workspace.application.SavedResultService;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class ChatRequestStatusLifecycleTest {

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
    private AiChatExternalReferenceDataService aiChatExternalReferenceDataService;
    @Mock
    private ChatSseService chatSseService;
    @Mock
    private ChatRequestStatusService chatRequestStatusService;
    @Mock
    private ChatCandidateAgentResolver chatCandidateAgentResolver;
    @InjectMocks
    private ChatMessageCommandService chatMessageCommandService;

    @Mock
    private com.kakao.backend.agent.infrastructure.AgentRepository agentRepository;
    @Mock
    private AiChatResponsePayloadReader aiChatResponsePayloadReader;
    @Spy
    private ObjectMapper objectMapper = new ObjectMapper();
    @Mock
    private SavedResultService savedResultService;
    @InjectMocks
    private ChatAiResponseCommandService chatAiResponseCommandService;

    @Test
    void sendCreatesQueuedRequestStatus() {
        User user = User.create("test@example.com", "tester", "USER");
        user.setId(2L);
        Workspace workspace = Workspace.create("workspace", "ACTIVE");
        workspace.setUser(user);
        ChatRoom room = ChatRoom.create(workspace, "free room", "FREE_DISCUSSION", null);
        room.setId(10L);
        ChatMessage savedMessage = ChatMessage.userMessage(room, user, "question", null);
        savedMessage.setId(100L);

        when(chatRoomRepository.findById(10L)).thenReturn(Optional.of(room));
        when(userRepository.findById(2L)).thenReturn(Optional.of(user));
        when(startupProfileRepository.findByUserId(2L)).thenReturn(Optional.of(StartupProfile.create()));
        when(chatMessageRepository.findTop20ByChatRoomIdOrderByIdDesc(10L)).thenReturn(List.of());
        when(chatMessageRepository.save(any(ChatMessage.class))).thenReturn(savedMessage);
        when(chatCandidateAgentResolver.resolve("FREE_CHAT", room, List.of()))
                .thenReturn(List.of("ProfileAgent", "IdeaAgent", "FinanceAgent"));
        when(aiChatReferenceContextService.resolve(any(AiChatDispatchCommand.class))).thenReturn(Map.of());
        when(aiChatExternalReferenceDataService.resolve(any(AiChatDispatchCommand.class))).thenReturn(Map.of());
        when(aiChatDispatchService.dispatch(any(AiChatDispatchCommand.class)))
                .thenAnswer(invocation -> invocation.getArgument(0, AiChatDispatchCommand.class).requestId());
        when(chatRequestStatusService.createQueued(any(), any(), any()))
                .thenReturn(ChatRequestStatus.create("req-123", 10L, 100L, "QUEUED"));
        when(chatCandidateAgentResolver.resolve("FREE_CHAT", room, List.of()))
                .thenReturn(List.of("ProfileAgent", "IdeaAgent", "FinanceAgent"));

        chatMessageCommandService.send(new SendChatMessageCommand(
                10L, 2L, "question", null, "auto", null, null, null, null, List.of(), Map.of()
        ));

        verify(chatRequestStatusService).createQueued(any(), org.mockito.Mockito.eq(10L), org.mockito.Mockito.eq(100L));
    }

    @Test
    void aiResponseMarksProcessingThenCompleted() {
        User user = User.create("test@example.com", "tester", "USER");
        Workspace workspace = Workspace.create("workspace", "ACTIVE");
        workspace.setUser(user);
        ChatRoom room = ChatRoom.create(workspace, "free room", "FREE_DISCUSSION", null);
        room.setId(10L);
        ChatMessage persisted = ChatMessage.agentMessage(room, null, "answer", null);
        persisted.setId(200L);

        when(chatRoomRepository.findById(10L)).thenReturn(Optional.of(room));
        when(agentRepository.findByName("IdeaAgent")).thenReturn(Optional.empty());
        when(chatMessageRepository.save(any(ChatMessage.class))).thenReturn(persisted);
        when(aiChatResponsePayloadReader.extractAgent(any(AiChatResponseMessage.class))).thenReturn("IdeaAgent");
        when(aiChatResponsePayloadReader.extractContent(any(AiChatResponseMessage.class))).thenReturn("answer");
        when(aiChatResponsePayloadReader.extractIntent(any(AiChatResponseMessage.class))).thenReturn("idea");
        when(aiChatResponsePayloadReader.extractResult(any(AiChatResponseMessage.class))).thenReturn(null);

        chatAiResponseCommandService.handle(new AiChatResponseMessage(
                "req-123", 10L, "idea", "IdeaAgent", "answer", Map.of(), List.of(), List.of(), null
        ));

        verify(chatRequestStatusService).markProcessing("req-123");
        verify(chatRequestStatusService).markCompleted("req-123");
    }
}
