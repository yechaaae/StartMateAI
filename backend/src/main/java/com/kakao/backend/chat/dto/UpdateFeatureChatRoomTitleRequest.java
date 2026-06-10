package com.kakao.backend.chat.dto;

public record UpdateFeatureChatRoomTitleRequest(
        Long userId,
        String targetFeature,
        String title
) {
}
