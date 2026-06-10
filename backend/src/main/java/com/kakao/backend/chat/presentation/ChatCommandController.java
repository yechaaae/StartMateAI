package com.kakao.backend.chat.presentation;

import com.kakao.backend.chat.application.ChatMessageCommandService;
import com.kakao.backend.chat.application.ChatMessageSendResult;
import com.kakao.backend.chat.application.ChatRoomQueryService;
import com.kakao.backend.chat.application.SendChatMessageCommand;
import com.kakao.backend.chat.dto.ChatMessageSendResponse;
import com.kakao.backend.chat.dto.CreateFeatureChatRoomRequest;
import com.kakao.backend.chat.dto.CreateFreeChatRoomRequest;
import com.kakao.backend.chat.dto.FeatureChatRoomResponse;
import com.kakao.backend.chat.dto.FreeChatRoomResponse;
import com.kakao.backend.chat.dto.SendChatMessageRequest;
import com.kakao.backend.chat.dto.UpdateChatRoomTitleRequest;
import com.kakao.backend.chat.dto.UpdateFeatureChatRoomTitleRequest;
import com.kakao.backend.common.presentation.LoginUserSessionResolver;
import jakarta.servlet.http.HttpSession;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/chat")
public class ChatCommandController {

    private final ChatMessageCommandService chatMessageCommandService;
    private final ChatRoomQueryService chatRoomQueryService;
    private final LoginUserSessionResolver loginUserSessionResolver;

    public ChatCommandController(
            ChatMessageCommandService chatMessageCommandService,
            ChatRoomQueryService chatRoomQueryService,
            LoginUserSessionResolver loginUserSessionResolver
    ) {
        this.chatMessageCommandService = chatMessageCommandService;
        this.chatRoomQueryService = chatRoomQueryService;
        this.loginUserSessionResolver = loginUserSessionResolver;
    }

    @PostMapping("/free-rooms")
    public ResponseEntity<FreeChatRoomResponse> createFreeRoom(
            @RequestBody(required = false) CreateFreeChatRoomRequest request,
            HttpSession session
    ) {
        var result = chatRoomQueryService.createNewFreeRoom(loginUserSessionResolver.resolve(session));
        return ResponseEntity.status(HttpStatus.CREATED).body(new FreeChatRoomResponse(
                result.roomId(),
                result.workspaceId(),
                result.title(),
                result.roomType(),
                result.targetFeature(),
                result.created()
        ));
    }

    @PostMapping("/feature-rooms")
    public ResponseEntity<FeatureChatRoomResponse> createFeatureRoom(
            @RequestBody CreateFeatureChatRoomRequest request,
            HttpSession session
    ) {
        var result = chatRoomQueryService.createNewFeatureRoom(
                loginUserSessionResolver.resolve(session),
                request.targetFeature()
        );
        return ResponseEntity.status(HttpStatus.CREATED).body(new FeatureChatRoomResponse(
                result.roomId(),
                result.workspaceId(),
                result.title(),
                result.roomType(),
                result.targetFeature(),
                result.created()
        ));
    }

    @PatchMapping("/free-rooms/{roomId}")
    public ResponseEntity<FreeChatRoomResponse> updateFreeRoomTitle(
            @PathVariable Long roomId,
            @RequestBody UpdateChatRoomTitleRequest request,
            HttpSession session
    ) {
        var result = chatRoomQueryService.updateFreeRoomTitle(
                roomId,
                loginUserSessionResolver.resolve(session),
                request.title()
        );
        return ResponseEntity.ok(new FreeChatRoomResponse(
                result.roomId(),
                result.workspaceId(),
                result.title(),
                result.roomType(),
                result.targetFeature(),
                result.created()
        ));
    }

    @PatchMapping("/feature-rooms/{roomId}")
    public ResponseEntity<FeatureChatRoomResponse> updateFeatureRoomTitle(
            @PathVariable Long roomId,
            @RequestBody UpdateFeatureChatRoomTitleRequest request,
            HttpSession session
    ) {
        var result = chatRoomQueryService.updateFeatureRoomTitle(
                roomId,
                loginUserSessionResolver.resolve(session),
                request.targetFeature(),
                request.title()
        );
        return ResponseEntity.ok(new FeatureChatRoomResponse(
                result.roomId(),
                result.workspaceId(),
                result.title(),
                result.roomType(),
                result.targetFeature(),
                result.created()
        ));
    }

    @PostMapping("/rooms/{roomId}/messages")
    public ResponseEntity<ChatMessageSendResponse> sendMessage(
            @PathVariable Long roomId,
            @RequestBody SendChatMessageRequest request,
            HttpSession session
    ) {
        ChatMessageSendResult result = chatMessageCommandService.send(new SendChatMessageCommand(
                roomId,
                loginUserSessionResolver.resolve(session),
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
