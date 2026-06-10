package com.kakao.backend.aichat.infrastructure;

import com.kakao.backend.aichat.dto.AiChatResponseMessage;
import com.kakao.backend.chat.application.ChatAiAgentEventService;
import com.kakao.backend.chat.application.ChatAiResponseCommandService;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;

@Component
public class AiChatResponseListener {

    private final ChatAiResponseCommandService chatAiResponseCommandService;
    private final ChatAiAgentEventService chatAiAgentEventService;

    public AiChatResponseListener(
            ChatAiResponseCommandService chatAiResponseCommandService,
            ChatAiAgentEventService chatAiAgentEventService
    ) {
        this.chatAiResponseCommandService = chatAiResponseCommandService;
        this.chatAiAgentEventService = chatAiAgentEventService;
    }

    @RabbitListener(queues = "#{aiChatResponseQueue.name}")
    public void consume(AiChatResponseMessage response) {
        if ("AGENT_EVENT".equalsIgnoreCase(response.messageType())) {
            chatAiAgentEventService.handle(response);
            return;
        }
        chatAiResponseCommandService.handle(response);
    }
}
