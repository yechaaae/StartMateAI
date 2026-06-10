package com.kakao.backend.chat.domain;

import com.kakao.backend.common.domain.BaseTimeEntity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "chat_request_status")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ChatRequestStatus extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "request_id", nullable = false, unique = true)
    private String requestId;

    @Column(name = "room_id", nullable = false)
    private Long roomId;

    @Column(name = "message_id", nullable = false)
    private Long messageId;

    @Column(name = "status", nullable = false)
    private String status;

    @Column(name = "error_message", columnDefinition = "text")
    private String errorMessage;

    public static ChatRequestStatus create(String requestId, Long roomId, Long messageId, String status) {
        ChatRequestStatus requestStatus = new ChatRequestStatus();
        requestStatus.setRequestId(requestId);
        requestStatus.setRoomId(roomId);
        requestStatus.setMessageId(messageId);
        requestStatus.setStatus(status);
        return requestStatus;
    }

    public void markProcessing() {
        this.status = "PROCESSING";
        this.errorMessage = null;
    }

    public void markCompleted() {
        this.status = "COMPLETED";
        this.errorMessage = null;
    }

    public void markFailed(String errorMessage) {
        this.status = "FAILED";
        this.errorMessage = errorMessage;
    }
}
