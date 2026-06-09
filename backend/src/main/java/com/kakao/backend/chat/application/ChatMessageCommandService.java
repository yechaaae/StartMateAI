package com.kakao.backend.chat.application;

import com.kakao.backend.aichat.application.AiChatDispatchCommand;
import com.kakao.backend.aichat.application.AiChatDispatchService;
import com.kakao.backend.aichat.application.AiChatReferenceContextService;
import com.kakao.backend.chat.domain.ChatMessage;
import com.kakao.backend.chat.domain.ChatRoom;
import com.kakao.backend.chat.infrastructure.ChatMessageRepository;
import com.kakao.backend.chat.infrastructure.ChatRoomRepository;
import com.kakao.backend.user.domain.StartupProfile;
import com.kakao.backend.user.domain.User;
import com.kakao.backend.user.infrastructure.StartupProfileRepository;
import com.kakao.backend.user.infrastructure.UserRepository;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional
public class ChatMessageCommandService {

    private final ChatRoomRepository chatRoomRepository;
    private final ChatMessageRepository chatMessageRepository;
    private final UserRepository userRepository;
    private final StartupProfileRepository startupProfileRepository;
    private final AiChatDispatchService aiChatDispatchService;
    private final AiChatReferenceContextService aiChatReferenceContextService;
    private final ChatSseService chatSseService;
    private final ChatRequestStatusService chatRequestStatusService;

    public ChatMessageCommandService(
            ChatRoomRepository chatRoomRepository,
            ChatMessageRepository chatMessageRepository,
            UserRepository userRepository,
            StartupProfileRepository startupProfileRepository,
            AiChatDispatchService aiChatDispatchService,
            AiChatReferenceContextService aiChatReferenceContextService,
            ChatSseService chatSseService,
            ChatRequestStatusService chatRequestStatusService
    ) {
        this.chatRoomRepository = chatRoomRepository;
        this.chatMessageRepository = chatMessageRepository;
        this.userRepository = userRepository;
        this.startupProfileRepository = startupProfileRepository;
        this.aiChatDispatchService = aiChatDispatchService;
        this.aiChatReferenceContextService = aiChatReferenceContextService;
        this.chatSseService = chatSseService;
        this.chatRequestStatusService = chatRequestStatusService;
    }

    public ChatMessageSendResult send(SendChatMessageCommand command) {
        ChatRoom room = chatRoomRepository.findById(command.roomId())
                .orElseThrow(() -> new IllegalArgumentException("Chat room not found."));

        User user = userRepository.findById(command.userId())
                .orElseThrow(() -> new IllegalArgumentException("User not found."));

        validateRoomOwnership(room, user);

        StartupProfile startupProfile = startupProfileRepository.findByUserId(user.getId()).orElse(null);
        List<ChatMessage> recentMessages = toChronologicalOrder(
                chatMessageRepository.findTop20ByChatRoomIdOrderByIdDesc(room.getId())
        );

        ChatMessage message = ChatMessage.userMessage(room, user, command.content(), command.metadata());
        ChatMessage savedMessage = chatMessageRepository.save(message);
        chatSseService.publish(savedMessage);

        String requestId = UUID.randomUUID().toString();
        chatRequestStatusService.createQueued(requestId, room.getId(), savedMessage.getId());

        AiChatDispatchCommand dispatchCommand = new AiChatDispatchCommand(
                requestId,
                room.getWorkspace(),
                room,
                user,
                startupProfile,
                savedMessage,
                defaultIfBlank(command.intent(), "auto"),
                defaultSessionType(command.sessionType(), room),
                command.currentResultType(),
                command.currentResultId(),
                command.selectedIdeaId(),
                command.candidateAgents() == null ? List.of() : List.copyOf(command.candidateAgents()),
                recentMessages,
                command.currentResult() == null ? Map.of() : command.currentResult(),
                Map.of()
        );
        dispatchCommand = new AiChatDispatchCommand(
                dispatchCommand.requestId(),
                dispatchCommand.workspace(),
                dispatchCommand.room(),
                dispatchCommand.user(),
                dispatchCommand.startupProfile(),
                dispatchCommand.message(),
                dispatchCommand.intent(),
                dispatchCommand.sessionType(),
                dispatchCommand.currentResultType(),
                dispatchCommand.currentResultId(),
                dispatchCommand.selectedIdeaId(),
                dispatchCommand.candidateAgents(),
                dispatchCommand.recentMessages(),
                dispatchCommand.currentResult(),
                aiChatReferenceContextService.resolve(dispatchCommand)
        );

        try {
            String dispatchedRequestId = aiChatDispatchService.dispatch(dispatchCommand);
            requestId = dispatchedRequestId;
        } catch (RuntimeException exception) {
            chatRequestStatusService.markFailed(requestId, exception.getMessage());
            throw exception;
        }

        return new ChatMessageSendResult(
                requestId,
                room.getId(),
                savedMessage.getId(),
                savedMessage.getSenderType(),
                savedMessage.getContent()
        );
    }

    private void validateRoomOwnership(ChatRoom room, User user) {
        if (room.getWorkspace() == null || room.getWorkspace().getUser() == null) {
            throw new IllegalArgumentException("Chat room workspace owner is missing.");
        }
        if (!room.getWorkspace().getUser().getId().equals(user.getId())) {
            throw new IllegalArgumentException("User cannot send message to this room.");
        }
    }

    private List<ChatMessage> toChronologicalOrder(List<ChatMessage> messages) {
        List<ChatMessage> ordered = new ArrayList<>(messages);
        ordered.sort((left, right) -> Long.compare(left.getId(), right.getId()));
        return List.copyOf(ordered);
    }

    private String defaultIfBlank(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }

    private String defaultSessionType(String sessionType, ChatRoom room) {
        if (sessionType != null && !sessionType.isBlank()) {
            return sessionType;
        }
        return room.getTargetFeature() == null || room.getTargetFeature().isBlank()
                ? "FREE_CHAT"
                : "FEATURE_CHAT";
    }
}
