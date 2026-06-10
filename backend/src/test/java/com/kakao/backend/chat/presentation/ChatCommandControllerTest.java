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

    @InjectMocks
    private ChatCommandController chatCommandController;

    @Test
    void sendsMessageThroughCommandService() {
        when(chatMessageCommandService.send(any())).thenReturn(
                new ChatMessageSendResult("req-123", 10L, 100L, "USER", "아이템 추천해줘")
        );

        SendChatMessageRequest request = new SendChatMessageRequest(
                2L,
                "아이템 추천해줘",
                "{\"source\":\"chat\"}",
                "idea",
                "FEATURE_CHAT",
                "IDEA_REPORT",
                44L,
                9L,
                List.of("IdeaAgent", "FinanceAgent"),
                Map.of("selectedOption", "A")
        );

        ChatMessageSendResponse response = chatCommandController.sendMessage(10L, request).getBody();

        assertThat(response).isNotNull();
        assertThat(response.requestId()).isEqualTo("req-123");
        assertThat(response.roomId()).isEqualTo(10L);
        assertThat(response.messageId()).isEqualTo(100L);
        assertThat(response.senderType()).isEqualTo("USER");
        assertThat(response.content()).isEqualTo("아이템 추천해줘");
    }

    @Test
    void createsFeatureRoom() {
        when(chatRoomQueryService.createNewFeatureRoom(2L, "ITEM"))
                .thenReturn(new FeatureChatRoomResult(20L, 1L, "Item recommendation", "FEATURE_DISCUSSION", "ITEM", true));

        FeatureChatRoomResponse response = chatCommandController.createFeatureRoom(
                new CreateFeatureChatRoomRequest(2L, "ITEM")
        ).getBody();

        assertThat(response).isNotNull();
        assertThat(response.roomId()).isEqualTo(20L);
        assertThat(response.targetFeature()).isEqualTo("ITEM");
        assertThat(response.created()).isTrue();
    }

    @Test
    void updatesFreeRoomTitle() {
        when(chatRoomQueryService.updateFreeRoomTitle(10L, 2L, "Investor Q&A"))
                .thenReturn(new FreeChatRoomResult(10L, 1L, "Investor Q&A", "FREE_DISCUSSION", null, false));

        FreeChatRoomResponse response = chatCommandController.updateFreeRoomTitle(
                10L,
                new UpdateChatRoomTitleRequest(2L, "Investor Q&A")
        ).getBody();

        assertThat(response).isNotNull();
        assertThat(response.roomId()).isEqualTo(10L);
        assertThat(response.title()).isEqualTo("Investor Q&A");
        assertThat(response.created()).isFalse();
    }

    @Test
    void updatesFeatureRoomTitle() {
        when(chatRoomQueryService.updateFeatureRoomTitle(20L, 2L, "ITEM", "쿠키 아이템 브랜치"))
                .thenReturn(new FeatureChatRoomResult(20L, 1L, "쿠키 아이템 브랜치", "FEATURE_DISCUSSION", "ITEM", false));

        FeatureChatRoomResponse response = chatCommandController.updateFeatureRoomTitle(
                20L,
                new UpdateFeatureChatRoomTitleRequest(2L, "ITEM", "쿠키 아이템 브랜치")
        ).getBody();

        assertThat(response).isNotNull();
        assertThat(response.roomId()).isEqualTo(20L);
        assertThat(response.title()).isEqualTo("쿠키 아이템 브랜치");
        assertThat(response.targetFeature()).isEqualTo("ITEM");
    }
}
