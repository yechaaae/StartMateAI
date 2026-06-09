package com.kakao.backend.chat.presentation;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import com.kakao.backend.chat.application.ChatMessageHistoryItemResult;
import com.kakao.backend.chat.application.ChatMessageHistoryResult;
import com.kakao.backend.chat.application.ChatRoomQueryService;
import com.kakao.backend.chat.application.FreeChatRoomResult;
import com.kakao.backend.chat.dto.ChatMessageHistoryResponse;
import com.kakao.backend.chat.dto.FreeChatRoomResponse;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class ChatQueryControllerTest {

    @Mock
    private ChatRoomQueryService chatRoomQueryService;

    @InjectMocks
    private ChatQueryController chatQueryController;

    @Test
    void getsOrCreatesFreeRoom() {
        when(chatRoomQueryService.getOrCreateFreeRoom(2L))
                .thenReturn(new FreeChatRoomResult(10L, 1L, "자유 상담실", "FREE_DISCUSSION", null, true));

        FreeChatRoomResponse response = chatQueryController.getFreeRoom(2L).getBody();

        assertThat(response).isNotNull();
        assertThat(response.roomId()).isEqualTo(10L);
        assertThat(response.workspaceId()).isEqualTo(1L);
        assertThat(response.created()).isTrue();
    }

    @Test
    void getsMessageHistory() {
        when(chatRoomQueryService.getMessageHistory(10L, 2L)).thenReturn(
                new ChatMessageHistoryResult(
                        10L,
                        List.of(
                                new ChatMessageHistoryItemResult(100L, 2L, null, "USER", "안녕", null, null),
                                new ChatMessageHistoryItemResult(101L, null, 5L, "AGENT", "무엇을 도와줄까?", "{\"requestId\":\"req-1\"}", null)
                        )
                )
        );

        ChatMessageHistoryResponse response = chatQueryController.getMessages(10L, 2L).getBody();

        assertThat(response).isNotNull();
        assertThat(response.roomId()).isEqualTo(10L);
        assertThat(response.messages()).hasSize(2);
        assertThat(response.messages().get(1).senderType()).isEqualTo("AGENT");
    }
}
