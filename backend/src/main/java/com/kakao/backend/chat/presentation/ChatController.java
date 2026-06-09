package com.kakao.backend.chat.presentation;

import com.kakao.backend.chat.application.ChatService;
import com.kakao.backend.chat.dto.ChatMessageResponse;
import com.kakao.backend.chat.dto.ChatRoomResponse;
import com.kakao.backend.chat.dto.CreateChatMessageRequest;
import com.kakao.backend.chat.dto.CreateChatRoomRequest;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/chat")
public class ChatController {

    private final ChatService chatService;

    public ChatController(ChatService chatService) {
        this.chatService = chatService;
    }

    @PostMapping("/rooms")
    @ResponseStatus(HttpStatus.CREATED)
    public ChatRoomResponse createRoom(@RequestBody CreateChatRoomRequest request) {
        return chatService.createRoom(request);
    }

    @GetMapping("/rooms/{roomId}")
    public ChatRoomResponse getRoom(@PathVariable Long roomId) {
        return chatService.getRoom(roomId);
    }

    @GetMapping("/workspaces/{workspaceId}/rooms")
    public List<ChatRoomResponse> getWorkspaceRooms(@PathVariable Long workspaceId) {
        return chatService.getWorkspaceRooms(workspaceId);
    }

    @GetMapping("/rooms/{roomId}/messages")
    public List<ChatMessageResponse> getMessages(@PathVariable Long roomId) {
        return chatService.getMessages(roomId);
    }

    @PostMapping("/rooms/{roomId}/messages")
    @ResponseStatus(HttpStatus.CREATED)
    public ChatMessageResponse createUserMessage(
            @PathVariable Long roomId,
            @RequestBody CreateChatMessageRequest request
    ) {
        return chatService.createUserMessage(roomId, request);
    }
}
