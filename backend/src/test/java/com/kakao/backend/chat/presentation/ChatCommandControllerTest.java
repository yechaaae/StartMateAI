package com.kakao.backend.chat.presentation;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import com.kakao.backend.chat.application.ChatMessageCommandService;
import com.kakao.backend.chat.application.ChatMessageSendResult;
import com.kakao.backend.chat.application.ChatRoomQueryService;
import com.kakao.backend.chat.application.FeatureChatRoomResult;
import com.kakao.backend.chat.application.FreeChatRoomResult;
import com.kakao.backend.chat.dto.ChatMessageSendResponse;
import com.kakao.backend.chat.dto.CreateFeatureChatRoomRequest;
import com.kakao.backend.chat.dto.FeatureChatRoomResponse;
import com.kakao.backend.chat.dto.FreeChatRoomResponse;
import com.kakao.backend.chat.dto.SendChatMessageRequest;
import com.kakao.backend.chat.dto.UpdateChatRoomTitleRequest;
import com.kakao.backend.chat.dto.UpdateFeatureChatRoomTitleRequest;
import com.kakao.backend.common.presentation.LoginUserSessionResolver;
import jakarta.servlet.http.HttpSession;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class ChatCommandControllerTest {

    @Mock
    private ChatMessageCommandService chatMessageCommandService;

    @Mock
    private ChatRoomQueryService chatRoomQueryService;

    @Mock
    private LoginUserSessionResolver loginUserSessionResolver;

    @Mock
    private HttpSession session;

    @InjectMocks
    private ChatCommandController chatCommandController;

    @Test
    void sendsMessageThroughCommandService() {
        when(loginUserSessionResolver.resolve(session)).thenReturn(2L);
        when(chatMessageCommandService.send(any())).thenReturn(
                new ChatMessageSendResult("req-123", 10L, 100L, "USER", "recommend an idea")
        );

        SendChatMessageRequest request = new SendChatMessageRequest(
                null,
                "recommend an idea",
                "{\"source\":\"chat\"}",
                "idea",
                "FEATURE_CHAT",
                "IDEA_REPORT",
                44L,
                9L,
                List.of("IdeaAgent", "FinanceAgent"),
                Map.of("selectedOption", "A")
        );

        ChatMessageSendResponse response = chatCommandController.sendMessage(10L, request, session).getBody();

        assertThat(response).isNotNull();
        assertThat(response.requestId()).isEqualTo("req-123");
        assertThat(response.roomId()).isEqualTo(10L);
        assertThat(response.messageId()).isEqualTo(100L);
        assertThat(response.senderType()).isEqualTo("USER");
        assertThat(response.content()).isEqualTo("recommend an idea");
    }

    @Test
    void createsFeatureRoom() {
        when(loginUserSessionResolver.resolve(session)).thenReturn(2L);
        when(chatRoomQueryService.createNewFeatureRoom(2L, "ITEM"))
                .thenReturn(new FeatureChatRoomResult(20L, 1L, "Item recommendation", "FEATURE_DISCUSSION", "ITEM", true));

        FeatureChatRoomResponse response = chatCommandController.createFeatureRoom(
                new CreateFeatureChatRoomRequest(null, "ITEM"),
                session
        ).getBody();

        assertThat(response).isNotNull();
        assertThat(response.roomId()).isEqualTo(20L);
        assertThat(response.targetFeature()).isEqualTo("ITEM");
        assertThat(response.created()).isTrue();
    }

    @Test
    void updatesFreeRoomTitle() {
        when(loginUserSessionResolver.resolve(session)).thenReturn(2L);
        when(chatRoomQueryService.updateFreeRoomTitle(10L, 2L, "Investor Q&A"))
                .thenReturn(new FreeChatRoomResult(10L, 1L, "Investor Q&A", "FREE_DISCUSSION", null, false));

        FreeChatRoomResponse response = chatCommandController.updateFreeRoomTitle(
                10L,
                new UpdateChatRoomTitleRequest(null, "Investor Q&A"),
                session
        ).getBody();

        assertThat(response).isNotNull();
        assertThat(response.roomId()).isEqualTo(10L);
        assertThat(response.title()).isEqualTo("Investor Q&A");
        assertThat(response.created()).isFalse();
    }

    @Test
    void updatesFeatureRoomTitle() {
        when(loginUserSessionResolver.resolve(session)).thenReturn(2L);
        when(chatRoomQueryService.updateFeatureRoomTitle(20L, 2L, "ITEM", "Cookie idea branch"))
                .thenReturn(new FeatureChatRoomResult(20L, 1L, "Cookie idea branch", "FEATURE_DISCUSSION", "ITEM", false));

        FeatureChatRoomResponse response = chatCommandController.updateFeatureRoomTitle(
                20L,
                new UpdateFeatureChatRoomTitleRequest(null, "ITEM", "Cookie idea branch"),
                session
        ).getBody();

        assertThat(response).isNotNull();
        assertThat(response.roomId()).isEqualTo(20L);
        assertThat(response.title()).isEqualTo("Cookie idea branch");
        assertThat(response.targetFeature()).isEqualTo("ITEM");
    }
}
