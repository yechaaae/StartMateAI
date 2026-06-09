package com.kakao.backend.chat.dto;

import java.util.List;

public record ChatMessageHistoryResponse(
        Long roomId,
        List<ChatMessageHistoryItemResponse> messages
) {
}
