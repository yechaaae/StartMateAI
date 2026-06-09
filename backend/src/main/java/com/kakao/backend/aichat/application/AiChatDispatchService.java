package com.kakao.backend.aichat.application;

import com.kakao.backend.aichat.dto.AiChatRequestMessage;
import org.springframework.stereotype.Service;

@Service
public class AiChatDispatchService {

    private final AiChatGateway gateway;
    private final AiChatRequestFactory factory;

    public AiChatDispatchService(AiChatGateway gateway, AiChatRequestFactory factory) {
        this.gateway = gateway;
        this.factory = factory;
    }

    public String dispatch(AiChatDispatchCommand command) {
        AiChatRequestMessage requestMessage = factory.create(command);
        gateway.publish(requestMessage);
        return requestMessage.requestId();
    }
}
