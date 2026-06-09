package com.kakao.backend.aichat.application;

import com.kakao.backend.aichat.dto.AiChatRequestMessage;

public interface AiChatGateway {

    void publish(AiChatRequestMessage requestMessage);
}
