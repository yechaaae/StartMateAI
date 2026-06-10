package com.kakao.backend.chat.presentation;

import com.kakao.backend.chat.application.ChatSseService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@RestController
@RequestMapping("/api/chat/rooms")
public class ChatStreamController {

    private final ChatSseService chatSseService;

    public ChatStreamController(ChatSseService chatSseService) {
        this.chatSseService = chatSseService;
    }

    @GetMapping("/{roomId}/stream")
    public SseEmitter subscribe(
            @PathVariable Long roomId,
            @RequestParam Long userId
    ) {
        return chatSseService.subscribe(roomId, userId);
    }
}
