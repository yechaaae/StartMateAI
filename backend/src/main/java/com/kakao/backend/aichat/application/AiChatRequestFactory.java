package com.kakao.backend.aichat.application;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.kakao.backend.aichat.dto.AiChatRequestMessage;
import org.springframework.stereotype.Component;

@Component
public class AiChatRequestFactory {

    private final AiChatPromptContextAssembler promptContextAssembler;

    public AiChatRequestFactory(AiChatPromptContextAssembler promptContextAssembler) {
        this.promptContextAssembler = promptContextAssembler;
    }

    public AiChatRequestMessage create(AiChatDispatchCommand command) {
        return new AiChatRequestMessage(
                "v1",
                "CHAT_REQUEST",
                command.requestId(),
                command.workspace() != null ? command.workspace().getId() : null,
                command.room() != null ? command.room().getId() : null,
                command.message() != null ? command.message().getId() : null,
                command.user() != null ? command.user().getId() : null,
                command.room() != null ? command.room().getRoomType() : null,
                command.room() != null ? command.room().getTargetFeature() : null,
                command.sessionType(),
                command.intent(),
                promptContextAssembler.assemble(command)
        );
    }
}
