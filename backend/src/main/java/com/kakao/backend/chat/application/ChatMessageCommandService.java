package com.kakao.backend.chat.application;

import com.kakao.backend.aichat.application.AiChatDispatchCommand;
import com.kakao.backend.aichat.application.AiChatDispatchService;
import com.kakao.backend.aichat.application.AiChatExternalReferenceDataService;
import com.kakao.backend.aichat.application.AiChatReferenceContextService;
import com.kakao.backend.chat.domain.ChatMessage;
import com.kakao.backend.chat.domain.ChatRoom;
import com.kakao.backend.chat.infrastructure.ChatMessageRepository;
import com.kakao.backend.chat.infrastructure.ChatRoomRepository;
import com.kakao.backend.startupProfile.model.StartupProfile;
import com.kakao.backend.user.model.User;
import com.kakao.backend.startupProfile.repository.StartupProfileRepository;
import com.kakao.backend.user.repository.UserRepository;
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
    private final AiChatExternalReferenceDataService aiChatExternalReferenceDataService;
    private final ChatSseService chatSseService;
    private final ChatRequestStatusService chatRequestStatusService;
    private final ChatCandidateAgentResolver chatCandidateAgentResolver;

    public ChatMessageCommandService(
            ChatRoomRepository chatRoomRepository,
            ChatMessageRepository chatMessageRepository,
            UserRepository userRepository,
            StartupProfileRepository startupProfileRepository,
            AiChatDispatchService aiChatDispatchService,
            AiChatReferenceContextService aiChatReferenceContextService,
            AiChatExternalReferenceDataService aiChatExternalReferenceDataService,
            ChatSseService chatSseService,
            ChatRequestStatusService chatRequestStatusService,
            ChatCandidateAgentResolver chatCandidateAgentResolver
    ) {
        this.chatRoomRepository = chatRoomRepository;
        this.chatMessageRepository = chatMessageRepository;
        this.userRepository = userRepository;
        this.startupProfileRepository = startupProfileRepository;
        this.aiChatDispatchService = aiChatDispatchService;
        this.aiChatReferenceContextService = aiChatReferenceContextService;
        this.aiChatExternalReferenceDataService = aiChatExternalReferenceDataService;
        this.chatSseService = chatSseService;
        this.chatRequestStatusService = chatRequestStatusService;
        this.chatCandidateAgentResolver = chatCandidateAgentResolver;
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

        String sessionType = defaultSessionType(command.sessionType(), room);
        List<String> candidateAgents = chatCandidateAgentResolver.resolve(
                sessionType,
                room,
                command.candidateAgents()
        );

        AiChatDispatchCommand dispatchCommand = new AiChatDispatchCommand(
                requestId,
                room.getWorkspace(),
                room,
                user,
                startupProfile,
                savedMessage,
                defaultIfBlank(command.intent(), "auto"),
                sessionType,
                command.currentResultType(),
                command.currentResultId(),
                command.selectedIdeaId(),
                candidateAgents,
                recentMessages,
                command.currentResult() == null ? Map.of() : command.currentResult(),
                Map.of()
        );
        Map<String, Object> referenceData = mergedReferenceData(dispatchCommand);
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
                referenceData
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

    private Map<String, Object> mergedReferenceData(AiChatDispatchCommand command) {
        Map<String, Object> referenceData = new java.util.LinkedHashMap<>();
        Map<String, Object> savedReferenceData = aiChatReferenceContextService.resolve(command);
        if (savedReferenceData != null && !savedReferenceData.isEmpty()) {
            referenceData.putAll(savedReferenceData);
        }

        Map<String, Object> externalData = aiChatExternalReferenceDataService.resolve(command);
        if (externalData != null && !externalData.isEmpty()) {
            referenceData.put("externalData", externalData);
        }
        return referenceData;
    }
}
