package com.kakao.backend.chat.dto;

import java.util.List;

public record FeatureChatRoomListResponse(
        List<FeatureChatRoomResponse> rooms
) {
}
