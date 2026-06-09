package com.kakao.backend.chat.application;

import com.kakao.backend.chat.domain.ChatMessage;
import com.kakao.backend.chat.domain.ChatRequestStatus;
import com.kakao.backend.chat.domain.ChatRoom;
import com.kakao.backend.chat.dto.ChatStreamEventResponse;
import com.kakao.backend.chat.infrastructure.ChatRoomRepository;
import com.kakao.backend.user.model.User;
import com.kakao.backend.user.repository.UserRepository;
import java.io.IOException;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@Service
public class ChatSseService {

    private static final Long DEFAULT_TIMEOUT = 60L * 60L * 1000L;

    private final ChatRoomRepository chatRoomRepository;
    private final UserRepository userRepository;
    private final ChatStreamEventFactory chatStreamEventFactory;
    private final Map<Long, Map<String, SseEmitter>> emittersByRoom = new ConcurrentHashMap<>();

    public ChatSseService(
            ChatRoomRepository chatRoomRepository,
            UserRepository userRepository,
            ChatStreamEventFactory chatStreamEventFactory
    ) {
        this.chatRoomRepository = chatRoomRepository;
        this.userRepository = userRepository;
        this.chatStreamEventFactory = chatStreamEventFactory;
    }

    public SseEmitter subscribe(Long roomId, Long userId) {
        ChatRoom room = chatRoomRepository.findById(roomId)
                .orElseThrow(() -> new IllegalArgumentException("Chat room not found."));

        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found."));

        validateRoomOwnership(room, user);

        SseEmitter emitter = new SseEmitter(DEFAULT_TIMEOUT);
        String emitterId = UUID.randomUUID().toString();

        emittersByRoom
                .computeIfAbsent(roomId, key -> new ConcurrentHashMap<>())
                .put(emitterId, emitter);

        emitter.onCompletion(() -> remove(roomId, emitterId));
        emitter.onTimeout(() -> remove(roomId, emitterId));
        emitter.onError(ex -> remove(roomId, emitterId));

        sendEvent(emitter, emitterId, roomId, "chat-connected", chatStreamEventFactory.connectedEvent(roomId));

        return emitter;
    }

    public void publish(ChatMessage message) {
        if (message == null || message.getChatRoom() == null || message.getChatRoom().getId() == null) {
            return;
        }

        Long roomId = message.getChatRoom().getId();
        Map<String, SseEmitter> roomEmitters = emittersByRoom.get(roomId);
        if (roomEmitters == null || roomEmitters.isEmpty()) {
            return;
        }

        ChatStreamEventResponse response = chatStreamEventFactory.messageEvent(message);

        roomEmitters.forEach((emitterId, emitter) -> {
            sendEvent(emitter, emitterId, roomId, "chat-message", response);
        });
    }

    public void publishStatus(ChatRequestStatus status) {
        if (status == null || status.getRoomId() == null) {
            return;
        }

        Map<String, SseEmitter> roomEmitters = emittersByRoom.get(status.getRoomId());
        if (roomEmitters == null || roomEmitters.isEmpty()) {
            return;
        }

        ChatStreamEventResponse response = chatStreamEventFactory.statusEvent(status);
        roomEmitters.forEach((emitterId, emitter) ->
                sendEvent(emitter, emitterId, status.getRoomId(), "chat-status", response));
    }

    private void sendEvent(SseEmitter emitter, String emitterId, Long roomId, String eventName, Object response) {
        try {
            emitter.send(SseEmitter.event()
                    .name(eventName)
                    .data(response));
        } catch (IOException | IllegalStateException exception) {
            remove(roomId, emitterId);
        }
    }

    private void validateRoomOwnership(ChatRoom room, User user) {
        if (room.getWorkspace() == null || room.getWorkspace().getUser() == null) {
            throw new IllegalArgumentException("Chat room workspace owner is missing.");
        }
        if (!room.getWorkspace().getUser().getId().equals(user.getId())) {
            throw new IllegalArgumentException("User cannot subscribe to this room.");
        }
    }

    private void remove(Long roomId, String emitterId) {
        Map<String, SseEmitter> roomEmitters = emittersByRoom.get(roomId);
        if (roomEmitters == null) {
            return;
        }
        roomEmitters.remove(emitterId);
        if (roomEmitters.isEmpty()) {
            emittersByRoom.remove(roomId);
        }
    }
}
