package com.kakao.backend.aichat.application;

import com.kakao.backend.aichat.dto.AiChatResponseMessage;
import com.kakao.backend.aichat.dto.AiChatResultPayload;
import java.util.Optional;
import org.springframework.stereotype.Service;

@Service
public class AiChatResultSupportService {

    private final AiChatResponsePayloadReader responsePayloadReader;

    public AiChatResultSupportService(AiChatResponsePayloadReader responsePayloadReader) {
        this.responsePayloadReader = responsePayloadReader;
    }

    public Optional<AiChatPromotedResult> extract(AiChatResponseMessage response) {
        if (response == null) {
            return Optional.empty();
        }

        AiChatResultPayload result = responsePayloadReader.extractResult(response);
        if (result == null) {
            return Optional.empty();
        }
        if (!result.shouldCreateResult()) {
            return Optional.empty();
        }

        return Optional.of(new AiChatPromotedResult(
                response.requestId(),
                response.roomId(),
                result.targetFeature(),
                result.resultType(),
                result.resultTitle(),
                result.routeKey(),
                result.referenceId(),
                result.payload()
        ));
    }
}
