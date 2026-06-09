package com.kakao.backend.chat.presentation;

import com.kakao.backend.chat.application.ChatMessageCommandService;
import com.kakao.backend.chat.application.ChatMessageSendResult;
import com.kakao.backend.chat.application.SendChatMessageCommand;
import com.kakao.backend.chat.dto.ChatMessageSendResponse;
import com.kakao.backend.chat.dto.SendChatMessageRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/chat/rooms")
public class ChatCommandController {

    private final ChatMessageCommandService chatMessageCommandService;

    public ChatCommandController(ChatMessageCommandService chatMessageCommandService) {
        this.chatMessageCommandService = chatMessageCommandService;
    }

    @PostMapping("/{roomId}/messages")
    public ResponseEntity<ChatMessageSendResponse> sendMessage(
            @PathVariable Long roomId,
            @RequestBody SendChatMessageRequest request
    ) {
        ChatMessageSendResult result = chatMessageCommandService.send(new SendChatMessageCommand(
                roomId,
                request.userId(),
                request.content(),
                request.metadata(),
                request.intent(),
                request.sessionType(),
                request.currentResultType(),
                request.currentResultId(),
                request.selectedIdeaId(),
                request.candidateAgents(),
                request.currentResult()
        ));

        return ResponseEntity.status(HttpStatus.ACCEPTED).body(new ChatMessageSendResponse(
                result.requestId(),
                result.roomId(),
                result.messageId(),
                result.senderType(),
                result.content()
        ));
    }
}
