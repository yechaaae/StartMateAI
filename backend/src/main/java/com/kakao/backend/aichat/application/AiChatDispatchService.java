package com.kakao.backend.aichat.application;

import com.kakao.backend.aichat.dto.AiChatRequestMessage;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

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
        // 트랜잭션이 진행 중이면 커밋 이후에 발행한다.
        // 커밋 전에 발행하면 ChatRequestStatus/메시지가 아직 커밋되지 않아
        // AI 응답 컨슈머가 status를 못 찾는 레이스(Chat request status not found)가 발생한다.
        if (TransactionSynchronizationManager.isSynchronizationActive()) {
            TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                @Override
                public void afterCommit() {
                    gateway.publish(requestMessage);
                }
            });
        } else {
            gateway.publish(requestMessage);
        }
        return requestMessage.requestId();
    }
}
