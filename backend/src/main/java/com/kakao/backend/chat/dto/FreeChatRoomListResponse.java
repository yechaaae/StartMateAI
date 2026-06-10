package com.kakao.backend.chat.dto;

import java.util.List;

public record FreeChatRoomListResponse(
        List<FreeChatRoomResponse> rooms
) {
}