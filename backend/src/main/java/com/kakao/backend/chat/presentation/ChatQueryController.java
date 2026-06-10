package com.kakao.backend.chat.presentation;

import com.kakao.backend.chat.application.ChatMessageHistoryResult;
import com.kakao.backend.chat.application.ChatRoomQueryService;
import com.kakao.backend.chat.application.FeatureChatRoomResult;
import com.kakao.backend.chat.application.FreeChatRoomResult;
import com.kakao.backend.chat.dto.ChatMessageHistoryItemResponse;
import com.kakao.backend.chat.dto.ChatMessageHistoryResponse;
import com.kakao.backend.chat.dto.FeatureChatRoomListResponse;
import com.kakao.backend.chat.dto.FeatureChatRoomResponse;
import com.kakao.backend.chat.dto.FreeChatRoomListResponse;
import com.kakao.backend.chat.dto.FreeChatRoomResponse;
import java.util.List;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/chat")
public class ChatQueryController {

    private final ChatRoomQueryService chatRoomQueryService;

    public ChatQueryController(ChatRoomQueryService chatRoomQueryService) {
        this.chatRoomQueryService = chatRoomQueryService;
    }

    @GetMapping("/free-room")
    public ResponseEntity<FreeChatRoomResponse> getFreeRoom(@RequestParam Long userId) {
        FreeChatRoomResult result = chatRoomQueryService.getOrCreateFreeRoom(userId);
        return ResponseEntity.ok(toFreeResponse(result));
    }

    @GetMapping("/feature-room")
    public ResponseEntity<FeatureChatRoomResponse> getFeatureRoom(
            @RequestParam Long userId,
            @RequestParam String targetFeature
    ) {
        FeatureChatRoomResult result = chatRoomQueryService.getOrCreateFeatureRoom(userId, targetFeature);
        return ResponseEntity.ok(toFeatureResponse(result));
    }

    @GetMapping("/free-rooms")
    public ResponseEntity<FreeChatRoomListResponse> getFreeRooms(@RequestParam Long userId) {
        List<FreeChatRoomResponse> rooms = chatRoomQueryService.getFreeRooms(userId).stream()
                .map(this::toFreeResponse)
                .toList();
        return ResponseEntity.ok(new FreeChatRoomListResponse(rooms));
    }

    @GetMapping("/feature-rooms")
    public ResponseEntity<FeatureChatRoomListResponse> getFeatureRooms(
            @RequestParam Long userId,
            @RequestParam String targetFeature
    ) {
        List<FeatureChatRoomResponse> rooms = chatRoomQueryService.getFeatureRooms(userId, targetFeature).stream()
                .map(this::toFeatureResponse)
                .toList();
        return ResponseEntity.ok(new FeatureChatRoomListResponse(rooms));
    }

    @GetMapping("/rooms/{roomId}/messages")
    public ResponseEntity<ChatMessageHistoryResponse> getMessages(
            @PathVariable Long roomId,
            @RequestParam Long userId
    ) {
        ChatMessageHistoryResult result = chatRoomQueryService.getMessageHistory(roomId, userId);
        List<ChatMessageHistoryItemResponse> messages = result.messages().stream()
                .map(message -> new ChatMessageHistoryItemResponse(
                        message.messageId(),
                        message.userId(),
                        message.agentId(),
                        message.senderType(),
                        message.content(),
                        message.metadata(),
                        message.createdAt()
                ))
                .toList();

        return ResponseEntity.ok(new ChatMessageHistoryResponse(result.roomId(), messages));
    }

    private FreeChatRoomResponse toFreeResponse(FreeChatRoomResult result) {
        return new FreeChatRoomResponse(
                result.roomId(),
                result.workspaceId(),
                result.title(),
                result.roomType(),
                result.targetFeature(),
                result.created()
        );
    }

    private FeatureChatRoomResponse toFeatureResponse(FeatureChatRoomResult result) {
        return new FeatureChatRoomResponse(
                result.roomId(),
                result.workspaceId(),
                result.title(),
                result.roomType(),
                result.targetFeature(),
                result.created()
        );
    }
}
