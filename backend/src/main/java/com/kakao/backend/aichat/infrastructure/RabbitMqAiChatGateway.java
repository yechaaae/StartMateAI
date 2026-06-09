package com.kakao.backend.aichat.infrastructure;

import com.kakao.backend.aichat.application.AiChatGateway;
import com.kakao.backend.aichat.config.AiChatProperties;
import com.kakao.backend.aichat.dto.AiChatRequestMessage;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.stereotype.Component;

@Component
public class RabbitMqAiChatGateway implements AiChatGateway {

    private final RabbitTemplate rabbitTemplate;
    private final AiChatProperties properties;

    public RabbitMqAiChatGateway(RabbitTemplate rabbitTemplate, AiChatProperties properties) {
        this.rabbitTemplate = rabbitTemplate;
        this.properties = properties;
    }

    @Override
    public void publish(AiChatRequestMessage requestMessage) {
        rabbitTemplate.convertAndSend(properties.requestQueue(), requestMessage);
    }
}
