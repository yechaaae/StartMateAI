package com.kakao.backend.chat.application;

public record FeatureChatRoomResult(
        Long roomId,
        Long workspaceId,
        String title,
        String roomType,
        String targetFeature,
        boolean created
) {
}
