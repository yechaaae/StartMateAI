package com.kakao.backend.chat.dto;

public record CreateChatRoomRequest(
        Long workspaceId,
        String title,
        String roomType,
        String targetFeature
) {
}
