package com.kakao.backend.chat.application;

import com.kakao.backend.chat.dto.ChatMessageResponse;
import com.kakao.backend.chat.dto.ChatRoomResponse;
import com.kakao.backend.chat.dto.CreateChatMessageRequest;
import com.kakao.backend.chat.dto.CreateChatRoomRequest;
import com.kakao.backend.chat.infrastructure.ChatMessageRepository;
import com.kakao.backend.chat.infrastructure.ChatRoomRepository;
import com.kakao.backend.domain.ChatMessage;
import com.kakao.backend.domain.ChatRoom;
import com.kakao.backend.domain.User;
import com.kakao.backend.domain.Workspace;
import com.kakao.backend.workspace.infrastructure.UserRepository;
import com.kakao.backend.workspace.infrastructure.WorkspaceRepository;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class ChatService {

    private final ChatRoomRepository chatRoomRepository;
    private final ChatMessageRepository chatMessageRepository;
    private final WorkspaceRepository workspaceRepository;
    private final UserRepository userRepository;

    public ChatService(
            ChatRoomRepository chatRoomRepository,
            ChatMessageRepository chatMessageRepository,
            WorkspaceRepository workspaceRepository,
            UserRepository userRepository
    ) {
        this.chatRoomRepository = chatRoomRepository;
        this.chatMessageRepository = chatMessageRepository;
        this.workspaceRepository = workspaceRepository;
        this.userRepository = userRepository;
    }

    @Transactional
    public ChatRoomResponse createRoom(CreateChatRoomRequest request) {
        Workspace workspace = workspaceRepository.findById(request.workspaceId())
                .orElseThrow(() -> new IllegalArgumentException("Workspace not found: " + request.workspaceId()));

        ChatRoom room = ChatRoom.create(
                workspace,
                request.title(),
                request.roomType(),
                request.targetFeature()
        );

        return toResponse(chatRoomRepository.save(room));
    }

    public ChatRoomResponse getRoom(Long roomId) {
        return toResponse(findRoom(roomId));
    }

    public List<ChatRoomResponse> getWorkspaceRooms(Long workspaceId) {
        return chatRoomRepository.findByWorkspaceIdOrderByCreatedAtAsc(workspaceId).stream()
                .map(this::toResponse)
                .toList();
    }

    public List<ChatMessageResponse> getMessages(Long roomId) {
        findRoom(roomId);
        return chatMessageRepository.findByChatRoomIdOrderByCreatedAtAsc(roomId).stream()
                .map(this::toResponse)
                .toList();
    }

    @Transactional
    public ChatMessageResponse createUserMessage(Long roomId, CreateChatMessageRequest request) {
        ChatRoom room = findRoom(roomId);
        User user = userRepository.findById(request.userId())
                .orElseThrow(() -> new IllegalArgumentException("User not found: " + request.userId()));

        ChatMessage message = ChatMessage.userMessage(room, user, request.content(), request.metadata());

        return toResponse(chatMessageRepository.save(message));
    }

    @Transactional
    public ChatMessageResponse createAgentMessage(
            Long roomId,
            Long agentId,
            String content,
            String metadata
    ) {
        ChatRoom room = findRoom(roomId);
        ChatMessage message = ChatMessage.agentMessage(room, agentId != null ? com.kakao.backend.domain.Agent.reference(agentId) : null, content, metadata);

        return toResponse(chatMessageRepository.save(message));
    }

    private ChatRoom findRoom(Long roomId) {
        return chatRoomRepository.findById(roomId)
                .orElseThrow(() -> new IllegalArgumentException("Chat room not found: " + roomId));
    }

    private ChatRoomResponse toResponse(ChatRoom room) {
        return new ChatRoomResponse(
                room.getId(),
                room.getWorkspace().getId(),
                room.getTitle(),
                room.getRoomType(),
                room.getTargetFeature()
        );
    }

    private ChatMessageResponse toResponse(ChatMessage message) {
        return new ChatMessageResponse(
                message.getId(),
                message.getChatRoom().getId(),
                message.getUser() != null ? message.getUser().getId() : null,
                message.getAgent() != null ? message.getAgent().getId() : null,
                message.getSenderType(),
                message.getContent(),
                message.getMetadata(),
                message.getCreatedAt()
        );
    }
}
