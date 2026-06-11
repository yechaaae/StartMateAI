package com.kakao.backend.chat.presentation;

import com.kakao.backend.chat.application.ChatSseService;
import com.kakao.backend.common.presentation.LoginUserSessionResolver;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@RestController
@RequestMapping("/chat/rooms")
public class ChatStreamController {

    private final ChatSseService chatSseService;
    private final LoginUserSessionResolver loginUserSessionResolver;

    public ChatStreamController(
            ChatSseService chatSseService,
            LoginUserSessionResolver loginUserSessionResolver
    ) {
        this.chatSseService = chatSseService;
        this.loginUserSessionResolver = loginUserSessionResolver;
    }

    @GetMapping("/{roomId}/stream")
    public SseEmitter subscribe(
            @PathVariable Long roomId,
            HttpSession session
    ) {
        return chatSseService.subscribe(roomId, loginUserSessionResolver.resolve(session));
    }
}
