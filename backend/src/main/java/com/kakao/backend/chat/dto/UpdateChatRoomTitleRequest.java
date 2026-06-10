package com.kakao.backend.chat.dto;

public record UpdateChatRoomTitleRequest(
        Long userId,
        String title
) {
}
