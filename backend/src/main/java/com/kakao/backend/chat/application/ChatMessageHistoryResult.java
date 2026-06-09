package com.kakao.backend.chat.application;

import java.util.List;

public record ChatMessageHistoryResult(
        Long roomId,
        List<ChatMessageHistoryItemResult> messages
) {
}
