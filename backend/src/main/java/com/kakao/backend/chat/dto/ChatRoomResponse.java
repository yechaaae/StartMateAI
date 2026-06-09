package com.kakao.backend.chat.dto;

public record ChatRoomResponse(
        Long id,
        Long workspaceId,
        String title,
        String roomType,
        String targetFeature
) {
}
