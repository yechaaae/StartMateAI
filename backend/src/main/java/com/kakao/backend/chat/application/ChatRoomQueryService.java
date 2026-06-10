package com.kakao.backend.chat.application;

import com.kakao.backend.chat.domain.ChatMessage;
import com.kakao.backend.chat.domain.ChatRoom;
import com.kakao.backend.chat.infrastructure.ChatMessageRepository;
import com.kakao.backend.chat.infrastructure.ChatRoomRepository;
import com.kakao.backend.user.model.User;
import com.kakao.backend.user.repository.UserRepository;
import com.kakao.backend.workspace.domain.Workspace;
import com.kakao.backend.workspace.infrastructure.WorkspaceRepository;
import java.time.format.DateTimeFormatter;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class ChatRoomQueryService {

    private static final DateTimeFormatter FORMATTER = DateTimeFormatter.ISO_LOCAL_DATE_TIME;
    private static final String FREE_DISCUSSION = "FREE_DISCUSSION";

    private final ChatRoomRepository chatRoomRepository;
    private final ChatMessageRepository chatMessageRepository;
    private final UserRepository userRepository;
    private final WorkspaceRepository workspaceRepository;

    public ChatRoomQueryService(
            ChatRoomRepository chatRoomRepository,
            ChatMessageRepository chatMessageRepository,
            UserRepository userRepository,
            WorkspaceRepository workspaceRepository
    ) {
        this.chatRoomRepository = chatRoomRepository;
        this.chatMessageRepository = chatMessageRepository;
        this.userRepository = userRepository;
        this.workspaceRepository = workspaceRepository;
    }

    @Transactional
    public FreeChatRoomResult getOrCreateFreeRoom(Long userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found."));

        return chatRoomRepository.findFirstByWorkspaceUserIdAndRoomTypeOrderByIdDesc(userId, FREE_DISCUSSION)
                .map(room -> toFreeRoomResult(room, false))
                .orElseGet(() -> createFreeRoom(user));
    }

    public List<FreeChatRoomResult> getFreeRooms(Long userId) {
        userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found."));

        return chatRoomRepository.findByWorkspaceUserIdAndRoomTypeOrderByIdDesc(userId, FREE_DISCUSSION).stream()
                .map(room -> toFreeRoomResult(room, false))
                .toList();
    }

    @Transactional
    public FreeChatRoomResult createNewFreeRoom(Long userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found."));
        return createFreeRoom(user);
    }

    @Transactional
    public FreeChatRoomResult updateFreeRoomTitle(Long roomId, Long userId, String title) {
        ChatRoom room = chatRoomRepository.findById(roomId)
                .orElseThrow(() -> new IllegalArgumentException("Chat room not found."));

        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found."));

        validateRoomOwnership(room, user);
        validateFreeDiscussionRoom(room);

        String normalizedTitle = normalizeTitle(title);
        room.rename(normalizedTitle);

        return toFreeRoomResult(room, false);
    }

    public ChatMessageHistoryResult getMessageHistory(Long roomId, Long userId) {
        ChatRoom room = chatRoomRepository.findById(roomId)
                .orElseThrow(() -> new IllegalArgumentException("Chat room not found."));

        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found."));

        validateRoomOwnership(room, user);

        List<ChatMessageHistoryItemResult> messages = chatMessageRepository.findByChatRoomIdOrderByIdAsc(roomId).stream()
                .map(this::toHistoryItem)
                .toList();

        return new ChatMessageHistoryResult(roomId, messages);
    }

    private FreeChatRoomResult createFreeRoom(User user) {
        Workspace workspace = workspaceRepository.findFirstByUserIdAndStatusOrderByIdAsc(user.getId(), "ACTIVE")
                .orElseGet(() -> {
                    Workspace created = Workspace.create("Free discussion workspace", "ACTIVE");
                    created.setUser(user);
                    return workspaceRepository.save(created);
                });

        int existingCount = chatRoomRepository.findByWorkspaceUserIdAndRoomTypeOrderByIdDesc(user.getId(), FREE_DISCUSSION).size();
        String title = existingCount == 0 ? "Free discussion" : "Free discussion " + (existingCount + 1);

        ChatRoom room = ChatRoom.create(workspace, title, FREE_DISCUSSION, null);
        ChatRoom saved = chatRoomRepository.save(room);
        return toFreeRoomResult(saved, true);
    }

    private void validateFreeDiscussionRoom(ChatRoom room) {
        if (!FREE_DISCUSSION.equals(room.getRoomType())) {
            throw new IllegalArgumentException("Only free discussion rooms can be renamed here.");
        }
    }

    private String normalizeTitle(String title) {
        if (title == null) {
            throw new IllegalArgumentException("Chat room title is required.");
        }

        String normalized = title.trim();
        if (normalized.isBlank()) {
            throw new IllegalArgumentException("Chat room title is required.");
        }
        if (normalized.length() > 60) {
            throw new IllegalArgumentException("Chat room title must be 60 characters or fewer.");
        }
        return normalized;
    }

    private FreeChatRoomResult toFreeRoomResult(ChatRoom room, boolean created) {
        return new FreeChatRoomResult(
                room.getId(),
                room.getWorkspace() != null ? room.getWorkspace().getId() : null,
                room.getTitle(),
                room.getRoomType(),
                room.getTargetFeature(),
                created
        );
    }

    private ChatMessageHistoryItemResult toHistoryItem(ChatMessage message) {
        return new ChatMessageHistoryItemResult(
                message.getId(),
                message.getUser() != null ? message.getUser().getId() : null,
                message.getAgent() != null ? message.getAgent().getId() : null,
                message.getSenderType(),
                message.getContent(),
                message.getMetadata(),
                message.getCreatedAt() != null ? message.getCreatedAt().format(FORMATTER) : null
        );
    }

    private void validateRoomOwnership(ChatRoom room, User user) {
        if (room.getWorkspace() == null || room.getWorkspace().getUser() == null) {
            throw new IllegalArgumentException("Chat room workspace owner is missing.");
        }
        if (!room.getWorkspace().getUser().getId().equals(user.getId())) {
            throw new IllegalArgumentException("User cannot access this room.");
        }
    }
}
