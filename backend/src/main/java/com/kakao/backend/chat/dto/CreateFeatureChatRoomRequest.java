package com.kakao.backend.chat.dto;

public record CreateFeatureChatRoomRequest(
        Long userId,
        String targetFeature
) {
}
