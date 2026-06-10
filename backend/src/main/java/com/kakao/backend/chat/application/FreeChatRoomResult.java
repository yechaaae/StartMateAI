package com.kakao.backend.chat.application;

public record FreeChatRoomResult(
        Long roomId,
        Long workspaceId,
        String title,
        String roomType,
        String targetFeature,
        boolean created
) {
}
