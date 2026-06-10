package com.kakao.backend.chat.dto;

public record FreeChatRoomResponse(
        Long roomId,
        Long workspaceId,
        String title,
        String roomType,
        String targetFeature,
        boolean created
) {
}
