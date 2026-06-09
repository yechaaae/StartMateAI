package com.kakao.backend.aichat.infrastructure;

import com.kakao.backend.aichat.dto.AiChatResponseMessage;
import com.kakao.backend.chat.application.ChatAiResponseCommandService;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;

@Component
public class AiChatResponseListener {

    private final ChatAiResponseCommandService chatAiResponseCommandService;

    public AiChatResponseListener(ChatAiResponseCommandService chatAiResponseCommandService) {
        this.chatAiResponseCommandService = chatAiResponseCommandService;
    }

    @RabbitListener(queues = "#{aiChatResponseQueue.name}")
    public void consume(AiChatResponseMessage response) {
        chatAiResponseCommandService.handle(response);
    }
}
